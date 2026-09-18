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

## Sprint 2 — 19 Sep 2026 — "The loop closes, twice"

Sprint goal met: the officer opens a queue, reviews the submitted revision with AI-assisted document checks beside each document, adds contextual feedback from templates and requests a resubmission; the operator sees the feedback on top, can edit only the flagged targets, resubmits as Revision 2; the officer sees Changed and Addressed markers, compares any two revisions, resolves feedback, schedules and completes a site visit, routes to approval and decides; the operator sees the outcome with the officer's note. Every step is audited and notified. Demonstrated end to end in Chrome, twice around, at 1440, 820 and 390, and the live OpenAI provider verified through the API.

Numbers at close: backend 620 tests (ruff, mypy strict, pytest on Postgres), frontend 28 tests (oxlint, tsc, vitest, vite build), all green locally. 33 commits on `dev` since `v0.1.0`, every one conventional, every story on its own branch merged with `--no-ff`. Remote CI has run for the branches pushed so far.

### Shipped

| Story | Outcome |
|-------|---------|
| US-020 Review queue | Done |
| US-021 Case view + Start review | Done |
| US-022 AI results beside documents | Done |
| US-023 Contextual feedback | Done |
| US-024 Comment templates | Done (7 templates) |
| US-025 Status transitions + operator notification | Done |
| US-032 Operator sees only the outcome | Done |
| US-016 Resubmission view | Done |
| US-017 Feedback anchored to section or document | Done |
| US-018 Edit only flagged, resubmit | Done |
| US-019 Operator history | Done |
| US-026 Officer notified on resubmission | Done |
| US-027 Highlights + revision compare | Done (any two revisions, SCOPE S4) |
| US-028 Feedback resolution tracking | Done |
| US-029 Audit trail | Done |
| US-031 Site visit and outcome | Done |
| US-013 Live verification status polish | Done |
| US-002 OpenAI provider | Done (`gpt-4.1-mini`) |
| US-003 Injection heuristic + malformed output | Done |
| US-033 Operator edge cases (added 19 Sep) | Done |
| US-034 Backend edge cases (added 19 Sep) | Done |

Also in this sprint, not tied to a story: the tidy pass (layering, schemas package, dead code), `docs/design/USER_JOURNEY.md`, `docs/reviews/EDGE_CASE_REVIEW.md`, SCOPE assumption 10 (who the operator is), 20 as-built captures in `docs/design/screens/as-built/`.

### Slipped

- Nothing. Every story on the Sprint 2 plan is Done, including the two added on the day.

### Retro

- What slowed us: the first live OpenAI call exposed two prompt and schema defects at once (invented enum values, no date), and the full test run against the live key took four minutes. Lesson: pin the wire schema and force the mock in tests before the first live run, not after.
- What went well: every officer and operator screen was verified in the browser at three widths before its story moved to Done; three independent edge-case reviews found 40 items and all the "now" ones shipped as two stories with tests, without breaking the loop (full suites and a browser smoke after the tidy pass).
- What to change tomorrow: write the Playwright journey first thing so the loop is protected while the Day 3 documents are written; keep the admin epic strictly after the MUSTs (tests, CI, deployment, documents).
- Risk into Sprint 3: Railway deployment needs the user's account; everything else is in our hands.

## Sprint 3 (in progress, 19 Sep 2026)

- US-006 CI complete: an `e2e` job starts the whole stack inside GitHub Actions (Postgres service, migrations, seed, uvicorn on the mock provider, `vite preview` of the production build) and runs the journey plus the six scenarios, uploading the Playwright report on failure; a `docker` job builds the backend image with the Actions cache. Verified locally with the same recipe (preview build, all seven specs green) and a local image build.

- US-047 Landing hero: red accent on the headline and the document tiles, an ink band with two slowly drifting lights behind the What you need panel (bleeds to the screen edge, panel centred, reduced motion respected), staff sign-in link dropped from the footer. A full red band was tried and rejected as too heavy. Also: site visit actions renamed to "Mark site visit scheduled" with a dialog note that no appointment is booked (UC3 deferred).

