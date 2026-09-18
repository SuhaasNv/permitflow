# Changelog

All notable milestones. Format: one section per sprint close plus in-sprint milestones. Story IDs refer to `docs/planning/USER_STORIES.md`.

## Sprint 1 — 18 Sep 2026 — "An operator can submit"

Sprint goal met: an operator signs in, creates an application, completes four validated sections, uploads four documents that are checked by the mock provider with live status, sees a server-computed progress indicator and submits; the submission becomes an immutable Revision 1 with audit events and officer notifications. Demonstrated end to end in Chrome at 1440, 820 and 390.

Numbers at close: backend 578 tests (ruff, mypy strict, pytest on Postgres), frontend 18 tests (oxlint, tsc, vitest, vite build), all green locally. CI has not run remotely: nothing has been pushed yet. 25 commits on `dev`, every one conventional.

### Shipped

| Story | Outcome |
|-------|---------|
| US-000 Project skeleton | Done |
| US-001 Login per persona | Done |
| US-030 Role-specific status labels + state machine | Done (528 parametrised transition tests) |
| US-010 Create application | Done |
| US-011 Sectioned form with validation | Done |
| US-012 Drag-and-drop document upload | Done (allowlist, magic bytes, 10 MB, sha256 no-change) |
| US-002 AI verification pipeline | Mock half Done; see Slipped |
| US-013 Live verification status | Done (pulled forward from Day 2) |
| US-014 Progress indicator | Done |
| US-015 Submit application | Done |
| US-006 CI pipeline | Skeleton Done; Playwright and Docker build remain Day 3 as planned |
| US-009 UI/UX design phase | Done (17 Sep, before the sprint) |

Also in this sprint, not tied to a story: the public landing page (FR-031), the branching strategy, two Railway environments documented, the frontend redesign (typography, motion, single-surface panels, shell, landing, sign-in, dashboard, application header, stepper, save indicator, toasts, progressive document check, review page) and the dashboard / My applications split.

### Slipped

- US-002 OpenAI provider: the `OpenAIProvider` class exists and is selected by `AI_PROVIDER`, but it has not been run against a live key. Moved to Sprint 2 as planned from the start; the mock stays the default. Notion `Sprint Day` set to Day 2 with a note.
- Nothing else slipped. US-006 was always split across Day 1 and Day 3.

### Retro

- What slowed us: the first UI pass was built to the prototype and judged "too basic". The redesign cost about a third of the day. Lesson: run the design-critique pass and a browser check on the first real screen, not after five screens.
- What went well: the domain layer (state machine, labels, form schema, completeness, verification rules) is pure and fully tested, so every UI rewrite touched no business logic and no backend test. The pipeline-in-background-task with polling met "real-time status" without a broker.
- What to change tomorrow: keep the officer screens honest from the first commit (no "all caught up" when the list is not built); verify every screen in Claude in Chrome at three widths before calling a story Done; write the Playwright journey early on Day 3 so the Sprint 2 loop is protected.
- Risk into Sprint 2: 19 stories on the plan. The cut order in `SPRINTS.md` applies; the OpenAI provider may slip to Sprint 3 morning without cutting anything.

## Sprint 2 (in progress, 19 Sep 2026)

- US-020 Review queue: `GET /officer/applications` (officer only; operators and admins get 403) lists every non-draft application with applicant, internal status and officer label, a server-derived next action and whose turn it is (`domain/officer_actions.py`), revision count, open feedback count, document-check attention and checking counts, first submission and last activity, plus turn counts, in four queries. Frontend queue with Needs review / Waiting on operator / Decided / All tabs, 30 s refresh, honest empty states; case route placeholder until US-021.

### Milestones during the sprint (Sprint 1)

- Dashboard and My applications are now different screens: the dashboard groups work cards by who is waiting on whom (Needs your response, Drafts to finish, With the licensing office, Decided) with a documents checklist rail; My applications is the full table with client-side status filter tabs.

- Frontend redesign (design language pass, no functional change): three-family typography (Public Sans, Instrument Serif display, IBM Plex Mono identifiers); motion tokens and route-keyed page entrance, staggered lists, animated stepper connectors and check marks, dialog and toast transitions, all collapsing under `prefers-reduced-motion`; one bordered surface per panel with rules instead of nested cards; app shell with sticky blurred top bar, side rail that animates between 232 and 64 px, bottom tab bar on phones; landing page rebuilt full width (hero, what you need, how it works, status journey, advisory-AI section); split sign-in with dark editorial panel; dashboard greeting by time of day with a one-line summary and clickable rows; shared `ApplicationHeader` (reference, business name, status, meta) on every application screen; journey stepper; `SaveIndicator` (Saving… / Saved just now); polished drop zone, upload progress and a progressive "Checking your document" block; review page as one editorial answers sheet with a sticky submit panel; submitted page; balanced empty states ("You are all caught up"). Verified in Chrome at 1440, 820 and 390. Follow-up: hero document panel centred with document glyphs, scroll reveals and a self-drawing status journey on the landing page, button hover sweeps, logo scrolls to top.

