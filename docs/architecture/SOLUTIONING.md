# PermitFlow — Solutioning

Engineering problems evaluated before implementation. Each entry: problem, constraints, options, choice, rationale, tradeoffs, validation. Decisions with lasting architectural impact also have an ADR in `decisions/`.

Global constraints that apply to every decision below:
- 3 calendar days, one engineer plus AI assistance.
- Must be runnable from the README on a clean machine and deployable to a simple platform.
- Evaluated on judgement and production readiness, not breadth.
- Must be explainable in a debrief.

---

## 1. Deployment topology: modular monolith vs microservices

**Problem.** How many deployable units?
**Options.** (A) Modular monolith: one API process, one DB, module boundaries in code. (B) Microservices per domain (applications, documents, AI). (C) Monolith plus a separate AI worker service.
**Choice.** A, with the AI verifier isolated behind an interface so C is a later extraction.
**Rationale.** One team, one repo, one database, three days. Module boundaries give maintainability; separate deployables would add network failure modes, contract versioning and infra for no user-visible benefit.
**Tradeoffs.** AI verification shares the API process's CPU; a long verification could compete with request handling. Mitigated by timeouts and by keeping extraction cheap.
**Validation.** Import-linter style check that modules only depend inward (documented dependency direction; enforced by review and a lightweight test that routers do not import repositories directly). See ADR-001.

## 2. API style: REST vs GraphQL vs RPC

**Options.** (A) REST/JSON with OpenAPI (FastAPI generates it). (B) GraphQL. (C) tRPC-style RPC (needs a TS backend).
**Choice.** A.
**Rationale.** FastAPI gives typed request/response models and OpenAPI for free; the resource model (applications, revisions, documents, feedback) maps cleanly; frontend can generate types from OpenAPI. GraphQL would add resolver authorization complexity, which is exactly where this product must be strict.
**Tradeoffs.** A few endpoints return composed views (application detail includes revision, documents, feedback) to avoid client-side joins; documented as read models rather than pure resources.
**Validation.** OpenAPI schema committed and used to generate the frontend client types; integration tests per endpoint.

## 3. Database: PostgreSQL relational vs document store