- US-042 Scenario suite: six Playwright specs, one per workflow (apply with AI checks; reaches the officer; officer flags, undoes, requests resubmission; two resubmission rounds to approval; withdraw; rejection), each asserting the audit trail; shared helpers seed officer-side scenarios through the API. Demo PDFs (`docs/demo/documents`) verified against the live check.

- US-044 Errors inside CORS and pool sizing: an innermost middleware answers unhandled exceptions with the JSON envelope and request id (the browser now reads it instead of reporting the server unreachable); an exhausted pool answers 503 after 5 s; pool size, overflow and timeout are settings documented in OPERATIONS.

- US-043 Layout audit fixes (`docs/reviews/LAYOUT_AUDIT.md`, all High, Medium and Low items): operator table stacked until `lg`, queue six columns from `2xl`, case sheet labels stacked at `lg`, audit trail stacked until `xl`, review rail scrolls inside the viewport and renders first on phones, stepper labels no longer collide, alert actions wrap under the text on phones, 40 px tap targets on phones, evidence quotes wrap, shorter search placeholders, filename and acronym copy, decided applications skip the confirmation page. From user feedback: no hover sweep on secondary and ghost buttons, Review card padding, Document checks without underlines, application card no longer stretches, and a note that the site visit steps change the status only.

- US-046 Sign-in: show/hide password toggle inside the field (accessible name, never submits); the helper text about the attempt limit and shared sign-in removed (the limiter and its 429 message stay).

- US-045 Delete draft: `DELETE /applications/{id}` removes a never-submitted draft with its files, runs and audit events (409 once submitted, ownership enforced); the application page offers Discard draft (nothing entered) or Delete draft behind a danger dialog. Same branch fixes the Declarations dead end on resubmission: re-confirming stamps `confirmed_at`, which the diff reports as "Confirmed on", so feedback on Declarations can be answered.

- US-039 Feedback decisions made safe: Mark resolved is offered only for items the operator has seen (409 for an unsent draft, which can only be withdrawn); Withdraw and Mark resolved toasts carry Undo for 10 s backed by `POST .../feedback/{fid}/restore` (own decision, 15 s server window, state still valid, audited as `feedback.restored`, migration 0004 `previous_resolution`); the composer closes itself when the case locks; item actions sit on their own row on phones. Toast component gains an action slot.

- US-040 and US-041 Respond-to-feedback flow recalibrated: Save and continue walks only the flagged targets (next flagged section, then documents if flagged, then the application page where Resubmit lives), locked sections show a lock in the rail and the stepper and cannot be opened from them, flagged sections read Flagged / Changed, the form carries a readiness banner, the application page shows "Ready to resubmit: n of m changed" above the feedback notice and each changed item reads "Changed, ready to resubmit". Reported from a phone screenshot where every section showed a green dot and Save and continue landed on a locked section.

- US-038 Withdraw application: new terminal status `withdrawn` reachable by the owner from every post-submission, non-terminal state (`POST /applications/{id}/withdraw`, optional reason up to 1000 characters, migration 0003 `withdrawal_reason`); audited with the operator as actor; every active officer notified with the reason; operator page offers Withdraw application in a danger dialog and shows a neutral outcome panel afterwards; officer case shows "Withdrawn by the operator: reason" and no actions; queue groups it under Decided. State machine tests extended (every state × target × actor still enumerated), six integration tests, one component test.

- US-037 Phone width fit and scroll to top (hotfix from iPhone 12 Pro screenshots): every responsive grid declares a base column so long file names and button rows no longer widen the page; `ScrollRestoration` in the shell (new pages open at the top, Back and Forward restore the position); the notifications popover spans the header on phones and the unread badge sits clear of the bell. Measured `scrollWidth` on every route at 390 and 820.

- US-036 Search in My applications and the review queue (client-side over reference, business, address, applicant) with a Clear search empty state; US-035 side rail reaches the bottom of the window while scrolling (rail column spans the page, nav sticks top, footer sticks bottom).

