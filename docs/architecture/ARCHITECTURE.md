# PermitFlow — Architecture

A modular monolith (ADR-001): one FastAPI backend, one React frontend, one PostgreSQL database, local file storage, and an isolated AI verification module.

## System diagram

```
┌────────────────────────────────────────────────────────────────────┐
│ Browser (React 19 + TypeScript strict, Vite, Tailwind v4)          │
│  pages/ ─▶ features/ (hooks: TanStack Query) ─▶ api/ (typed client)│
│  Auth context (JWT in memory + sessionStorage)                     │
└──────────────┬─────────────────────────────────────────────────────┘
               │ HTTPS JSON (Bearer token), multipart for uploads
┌──────────────▼─────────────────────────────────────────────────────┐
│ FastAPI backend (backend/app)                                      │
│                                                                    │
│  api/            routers, request/response schemas, dependencies   │
│    │  (auth, role, ownership resolved here)                        │
│  services/       use cases: ApplicationService, SubmissionService, │
│    │             FeedbackService, DocumentService, VerificationSvc │
│    │             — the only layer that mutates and writes audit    │
│  domain/         pure logic: workflow (state machine), form_schema,│
│    │             diff, labels, feedback resolution rules           │
│  repositories/   SQLAlchemy queries; ownership filters             │
│  models/         SQLAlchemy ORM models                             │
│  infra/          db session, storage (FileStorage), notifier,      │
│                  ai providers (OpenAI, Mock)  , logging, settings │
│                                                                    │
│  Background task: verification.run_verification(document_id)      │
└───────┬───────────────────────────┬─────────────────┬──────────────┘
        │                           │                 │
┌───────▼────────┐        ┌─────────▼───────┐  ┌──────▼─────────────┐
│ PostgreSQL     │        │ File storage    │  │ LLM provider       │
│ (JSON snapshots│        │ (local disk /   │  │ (OpenAI API,       │
│  + relational) │        │  Railway volume)│  │  replaceable)      │
└────────────────┘        └─────────────────┘  └────────────────────┘
```

## Backend layering and dependency direction

```
api  ──▶  services  ──▶  domain
 │            │            ▲
 │            ▼            │ (domain imports nothing from below)
 │        repositories ──▶ models
 │            │
 └──────▶  infra (settings, db, storage, ai, notifier, logging)
```

Rules:
- `api` never touches `repositories` or `models` directly; it calls services and maps exceptions to HTTP.
- `domain` is pure Python: no SQLAlchemy, no FastAPI, no I/O. It contains the state machine, labels, form schema, diff and resolution rules — the code a reviewer should read first.
- `services` orchestrate: load via repositories, apply domain rules, mutate, write audit events, create notifications, commit. One service method = one transaction.
- `infra.ai` exposes `VerificationProvider`; `services.verification` is the only caller. No other module imports `infra.ai`.
- A unit test enforces the two most important rules (routers do not import repositories; domain does not import SQLAlchemy/FastAPI).

## Module boundaries and data ownership

| Module | Owns tables | Public service API (examples) |
|--------|-------------|-------------------------------|
| auth | users | `authenticate(email, password) -> Token`, `current_user()` |
| applications | applications | `create`, `get_for(user, id)`, `list_for(user)`, `update_draft(user, id, section, data)`, `transition(officer, id, target, note, expected_version)` |
| revisions | application_revisions | `submit(operator, id)`, `resubmit(operator, id)`, `list(id)`, `compare(id, from_no, to_no)` |
| documents | documents | `upload(user, id, type, file)`, `replace`, `download`, `list` |
| verification | verification_runs | `enqueue(document_id)`, `run_verification(document_id)`, `latest(document_id)`, `rerun` |
| feedback | feedback | `create(officer, id, target, message, template_key)`, `resolve`, `withdraw`, `list`, `templates()` |
| notifications | notifications | `notify(user_ids, kind, application, ...)`, `list(user)`, `mark_read` |
| audit | audit_events | `record(application_id, actor, event_type, payload)`, `list(application_id)`, `feed(limit)` |
| admin | — (reads other modules' tables through their repositories; writes users through the auth module's service) | `overview()`, `ai_health()`, `audit_feed()`, `users()`, `create_user()`, `update_user(role, is_active)` |

Cross-module writes go through services, never across repositories.

## Request flow examples