- US-015 Submit: `POST /applications/{id}/submit` locks the row, re-checks completeness through the state machine guard (422 listing every gap), creates immutable Revision 1 (form snapshot + document ids), moves to `application_received`, writes `revision.submitted` + `status.changed` audit events and one `submitted` notification per active officer, all in one transaction; the application becomes read-only (403 on edits, 409 on a second submit). Frontend: review page with section summaries, document check outcomes, warning for unresolved checks, submit dialog, 422 gap list; confirmation page with what happens next.

- US-014 Progress indicator: server-computed `completeness` (percent, per-section valid/invalid, per-document present/missing, list of gaps) used by both the UI and the submit guard; `CompletionCard` with progress bar and checklist with Fix / Start / Upload actions on the application page.

- US-002 (mock) + US-013 AI verification pipeline: `run_verification(run_id)` runs in FastAPI BackgroundTasks with its own session; extraction (pypdf ≤ 30 pages / 20 000 chars / 10 s, TXT, images → `unreadable`, no model call); `VerificationProvider` protocol with deterministic `MockProvider` (wrong type, field mismatch, expiry, short-text low confidence) and an `OpenAIProvider` (structured outputs, wire vs strict domain model) selected by `AI_PROVIDER`; strict domain validation (`extra=forbid`, 0..1 confidence, `IssueCode` enum); rules (confidence threshold → `needs_review`, prompt-injection heuristic → `needs_review` + issue); every failure stored as `failed` / `unavailable` with a reason, never raised; `verification.completed` audit; stale `running` runs marked `failed` at startup; `POST …/documents/{id}/verify` re-run (owner or officer, only when terminal). Frontend polls every 2 s while any check is pending/running and shows all eight states with plain-language copy, issues and "what to do"; "Re-run check" action. Confidence is not shown to operators.

- US-012 Document upload: `POST /applications/{id}/documents` (multipart) validates extension + MIME allowlist, magic bytes on the first chunk, 10 MB streamed cap, empty files; stores under a server-generated key via `FileStorage` (local disk); computes `sha256` while streaming; an identical re-upload for the same type returns `unchanged: true` and keeps the existing document; a different file supersedes the previous one (`supersedes_id`, `is_current`); creates a `pending` verification run; audit `document.uploaded` / `document.replaced` / `document.deleted`; `DELETE` while draft; authorised download (owner, officer, admin; sub-resource check). Frontend documents page: per-type slots, drag-and-drop + browse, XHR progress bar, client pre-validation, replace, remove with confirmation, download, duplicate notice, verification block copy for all eight states, required-documents checklist.

- US-011 Sectioned form: `PATCH /applications/{id}/sections/{key}` with row lock, editability by state (403 outside the editable set), Pydantic/domain validation (422 with per-field messages; in `draft`, missing required fields are tolerated so a partial section can be saved), form page with stepper, section rail with completion marks, Zod validators built from `/form-schema` (draft vs complete modes), inline errors + error summary, Save section / Save and continue, unsaved-changes dialog. Also: public landing page at `/` (FR-031), login column centred, frontend on port 3000.

- US-010 Create application: `POST /applications` creates a draft with a sequential reference (`PF-<year>-<n>`, migration `0002`) and an `application.created` audit event in the same transaction; `GET /applications` (own only) and `GET /applications/{id}` (other operators' applications look like 404); `GET /form-schema`; operator view serializer with role label, tone, plain-language explanation, sections, document slots, editability and completeness; pure-domain form schema with server-side validation and completeness rules; dashboard with list, empty/loading/error states and "New application".

- US-030 Role-specific status labels and the state machine: `domain/labels.py` (assessment table verbatim, tested row by row; badge tone), `domain/workflow.py` (every transition from STATE_MACHINE.md with actors and guards, reject from every non-terminal post-submission state, `available_actions` with disabled reasons), 528 parametrised tests covering every (state, target, actor) combination; `StatusBadge` component that renders the served label and never maps codes.

- US-001 Login per persona: `POST /auth/login` (argon2, JWT with role claim, generic 401, 429 after 10 failed attempts per IP), `GET /auth/me`, role guards (`require_role`) that re-check the user row per request, seed script for operator and officer; frontend login page (Zod validation, error states), session in memory + sessionStorage with server re-validation, `RequireRole` guard, role home routing, app shell with masthead, collapsible side rail and mobile drawer, "Not available for your role" and not-found panels.

- US-000 Project skeleton: FastAPI app with standard error body, security headers, CORS, JSON request logging, `/api/v1/health` (503 when the database is down); SQLAlchemy models for the whole domain model and Alembic migration `0001`; Docker Compose PostgreSQL with a separate test database; pytest fixtures that migrate from scratch and truncate between tests; layering tests; React + TypeScript + Vite + Tailwind shell with design tokens and typed API client; GitHub Actions CI skeleton (backend lint/type/test on Postgres, frontend lint/type/test/build, gitleaks).

## Design phase (17–18 Sep 2026)

- US-009 UI/UX design phase: design system, 23-artboard prototype, design documentation, two critique passes. See `docs/design/README.md`.
