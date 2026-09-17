# Changelog

All notable milestones. Format: one section per sprint close plus in-sprint milestones. Story IDs refer to `docs/planning/USER_STORIES.md`.

## Sprint 1 (in progress, 18 Sep 2026)

- US-012 Document upload: `POST /applications/{id}/documents` (multipart) validates extension + MIME allowlist, magic bytes on the first chunk, 10 MB streamed cap, empty files; stores under a server-generated key via `FileStorage` (local disk); computes `sha256` while streaming; an identical re-upload for the same type returns `unchanged: true` and keeps the existing document; a different file supersedes the previous one (`supersedes_id`, `is_current`); creates a `pending` verification run; audit `document.uploaded` / `document.replaced` / `document.deleted`; `DELETE` while draft; authorised download (owner, officer, admin; sub-resource check). Frontend documents page: per-type slots, drag-and-drop + browse, XHR progress bar, client pre-validation, replace, remove with confirmation, download, duplicate notice, verification block copy for all eight states, required-documents checklist.

- US-011 Sectioned form: `PATCH /applications/{id}/sections/{key}` with row lock, editability by state (403 outside the editable set), Pydantic/domain validation (422 with per-field messages; in `draft`, missing required fields are tolerated so a partial section can be saved), form page with stepper, section rail with completion marks, Zod validators built from `/form-schema` (draft vs complete modes), inline errors + error summary, Save section / Save and continue, unsaved-changes dialog. Also: public landing page at `/` (FR-031), login column centred, frontend on port 3000.

- US-010 Create application: `POST /applications` creates a draft with a sequential reference (`PF-<year>-<n>`, migration `0002`) and an `application.created` audit event in the same transaction; `GET /applications` (own only) and `GET /applications/{id}` (other operators' applications look like 404); `GET /form-schema`; operator view serializer with role label, tone, plain-language explanation, sections, document slots, editability and completeness; pure-domain form schema with server-side validation and completeness rules; dashboard with list, empty/loading/error states and "New application".

- US-030 Role-specific status labels and the state machine: `domain/labels.py` (assessment table verbatim, tested row by row; badge tone), `domain/workflow.py` (every transition from STATE_MACHINE.md with actors and guards, reject from every non-terminal post-submission state, `available_actions` with disabled reasons), 528 parametrised tests covering every (state, target, actor) combination; `StatusBadge` component that renders the served label and never maps codes.

- US-001 Login per persona: `POST /auth/login` (argon2, JWT with role claim, generic 401, 429 after 10 failed attempts per IP), `GET /auth/me`, role guards (`require_role`) that re-check the user row per request, seed script for operator and officer; frontend login page (Zod validation, error states), session in memory + sessionStorage with server re-validation, `RequireRole` guard, role home routing, app shell with masthead, collapsible side rail and mobile drawer, "Not available for your role" and not-found panels.

- US-000 Project skeleton: FastAPI app with standard error body, security headers, CORS, JSON request logging, `/api/v1/health` (503 when the database is down); SQLAlchemy models for the whole domain model and Alembic migration `0001`; Docker Compose PostgreSQL with a separate test database; pytest fixtures that migrate from scratch and truncate between tests; layering tests; React + TypeScript + Vite + Tailwind shell with design tokens and typed API client; GitHub Actions CI skeleton (backend lint/type/test on Postgres, frontend lint/type/test/build, gitleaks).

## Design phase (17–18 Sep 2026)

- US-009 UI/UX design phase: design system, 23-artboard prototype, design documentation, two critique passes. See `docs/design/README.md`.