### Upload with AI verification
```
POST /applications/{id}/documents (multipart)
  api: auth → ownership → editability (draft: any type; pending resubmission: flagged types only)
       → validate extension/MIME/size (streamed, 10 MB cap) → magic bytes
  DocumentService.upload (one transaction): Document row (is_current, supersedes) →
     VerificationRun(pending) → audit document.uploaded → commit
     file bytes are written to FileStorage before commit; on commit failure the file is deleted
  BackgroundTasks.add(run_verification, run_id)   # request session is already closed at this point
  201 { document, verification: { status: "pending" } }

run_verification(run_id):   # plain sync function; FastAPI runs it in the threadpool
  opens its own SessionLocal() and transaction (the request-scoped session is gone)
  set running
  → extract text here, not in the request: pypdf with caps (≤ 30 pages, ≤ 20 000 chars, 10 s budget);
    images and unsupported types → unreadable (no model call); empty text → unreadable
  → injection heuristic (instruction-like phrases) → forces needs_review later
  → provider.verify(request) with 30 s timeout, one retry on transient errors (sync openai client)
  → parse wire model → validate into domain VerificationResult (extra=forbid, bounded confidence)
  → deterministic rules (confidence threshold, injection flag) → persist terminal status
  → audit verification.completed → commit
  → on any exception: failed/unavailable with reason (never raises out of the task)
  Multi-worker note: startup stale-run cleanup only marks runs whose started_at is older than the
  timeout + grace, so a peer worker's in-flight run is not killed.

Client: GET /applications/{id} polls every 2 s while any document is pending/running.
```

### Resubmission
```
POST /applications/{id}/resubmit
  api: auth → ownership
  SubmissionService.resubmit:
    SELECT application FOR UPDATE; load current revision + open feedback (transaction)
    domain.diff(previous.form_data, app.draft_data) → changed sections; documents compared by sha256
    domain.resolution.validate_only_flagged_changed(changed, open_feedback) → 403 if violated
    require at least one flagged target changed → 422 otherwise
    workflow.transition(app, pre_site_resubmitted, actor=operator, ctx)
    Revision N+1 (snapshot) → feedback with changed targets → addressed
    audit revision.submitted, feedback.addressed*, status.changed
    notify officers
    commit
  200 { application (operator view) }
```

## API surface (v1)

All under `/api/v1`. Error body: `{ "error": { "code": string, "message": string, "details"?: object } }`.

| Method | Path | Role | Purpose |
|--------|------|------|---------|
| POST | /auth/login | any | JWT |
| GET | /auth/me | any | current user |
| GET | /form-schema | any | sections/fields definition |
| GET | /feedback-templates | any | comment templates |
| GET | /applications | operator | own applications |
| POST | /applications | operator | create draft |
| GET | /applications/{id} | operator (own) | operator view: sections, documents + verification, feedback (all rounds), revisions summary, editability |
| PATCH | /applications/{id}/sections/{key} | operator (own) | update a section of the working copy (checked against editability) |
| POST | /applications/{id}/submit | operator (own) | draft → application_received |
| POST | /applications/{id}/resubmit | operator (own) | pending_pre_site_resubmission → pre_site_resubmitted |
| POST | /applications/{id}/documents | operator (own) | upload / replace by type |
| DELETE | /applications/{id}/documents/{doc_id} | operator (own) | remove a document while in `draft` only |
| GET | /applications/{id}/documents/{doc_id}/download | owner, officer or admin | file; the document must belong to `{id}` |
| POST | /applications/{id}/documents/{doc_id}/verify | owner or officer | re-run verification (only when the latest run is terminal) |
| GET | /applications/{id}/revisions | owner, officer or admin | list revisions |
| GET | /applications/{id}/revisions/{n} | owner, officer or admin | snapshot |
| GET | /applications/{id}/compare?from=n&to=m | owner, officer or admin | field and document diff |
| GET | /officer/applications | officer | queue (all applications, internal status, counts) |
| GET | /officer/applications/{id} | officer | officer view (internal status, officer label, audit, feedback, verification) |
| POST | /officer/applications/{id}/transition | officer | `{ target, note?, expected_version }` |
| POST | /officer/applications/{id}/feedback | officer | create feedback (only while `under_review`) |
| POST | /officer/applications/{id}/feedback/{fid}/resolve | officer | addressed/open → resolved; `{fid}` must belong to `{id}` |
| POST | /officer/applications/{id}/feedback/{fid}/withdraw | officer | open → withdrawn (only while `under_review`) |
| GET | /officer/applications/{id}/audit | officer | audit trail |
| GET | /admin/overview | admin | counts by status, idle applications, today's submissions |
| GET | /admin/ai-health | admin | verification runs (24 h), outcome counts, failure rate, latency, provider |
| GET | /admin/audit-feed | admin | latest 50 audit events across applications |
| GET | /admin/users | admin | user directory |
| POST | /admin/users | admin | create user `{full_name, email, role}`; audit `user.created` |
| PATCH | /admin/users/{id} | admin | change `role` and/or `is_active`; audit `user.role_changed` / `user.deactivated` / `user.reactivated`; 409 when it would remove the last active admin |
| GET | /admin/applications/{id} | admin | officer view, read-only (mutations 403) |
| GET | /notifications | any | own notifications |
| POST | /notifications/{id}/read | any | mark read; scoped to the caller's own notifications |
| GET | /health | public | `{status, database}`; 503 when the database ping fails; provider details are not exposed publicly (admin sees them in `/admin/ai-health`) |