**Options.** (A) PostgreSQL with normalised tables and JSONB for revision snapshots. (B) MongoDB. (C) SQLite only.
**Choice.** A. PostgreSQL only — no SQLite fallback, even for tests.
**Rationale.** The domain is relational (users, applications, revisions, documents, feedback, audit) with strong integrity needs (no lost applications, atomic submissions). Postgres JSONB gives a natural home for the form snapshot without a table per field. Railway provides managed Postgres.
**Tradeoffs.** JSON columns are used for form data; queries by field are not needed at MVP scale. Dropping a SQLite fallback means tests need Docker (or CI's Postgres service), but it lets us use `SELECT … FOR UPDATE`, native UUIDs, JSONB and sequences without a second engine to keep green.
**Validation.** Alembic migrations; integration tests on Postgres in CI. See ADR-002.

## 4. File storage

**Options.** (A) Local disk behind an interface, Railway volume in prod. (B) S3-compatible bucket from day one. (C) Store bytes in Postgres.
**Choice.** A.
**Rationale.** Uploads at MVP scale are small; an interface (`FileStorage.save/open/delete`) keeps the swap to S3 a one-file change. Bytes-in-DB bloats backups and complicates streaming.
**Tradeoffs.** Not horizontally scalable; no signed URLs. Files are only served through an authorized API endpoint, which is the right control regardless of backend.
**Validation.** Unit test for the storage interface with a temp directory; authorization test for the download endpoint.

## 5. AI verification: synchronous vs asynchronous

**Options.** (A) Synchronous in the upload request. (B) In-process background task with polled status. (C) External worker + queue.
**Choice.** B, designed so C is additive (a `verification_runs` table with status, and a single `run_verification(document_id)` entry point).
**Rationale.** The assessment asks for "real-time AI verification status visible per uploaded document", which implies the upload returns immediately and the status changes later. A queue would add a broker to run locally and deploy; three days does not justify it.
**Tradeoffs.** If the API process restarts mid-verification, the run stays `running`. Mitigation: on startup, mark stale `running` runs as `failed` with reason `interrupted`, and expose a re-run action.
**Validation.** Integration test: upload → status pending → background task executes with mock provider → status verified. See ADR-004.

## 6. Workflow state: explicit state machine vs scattered status logic

**Options.** (A) One `StateMachine` module: transition table keyed by (from, to) with the allowed role and guards. (B) Status checks inline in each endpoint. (C) A workflow library.
**Choice.** A.
**Rationale.** The assessment lists 12 states with precise labels and visibility rules and stresses "no applications lost due to status transitions". A single table is testable exhaustively and readable in the debrief. A library is overkill for a linear-ish flow.
**Tradeoffs.** Guards that need data (e.g. "no open feedback before site visit") are passed in as a small context object, keeping the machine pure.
**Validation.** Parametrised unit tests over every (state, target, role) combination. See ADR-003.

## 7. Authorization: server-side vs UI-only

**Options.** (A) Server-side dependency-injected checks per endpoint plus role-aware serializers. (B) Hide things in the UI.
**Choice.** A; the UI also hides, but that is presentation.
**Rationale.** "Never expose the internal approval stage to Operators" is a data-exposure rule; it must hold for the raw API. Ownership is checked in one repository method (`get_for_user`) so it cannot be forgotten.
**Tradeoffs.** Slightly more code per endpoint; worth it.
**Validation.** Authorization tests: operator A cannot read/modify operator B's application (404); operator cannot call officer endpoints (403); operator response never contains internal labels. See ADR-005.

## 8. AI-driven vs deterministic workflow

**Options.** (A) LLM output is advisory data attached to documents; workflow is deterministic. (B) LLM decides whether to accept a document or move status.
**Choice.** A.
**Rationale.** A regulator cannot delegate outcomes to a probabilistic component; officers are accountable. AI value here is triage: surface likely problems early.
**Tradeoffs.** Less "magic". Officers still make every call.
**Validation.** Code review: no code path from verification results to status or feedback mutations; test asserts submission is allowed with failed verification. See ADR-006.

## 9. Structured LLM output vs free-form

**Options.** (A) Tool-use / JSON schema forced output, validated by Pydantic. (B) Free text parsed with regex. (C) Free text shown to the officer as-is.
**Choice.** A.
**Rationale.** Structured output allows deterministic post-processing (thresholds, issue codes), UI rendering, and tests. Validation failures are treated as provider failures.
**Tradeoffs.** Model may still produce semantically wrong but schema-valid output; confidence field and evidence quotes help the officer judge.
**Validation.** Unit tests feeding malformed, partial, extra-field and injected outputs to the validator; evaluation set run against the real provider. See ADR-006.

## 10. Background jobs vs synchronous processing (general)

Everything except AI verification is synchronous within a request and a single transaction. Notifications are rows inserted in the same transaction (no delivery step to fail). This keeps REL-002 (atomic submission) simple. Revisit if email delivery is added.

## 11. Revision storage strategy

**Options.** (A) Full snapshot of form data JSON + document id list per revision. (B) Event-sourced field changes. (C) Mutable application row plus a change log.
**Choice.** A.
**Rationale.** Snapshots make "compare any two revisions" and "data is never lost" trivial and auditable; storage cost is negligible for a form. Event sourcing is elegant but expensive to get right in three days. C loses the ability to reconstruct exactly what the officer saw.
**Tradeoffs.** Diff is computed at read time (cheap for a small form); a working copy (`draft_data`) lives on the application row between submissions.
**Validation.** Integration test: two resubmissions produce three revisions; revision 1 unchanged after revision 3. See ADR-007.

## 12. Audit log strategy

**Options.** (A) Append-only `audit_events` table written by services in the same transaction. (B) Database triggers. (C) Log files only.
**Choice.** A.
**Rationale.** Application-level events carry business meaning (feedback resolved, revision submitted) and the actor, which triggers do not know. Same-transaction writes guarantee consistency.
**Tradeoffs.** Relies on discipline: every mutating service must call `audit.record`. Mitigated by putting the call inside the service layer, not routers, and by tests asserting event counts.
**Validation.** Integration test asserting the exact event sequence for the critical journey. See ADR-008.

## 13. Diff strategy

**Options.** (A) Deterministic structural diff over the section→field JSON, plus set diff over documents by type. (B) Text diff library. (C) LLM summarises changes.
**Choice.** A.
**Rationale.** Form data is structured; a field-level diff is exact and explainable. LLM summaries would be unverifiable.
**Tradeoffs.** Long free-text fields show whole-value old/new rather than word-level diff; acceptable. Documents are compared by `sha256`, not by row id, so re-uploading the same file is not a change.
**Validation.** Unit tests for added/removed/changed fields, nested sections, and document replace/add/remove.

## 14. Frontend data and state management

**Options.** (A) TanStack Query for server state + local component state; no global store. (B) Redux Toolkit. (C) Zustand global store.
**Choice.** A.
**Rationale.** Nearly all state is server state (applications, documents, feedback). TanStack Query gives caching, polling (verification status), invalidation after mutations, and loading/error states. Auth token is the only global piece and lives in a small context.
**Tradeoffs.** Polling adds requests while verifying; bounded by stopping when no document is pending.
**Validation.** Vitest tests on hooks with MSW; E2E asserts status updates without reload.

## 15. Form validation strategy

**Options.** (A) Zod schemas per section on the client, mirrored Pydantic models on the server, both derived from one shared field definition list (`form_schema` JSON exported by the backend). (B) Validate only on the server. (C) Validate only on the client.
**Choice.** A, with the backend as the source of truth: the backend serves `/form-schema` (sections, fields, types, required, labels) and the frontend builds Zod schemas from it; server-side Pydantic validation is authoritative.
**Rationale.** Inline validation is a UX requirement; server validation is a security requirement; one definition prevents drift.
**Tradeoffs.** Dynamic Zod construction is slightly more code than static schemas.
**Validation.** Unit test that every field in the served schema is validated identically on both sides for required/max-length cases.

## 16. Testing strategy

Layered (see `docs/testing/TEST_STRATEGY.md`): unit tests for the state machine, authorization, diff, AI validation; integration tests through the FastAPI test client against Postgres for the lifecycle; one Playwright E2E for the critical journey; an AI evaluation set. Target is behaviour coverage, not a percentage.

## 17. Deployment strategy

**Options.** (A) Railway: backend service (Docker), Postgres plugin, frontend as static site. (B) Render. (C) Fly.io. (D) Docker Compose only.
**Choice.** A (CLI already installed; managed Postgres; volumes for uploads). D is also provided for local runs.
**Tradeoffs.** Single region, no autoscaling; fine for MVP.
**Validation.** Health endpoint checked after deploy; UAT run on the deployed URL.

## 18. CI/CD strategy

**Options.** (A) GitHub Actions: one CI workflow (lint, typecheck, unit/integration, E2E, secret scan, Docker build) required on PRs; deployment triggered manually / on main via Railway. (B) No CI. (C) Full GitOps.
**Choice.** A. CI and deployment are separate workflows so a green CI is a precondition, not a trigger, for deploying.
**Validation.** Branch protection on `main` requires the CI workflow.

## 19. Authentication mechanism

**Options.** (A) JWT bearer tokens issued by the backend with seeded users. (B) Session cookies. (C) External IdP.
**Choice.** A.
**Rationale.** Simplest to demo across a static frontend and API on different origins; role claim in the token; no CSRF surface because no cookies. Passwords hashed with argon2.
**Tradeoffs.** Token stored in `sessionStorage` is readable by XSS; mitigated by React's escaping, no `dangerouslySetInnerHTML`, and 8-hour expiry. Documented as a production gap (httpOnly cookie + refresh token).
**Validation.** Auth tests; security headers test.

## 20. LLM provider

**Options.** (A) OpenAI via the official `openai` SDK with structured outputs (JSON schema derived from a Pydantic model), direct API key. (B) Anthropic Claude with tool-use structured output. (C) Any provider behind one interface.
**Choice.** C in design, A implemented: a `VerificationProvider` protocol with `OpenAIProvider` and `MockProvider`; other providers (Anthropic, Azure OpenAI) can be added without touching the pipeline. The product owner asked for OpenAI with a direct key.
**Rationale.** Structured outputs with a JSON schema give reliable, validated output; the mock keeps tests hermetic and the app functional without a key.
**Validation.** Evaluation set; unit tests on the mock; provider selection by environment variable tested.