- US-005 Critical journey E2E: Playwright runs the whole loop in Chromium against the running stack (apply, upload, submit, flag, request resubmission, fix only the flagged section, resubmit, compare, resolve, site visit, approve). `docs/testing/TEST_STRATEGY.md` written. Vitest scoped to `src` so the two runners stay apart. Fixed a redirect race on the review page between a successful submit and the confirmation page.

### Milestones during the sprint (Sprint 2)

- US-033 and US-034 Edge-case pass (three independent reviews, every finding and its fix or plan in `docs/reviews/EDGE_CASE_REVIEW.md`). Frontend (US-033): any 401 ends the session in one place and the sign-in page explains it; the token expiry signs out proactively; a network blip on reload no longer logs the user out; browser prompt on refresh or close with unsaved section input; Sign out asks first when a form is dirty; "Save and exit" saves the partial draft; a dirty section is never overwritten by another tab's save; submit is guarded against double fire and explains a 409; review and submitted pages redirect when the application is not in the right state; locked applications show no editing chrome; polling stops after 3 minutes and offers Re-run; Replace is hidden while a check runs; Re-run needs an editable slot; download errors surface as toasts; confirmation dialogs focus Cancel when destructive; over-promising copy removed ("10 working days", "by email"). Backend (US-034): login limiter keyed on the socket address with `TRUSTED_PROXIES`, no reset on success, constant-cost unknown email; `Content-Length` refused before the multipart body is read and no `.part` leftovers; RFC 5987 download names and 404 for missing files; `NaN` is a 422; injection beats model-declared unreadable; stale `pending` runs failed at startup and atomic run claim; re-run under row lock with `verification.requested` audit; `section.updated` audit with field names only; fixed error-reason vocabulary; notifications delivered after commit; batched operator list; admin download closed until US-072.