All paths are under `/api/v1` including `/health`. FastAPI's default `{"detail": …}` bodies for 401/403/422 are replaced by explicit exception handlers so every error uses the standard shape (REL-001).

## Frontend structure

```
frontend/src
  api/            generated OpenAPI types + thin fetch client (auth header, error mapping)
  app/            router, providers (QueryClient, Auth), layout shell
  features/
    auth/         login page, useAuth
    operator/     dashboard, application form (sections, uploads, progress), application detail, resubmission
    officer/      queue, review page (sections, documents, AI results, feedback panel, transition actions), compare view, audit
    admin/        operations dashboard (status counts, idle, AI health, audit feed), users (add, change role, deactivate)
    landing/      public landing page
    shared/       StatusBadge, FeedbackList, DocumentCard, RevisionCompare, EmptyState, ErrorState, Skeleton
  lib/            zod-from-schema builder, formatting, constants
  styles/         tailwind base, design tokens
```

State: server state in TanStack Query (query keys per resource; invalidation after mutations; polling while verifying). Auth in a small context. Forms via React Hook Form with Zod resolvers built from `/form-schema`.

## Error boundaries

- API: a global exception handler maps domain exceptions (`NotFound`, `Forbidden`, `InvalidTransition`, `ValidationFailed`, `VersionConflict`) to the standard error body; unexpected exceptions → 500 with a request id and no stack trace.
- Verification task: catches everything, records failure, never propagates.
- Frontend: route-level error boundary; query errors rendered by `ErrorState` with retry; mutation errors shown inline and preserve input.

## Authorization boundaries

- Authentication: `get_current_user` dependency (JWT → User row; rejects unknown users and `is_active = false`).
- Role: `require_role(...)` on officer routers (`officer`) and admin routers (`admin`); admin is read-only on applications.
- Ownership: `ApplicationRepository.get_for(user, id)` applies `operator_id` filter for operators; raises `NotFound`.
- Editability: `domain.editability.editable_targets(status, open_feedback)` used by section update and document upload.
- Transition role and guards: `domain.workflow`.
- Response shaping: `ApplicationOperatorView` vs `ApplicationOfficerView`.

## Observability

- Request logging middleware: request id, method, path, status, duration, user id; request id echoed in `X-Request-ID`.
- Verification logs: run id, provider, model, latency, outcome, `raw_output_valid`.
- `/health`: database ping (503 on failure). AI provider configuration is reported on the admin AI-health endpoint, not publicly.

## Deployment

- Local: `docker compose up db` (PostgreSQL only; the API and the frontend run natively with `uvicorn` and `vite`) or `docker compose --profile full up` to also run the API container. A local database is kept because the test suite truncates tables between tests and because a reviewer must be able to run the system from a clean clone without any hosted credentials (NFR-001).
- Railway, two environments: `development` deploys from the `dev` branch and `production` from `main` (see `docs/operations/BRANCHING.md`). Each has its own PostgreSQL and its own variables. Per environment: `backend` service from `backend/Dockerfile` with a volume at `/data/uploads`, `frontend` static service built from `frontend/` with `VITE_API_URL`. See `docs/operations/OPERATIONS.md`.