- US-002 OpenAI provider + US-003 injection and malformed output: `AI_PROVIDER=openai` run live with `gpt-4.1-mini` (new default; measured against `gpt-4o-mini` and `gpt-5-mini`). The first live call exposed two defects, both fixed: the wire schema used plain strings so the model invented status, severity and code values (now pinned as JSON-schema enums and listed in the prompt, unit-tested), and the prompt carried no date so an expired certificate passed (today's date is now in the user message). Six live cases recorded in `docs/ai/AI_VERIFICATION_DESIGN.md`; an end-to-end upload through the API stored `provider=openai, model=gpt-4.1-mini`. The test suite now forces the mock provider regardless of `.env` (`TEST_LIVE_AI=1` opts in), after the first full run with the live key took four minutes and failed one assertion. US-003's criteria are met by the injection heuristic (now applied before the model's `unreadable` verdict), the strict wire and domain models (`raw_output_valid=false` on any malformed output) and the confidence bounds.

- US-031 Site visit and outcome: the officer rail drives Schedule site visit → Mark site visit done → Route to approval → Approve (note optional) or Reject (note required) through the transition endpoint; the decision note is stored and served to the operator only with the final outcome; operator application page shows an outcome panel with the note; nothing can follow a decision (409). Covered by outcome and rejection tests and a browser run of the full path.

- US-029 Audit trail + US-019 Operator history: `GET /officer/applications/{id}/audit` serves every event in order with actor name and role, a plain-language summary from `domain/audit_labels.py` and the payload; covered by a whole-journey sequence test (create → sections → uploads → checks → submit → review → feedback → release → resubmit → addressed → resolved). Operator views carry the revision list; `/app/applications/{id}/history` shows revisions, "what changed from Revision N-1" (owner-side compare) and every released feedback item by round. Case page gains a collapsible, filterable audit trail.

- Tidy pass (audit by a read-only agent, 23 findings, all behaviour-neutral): Pydantic schemas moved from `app/api/v1/*_schemas.py` to `app/schemas/` so services no longer import the API layer (new layering tests); shared test journeys in `tests/journeys.py` replace cross-imports between test modules; dead helpers removed (`pending_runs`, limiter `reset`, `count_for_operator`, backend `ALLOWED_EXTENSIONS`); `PROMPT_VERSION` recorded in the verification audit payload; Vite template stylesheet, unused assets and `api/health.ts` removed; `Breadcrumb` in its own file; internal exports made private; `.gitignore` covers `data/`, `*.part`, coverage and generated prototype output; README status and AI verification section; artboard count and docs index corrected.

- US-026, US-027, US-028 Officer resubmission review: officers are notified on resubmission and the queue shows "Review resubmission"; `domain/diff.py` (field-level form diff bound to the schema, documents by sha256) behind `GET /applications/{id}/compare?from&to` for owner or officer; the officer view carries `changed_sections`, `changed_document_types`, `previous_revision_number` and `addressed_unresolved_count`; `POST .../feedback/{fid}/resolve` (open or addressed → resolved, audited). Frontend: resubmitted banner, Changed / Replaced markers, compare panel with any-two-revision selectors (SCOPE S4 landed), "Addressed in Revision N" badges and Mark resolved, warning while addressed items stay unresolved.

- US-016, US-017, US-018 Operator resubmission: the operator view lists released feedback only (never drafts or pre-release withdrawals, never the author) with resolution and round; editability now comes from open released feedback (`ApplicationService.editable_for`), so non-flagged sections and documents return 403 with a plain reason; `resubmit` readiness reports changed and untouched flagged targets; `POST /applications/{id}/resubmit` creates Revision N+1, marks changed items addressed, audits and notifies officers (422 `no_change`, 409 when the state moved). Frontend: feedback notice on top of the application with links to each target, inline officer comments on the flagged section and document slot, locked-with-reason on the rest, Respond to feedback and Resubmit actions with a confirmation that names untouched items, "Changes resubmitted" confirmation page. Verified with a full officer → operator → officer loop in the browser.

- US-025 Status transitions + operator notification, US-032 operator sees only the outcome: the transition endpoint (US-021) now covers every officer edge with guards (request resubmission needs an open item and releases the round, site visit needs none, reject needs a note, stale version 409); every transition writes an operator notification in the same transaction with the operator label only; `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all` (own items only); operator views carry `needs_operator_action` so the dashboard no longer infers it from a colour. Frontend: bell with unread count and popover in the shell for every role. US-032 is satisfied by the serializer (operator views never carry the internal code; "Pending Approval" is the operator wording for the approval stage), covered by tests.

- US-023 Contextual feedback + US-024 Comment templates: `Feedback` rows tied to a section key or a document type, created and withdrawn only while Under Review (409 otherwise), audited (`feedback.created`, `feedback.withdrawn`); seven templates in `domain/feedback_templates.py` served by `GET /officer/feedback-templates`; the officer view lists items by round with author, resolution and release state, and reports `feedback_editable` with a reason; requesting a resubmission releases every open item (`released_to_operator_at`, `feedback.released`). Frontend: feedback rail with composer (template fills target and message), Withdraw, inline "n open feedback" markers on sections and documents, Request resubmission becomes the primary action once an item is open.

- US-022 AI results beside each document (officer): delivered by the case view (`CheckResult`: status, confidence, model, summary, issues with code, field and evidence, missing information, fixed error reasons) plus an officer re-run endpoint and button; the case polls every 2 s while a check runs.

- US-021 Officer case view + Start review: `GET /officer/applications/{id}` serves the submitted revision's sections (never the working copy), current documents with full check detail (confidence, evidence, model), revision history and the transitions available now with guard reasons; `POST /officer/applications/{id}/transition` locks the row, checks `expected_version` (409), runs `domain/workflow.transition` (409 with allowed targets), writes `status.changed` with the officer as actor and notifies the operator in the same transaction. Frontend case workspace: key facts strip, submission sheet, documents with `CheckResult`, revision history, sticky review rail with server-driven actions, confirmation dialogs (note required to reject), stale-version reload banner. Verified in Chrome as the officer at 1440, 820 and 390.

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
