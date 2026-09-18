# PermitFlow — User Stories

This file and the Notion board ("PermitFlow — Xtremax Assessment" → Epics / Stories) are kept in sync: same epic names, same story IDs, same titles. Priority values match the Notion `Priority` select (MVP, Nice-to-have, Deferred, Mocked). Requirement IDs refer to `docs/requirements/REQUIREMENTS.md`; use cases UC0-A … UC4-A refer to `docs/requirements/USE_CASES.md` (grouped by the same epics). Definition of Done: `DEFINITION_OF_DONE.md`.

Story format: **US-xxx — As a [user], I want [capability], so that [value].**

---

## E0 — Foundation, AI Pipeline & Delivery

### US-000 — As an engineer, I want a runnable backend, frontend and database skeleton, so that every feature builds on a working base.
- Acceptance criteria: `docker compose up` starts Postgres; `alembic upgrade head` creates the schema; `GET /api/v1/health` returns 200 with database status and 503 when the database is down; every error (including FastAPI's own 401/403/422) uses `{ "error": { "code", "message", "details"? } }` via explicit exception handlers; security headers and CORS allowlist are set; the app refuses to start without `JWT_SECRET` outside the test environment; the frontend dev server renders the app shell; CI skeleton runs lint and type checks.
- Priority: MVP · Day 1 · Dependencies: none · Requirements: NFR-001, NFR-005, REL-006
- Definition of Done: DoD checklist + a clean clone runs with the README steps.

### US-001 — As an operator, officer or admin, I want to log in with my email and password and land in my own workspace, so that each persona works in the screens meant for it.
- Acceptance criteria: seeded operator and officer accounts (the admin account is seeded with US-070); wrong credentials return a generic 401; JWT contains the role claim; `GET /auth/me` returns the current user; after login an operator lands on the operator dashboard, an officer on the review queue and an admin (when E4 is built) on the operations dashboard; protected routes redirect to login; a route for another role shows "Not available for your role" and the API returns 403; more than 10 *failed* attempts per minute per IP returns 429 (configurable, disabled in tests).
- Priority: MVP · Day 1 · Dependencies: US-000 · Requirements: FR-028, SEC-006, SEC-010 · Use case UC0-A
- Definition of Done: DoD checklist + auth tests (401, 429, role claim).

### US-002 — As the system, I want an AI verification pipeline behind a provider interface, so that documents are checked consistently and the provider can be replaced.
- Acceptance criteria: text extraction for PDF and TXT; empty text becomes `unreadable` with no model call; `VerificationProvider` protocol with `OpenAIProvider` (structured outputs) and `MockProvider`; provider chosen by `AI_PROVIDER`; output validated by a strict Pydantic model; confidence threshold rule; 30 s timeout with one retry; failures recorded as data, never raised; stale `running` runs marked `failed` on startup; runs in a background task after upload.
- Priority: MVP · Day 1 (mock, done), Day 2 (OpenAI; slipped from Sprint 1 as planned) · Dependencies: US-012 · Requirements: AI-001…AI-007, AI-009, REL-003, REL-004 · ADR-004, ADR-006
- Definition of Done: DoD checklist + pipeline integration test with the mock provider; provider-raising test.

### US-003 — As the system, I want to flag suspicious document content and reject malformed model output, so that officers are not misled by prompt injection or hallucinated results.
- Acceptance criteria: instruction-like phrases in extracted text add a `possible_prompt_injection` issue; malformed, partial or extra-field output produces a `failed` run with `raw_output_valid = false`; confidence outside 0–1 is rejected.
- Priority: MVP · Day 2 · Dependencies: US-002 · Requirements: AI-003, SEC-008 · Threat model T5, T6
- Definition of Done: DoD checklist + unit tests for each malformed case and the heuristic.

### US-004 — As an engineer, I want a small AI evaluation set with expected outcomes, so that provider behaviour can be checked and documented honestly.
- Acceptance criteria: six cases (valid, wrong document type, missing information, ambiguous, empty, prompt injection); a runner script prints a results table; results recorded in `docs/ai/AI_EVALUATION.md`.
- Priority: Nice-to-have · Day 3 · Dependencies: US-002 · Requirements: AI-008
- Definition of Done: runner executes against mock and OpenAI providers; document updated.

### US-005 — As an engineer, I want unit, integration and end-to-end tests for the critical journey, so that regressions are caught before they ship.
- Acceptance criteria: unit tests for the state machine (every state/target/role), labels, diff, editability, AI validation; integration tests for the full loop and authorization; one Playwright journey (submit → flag → fix only flagged → resubmit → compare); all green in CI.
- Priority: MVP · Day 1–3 (continuous) · Dependencies: US-000 · Requirements: all · `docs/testing/TEST_STRATEGY.md`
- Definition of Done: CI green with all layers.

### US-006 — As an engineer, I want a CI pipeline that lints, type-checks, tests, builds and scans for secrets, so that broken or unsafe code is never considered done.
- Acceptance criteria: GitHub Actions workflow runs frontend lint/typecheck/test/build, backend ruff/mypy/pytest on a Postgres service, Playwright E2E, gitleaks and a Docker build; required on pull requests.
- Priority: MVP · Day 1 (skeleton), Day 3 (complete) · Dependencies: US-000 · Requirements: NFR-004, NFR-005
- Definition of Done: branch protection requires the workflow; green on `main`.

### US-007 — As a reviewer, I want the application deployed with seeded accounts, so that I can try it without local setup.
- Acceptance criteria: Railway backend (Docker, volume for uploads), managed Postgres and static frontend; migrations and seed run on deploy; `/health` green; deployment separate from CI.
- Priority: MVP · Day 3 · Dependencies: US-006 · Requirements: NFR-006 · `docs/operations/OPERATIONS.md`
- Definition of Done: UAT executed on the deployed URL.

### US-008 — As a reviewer, I want clear documentation of scope, architecture, AI usage, testing and operations, so that every decision is explainable.
- Acceptance criteria: README (setup, env vars, tests, AI usage, what I would do next), SCOPE.md, ADRs, threat model, test strategy, UAT plan, operations guide, production readiness review, assessment traceability, CHANGELOG.
- Priority: MVP · Day 3 (continuous) · Dependencies: all
- Definition of Done: every document reflects the implemented system; no fake content.

### US-009 — As the team, I want a reviewed UI design system and clickable prototype before implementation, so that every screen is built from an agreed, requirement-traced design.
- Acceptance criteria: design direction, tokens and type scale; screen inventory with IDs, personas, requirements and states; operator and officer flows; component inventory; UI state inventory including the upload → verification lifecycle; frontend architecture; requirement traceability; a clickable prototype covering login, operator submission, resubmission, officer review, feedback, compare, audit, admin, phone and tablet; two independent design-critique passes with findings applied; brand mark and logo.
- Priority: MVP · Design phase (17–18 Sep) · Dependencies: US-000 docs · Requirements: UX-001…UX-008 · `docs/design/`
- Definition of Done: `docs/design/README.md` links the prototype; every screen in the inventory exists on the canvas; no contradiction with STATE_MACHINE or DOMAIN_MODEL.

---

### US-034 — As the system, I want login, upload, verification and audit hardened against the near-misses found in review, so that abuse and restarts cannot corrupt or stall an application.
- Acceptance criteria: the login limiter keys on the socket address and honours `X-Forwarded-For` only from `TRUSTED_PROXIES`; a successful login does not reset the failure window; unknown emails cost the same hash check; an upload whose `Content-Length` exceeds the cap is refused before the body is read and rejected uploads leave no partial file; downloads work for any file name and return 404 when the file is missing; `NaN` in a number field is a 422; injection phrases are flagged even when the model calls the document unreadable; runs left `pending` by a restart are failed on startup and the pending-to-running claim is atomic; re-run takes the row lock and is audited; section saves are audited with field names only; error reasons served to clients come from a fixed vocabulary; notifications are delivered only after the commit; admin cannot download documents until US-072 grants it.
- Priority: MVP · Day 2 · Dependencies: US-001, US-012, US-002 · Requirements: SEC-005, SEC-010, REL-003, AUD-001 · Threat model T4, T5, T13 · Source: `docs/reviews/EDGE_CASE_REVIEW.md` items 17 to 31 · Branch `fix/us-034-backend-edge-cases`
- Definition of Done: DoD checklist + `tests/integration/test_edge_cases.py` (11 regression tests).

### US-035 — As an operator or officer, I want the side rail to reach the bottom of the window while I scroll, so that the workspace never shows a broken edge.
- Acceptance criteria: after scrolling past the top notice bar the side rail still ends at the bottom of the window with its footer visible; holds on every operator and officer screen, expanded and collapsed; short pages gain no scrollbar.
- Priority: MVP · Day 3 (hotfix, added 19 Sep from a screenshot) · Dependencies: US-001 · Requirements: UX-001 · Branch `fix/rail-gap`
- Definition of Done: Playwright measurement on dashboard, my applications, application, history, queue and case: rail bottom equals viewport height.

### US-036 — As an operator or officer, I want to search my list by reference, business, address or applicant, so that I can open the right application without scrolling.
- Acceptance criteria: My applications and the review queue carry a search box beside the status tabs; matching is case-insensitive and every word of the query must appear in the reference, business name, premises address or (officer only) applicant name; search combines with the active tab; no match shows the query and a Clear search action; fits 1440, 820 and 390.
- Priority: Nice-to-have · Day 3 (added 19 Sep on request) · Dependencies: US-020, US-010 · Requirements: UX-003 · Branch `feat/us-036-list-search` · Client-side over the loaded list, same pattern as SCOPE S1
- Definition of Done: unit test for the matcher, component tests on both pages, screenshots at three widths.

### US-037 — As an officer or operator on a phone, I want every screen to fit the width of the phone and every navigation to open at the top of the page, so that I never scroll sideways or land mid-page.
- Acceptance criteria: the officer case page (documents, check results, compare panel, revision history, review rail) and the operator dashboard fit 390 px with no horizontal scroll; the notifications popover fits the phone width below the header and the unread badge does not cover the bell; opening a new page scrolls to the top while Back and Forward keep the browser's remembered position; verified on every operator and officer route at 390 and 820.
- Priority: MVP · Day 3 (hotfix, added 19 Sep from iPhone 12 Pro screenshots) · Dependencies: US-021 · Requirements: UX-001 · Branch `fix/us-037-phone-layout`
- Definition of Done: Playwright measurement of `scrollWidth` on every route at 390; scroll position check after navigation.

## UC1 — Operator Submission & Resubmission

### US-010 — As an operator, I want to create a new licence application, so that I can start my submission.
- Acceptance criteria: `POST /applications` creates a `draft` with a human-readable reference number; it appears on my dashboard labelled "Draft"; another operator requesting it receives 404.
- Priority: MVP · Day 1 · Dependencies: US-001 · Requirements: FR-001, SEC-002 · Use case UC1-A
- Definition of Done: DoD checklist + ownership test.

### US-011 — As an operator, I want to complete a sectioned form with inline validation and save my progress, so that I can enter accurate information over time.
- Acceptance criteria: sections and fields come from `GET /form-schema`; each section validates with Zod on the client and Pydantic on the server; `PATCH /applications/{id}/sections/{key}` saves one section; invalid data returns 422 with field errors; reloading shows saved values.
- Priority: MVP · Day 1 · Dependencies: US-010 · Requirements: FR-002, FR-003, SEC-007, UX-003 · Use case UC1-A
- Definition of Done: DoD checklist + validation parity test.

### US-012 — As an operator, I want to upload documents by drag-and-drop and tag each with its type, so that my supporting documents are attached to the application.
- Acceptance criteria: drop zone and file picker; document type selector; allowlisted types (PDF, PNG, JPEG, TXT) and 10 MB limit with clear errors; magic-byte check; replacing a type supersedes the previous file; the owner can download.
- Priority: MVP · Day 1 · Dependencies: US-010 · Requirements: FR-004, SEC-005 · Use case UC1-A
- Definition of Done: DoD checklist + upload rejection tests; wrong-owner download returns 404.

### US-013 — As an operator, I want to see each document's AI verification status update in real time, so that I know about problems before I submit.
- Acceptance criteria: after upload the card shows "Verifying…"; without a page reload it changes to Verified / Issues found (n) / Needs review / Unreadable / Failed / Unavailable; summary and issues are expandable. (Re-run action is SCOPE S2, not required for this story.)
- Priority: MVP · Day 2 (pipeline Day 1) · Dependencies: US-012, US-002 · Requirements: FR-005, AI-002, AI-006 · Use case UC1-A
- Definition of Done: DoD checklist + E2E asserts the card changes state without reload.

### US-014 — As an operator, I want a progress indicator of overall completion, so that I know what remains before I can submit.
- Acceptance criteria: percentage plus a checklist of sections (valid/invalid) and required document types (present/missing); computed by the server (`completeness`) so the UI and the submit guard agree.
- Priority: MVP · Day 1 · Dependencies: US-011, US-012 · Requirements: FR-006 · Use case UC1-A
- Definition of Done: DoD checklist + completeness unit test.

### US-015 — As an operator, I want to submit my completed application, so that an officer can review it.
- Acceptance criteria: Submit is disabled until complete; the server re-validates and returns 422 listing gaps; success creates Revision 1, status label "Submitted", the form becomes read-only, officers are notified, audit events are recorded.
- Priority: MVP · Day 1 · Dependencies: US-014 · Requirements: FR-007, AUD-001, AUD-005, REL-002 · Use case UC1-A
- Definition of Done: DoD checklist + atomic submission integration test.

### US-016 — As an operator, I want to see the status "Pending Pre-Site Resubmission" and the officer's comments prominently at the top of my application, so that I immediately understand what is being asked.
- Acceptance criteria: status badge shows the operator label; a feedback panel above the form lists every released open item with its target, message, author role and round; resolved items are shown collapsed; feedback the officer is still drafting or withdrew before release is never returned to the operator.
- Priority: MVP · Day 2 · Dependencies: US-015, US-023, US-025 · Requirements: FR-009, FR-008 · Use case UC1-B
- Definition of Done: DoD checklist + operator view test (labels, feedback present, no internal fields).

### US-017 — As an operator, I want each feedback item linked to the specific form section or document it concerns, so that I know exactly where to make changes.
- Acceptance criteria: every feedback item carries a section key or a document type; clicking an item scrolls to and highlights its target; the target shows an inline marker with the comment.
- Priority: MVP · Day 2 · Dependencies: US-016 · Requirements: FR-010, UX-004 · Use case UC1-B
- Definition of Done: DoD checklist + anchoring covered in E2E.

### US-018 — As an operator, I want to update only the flagged sections and documents and resubmit, so that I do not re-enter the entire application.
- Acceptance criteria: only sections and document types with open feedback are editable; other sections are read-only and carried forward; editing a non-flagged section via the API returns 403; Resubmit creates Revision N+1, status becomes "Pre-Site Resubmitted", officers are notified; resubmitting with no change to any flagged target returns 422.
- Priority: MVP · Day 2 · Dependencies: US-017 · Requirements: FR-011, FR-012, FR-013 · ADR-007 · Use case UC1-B
- Definition of Done: DoD checklist + editability and resubmission integration tests.

### US-019 — As an operator, I want to see my revision history and all previous officer comments, so that nothing is lost between rounds and I understand the full context.
- Acceptance criteria: a History tab lists every revision with its timestamp and every released feedback item with its state and round; three rounds produce three revisions; Revision 1 is unchanged after Revision 3.
- Priority: MVP · Day 2 · Dependencies: US-018 · Requirements: FR-013, FR-014, AUD-001 · Use case UC1-C
- Definition of Done: DoD checklist + multi-round integration test.

---

### US-033 — As an operator, I want my unsaved work and my session protected from refreshes, expiry and other tabs, so that I never lose what I typed or get stuck on a dead page.
- Acceptance criteria: a 401 from any request ends the session in one place and the sign-in page explains it, keeping the return path only within the role's own area; the token expiry signs out proactively; a network blip on reload does not sign out; refreshing or closing the tab with unsaved section input triggers the browser prompt; Sign out and in-app navigation ask first when a form is dirty; "Save and exit" saves the partial draft; a dirty section is never overwritten by another tab's save; submit cannot double-fire and a 409 is explained; the review and confirmation pages redirect when the application is not in the right state; locked applications show no editing chrome; polling stops after 3 minutes and offers Re-run; Replace is hidden while a check runs; download errors are shown; destructive dialogs focus Cancel; copy makes no promise the system cannot keep.
- Priority: MVP · Day 2 · Dependencies: US-011, US-015 · Requirements: SEC-006, UX-002, REL-005 · Source: `docs/reviews/EDGE_CASE_REVIEW.md` items 1 to 16 · Branch `fix/us-033-operator-edge-cases`
- Definition of Done: DoD checklist + `lib/unsaved.test.ts`, `queries.test.ts`, Chrome check of the sign-out guard and Save and exit.

### US-038 — As an operator, I want to withdraw my submitted application with an optional reason, so that the licensing office stops working on something I no longer need.
- Acceptance criteria: Withdraw is available to the owner from every post-submission, non-terminal status; drafts are simply left and decided applications cannot be withdrawn (409); optional reason (up to 1000 characters) stored with the application, shown to the officer on the case and to the operator in an outcome panel; Withdrawn is a terminal status labelled Withdrawn for both roles and nothing can be edited, resubmitted or transitioned afterwards; officers are notified in-app; the audit trail records the status change with the operator as actor; officers and admins get 403.
- Priority: Nice-to-have · Day 3 (added 19 Sep on request) · Dependencies: US-015, US-025 · Requirements: FR-032 · `docs/architecture/STATE_MACHINE.md` · Branch `feat/us-038-withdraw-application`
- Definition of Done: state machine tests cover the new edges; `tests/integration/test_withdrawal.py`; `ApplicationPage.test.tsx`; browser check on both sides; STATE_MACHINE, DOMAIN_MODEL, ARCHITECTURE, REQUIREMENTS, SCOPE, USE_CASES, SCREEN_INVENTORY, UI_STATES, USER_JOURNEY updated.

### US-040 — As an operator responding to feedback, I want the flagged sections marked with a warning in the form rail and the stepper, so that I can see at a glance where the officer asked for changes.
- Acceptance criteria: while the application is Pending Pre-Site Resubmission, sections with open released feedback show a warning marker (dot plus label, never colour alone) in the form rail, the stepper and the documents row; untouched sections keep their complete marker but are visibly locked; the marker becomes an addressed marker once the section changed in this round; fits 1440, 820 and 390.
- Priority: MVP · Day 3 (added 19 Sep from a phone screenshot) · Dependencies: US-017 · Requirements: FR-011, UX-003 · Branch `feat/us-040-flagged-markers`
- Definition of Done: component test for the rail markers; browser check on the resubmission flow.

## UC2 — Officer Review & Feedback

### US-020 — As an officer, I want a review queue of all submitted applications with their internal status, so that I can pick what to review next.
- Acceptance criteria: `GET /officer/applications` lists non-draft applications with internal status and officer label, applicant, reference, revision count, open feedback count and last activity; empty state; operators receive 403. (Status filter is SCOPE S1.)
- Priority: MVP · Day 2 · Dependencies: US-015 · Requirements: FR-015, SEC-003 · Use case UC2-A
- Definition of Done: DoD checklist + role test.

### US-021 — As an officer, I want to open the full submission with all form data and documents in an organised structure, so that I can review efficiently.
- Acceptance criteria: sections rendered from the schema; document cards per type with download; "Start review" moves Application Received or Pre-Site Resubmitted to Under Review and records the actor.
- Priority: MVP · Day 2 · Dependencies: US-020 · Requirements: FR-016, FR-019 · Use case UC2-A
- Definition of Done: DoD checklist + start-review transition test.

### US-022 — As an officer, I want to see AI verification results and flagged document issues beside each document, so that I can focus on likely problems first.
- Acceptance criteria: each document shows status, confidence, summary, issues with severity and evidence, and missing information; failed or unavailable runs are shown explicitly; re-run action available.
- Priority: MVP · Day 2 · Dependencies: US-021, US-002 · Requirements: FR-017, AI-005 · Use case UC2-A
- Definition of Done: DoD checklist + officer view includes verification data.

### US-023 — As an officer, I want to request more information with comments tied to a specific section or document, so that the operator receives actionable feedback.
- Acceptance criteria: target selector (section or document type); message required; items listed with target, author, round and state; an open item can be withdrawn; create and withdraw are allowed only while the application is Under Review (409 otherwise); operators receive 403 on the endpoint.
- Priority: MVP · Day 2 · Dependencies: US-021 · Requirements: FR-018, FR-010, AUD-003 · Use case UC2-A
- Definition of Done: DoD checklist + feedback CRUD tests.

### US-024 — As an officer, I want predefined comment templates for common issues, so that I give consistent feedback quickly.
- Acceptance criteria: `GET /feedback-templates` returns templates with target type and body; selecting a template fills the message, which remains editable; the template key is stored with the feedback.
- Priority: MVP · Day 2 · Dependencies: US-023 · Requirements: FR-018 · Use case UC2-A
- Definition of Done: DoD checklist + template endpoint test.

### US-025 — As an officer, I want to set the application status through allowed transitions and have the operator notified automatically, so that the case moves forward without manual follow-up.
- Acceptance criteria: only allowed targets for the current state are offered; Request resubmission requires at least one open feedback item and releases the round's feedback to the operator; Schedule site visit requires no `open` items; Reject requires a note and is available from every non-terminal post-submission state; invalid transitions return 409 and stale `expected_version` returns 409; the operator receives an in-app notification carrying the operator label; email delivery is mocked (logged).
- Priority: MVP (notification delivery: Mocked) · Day 2 · Dependencies: US-023 · Requirements: FR-019, FR-020, SEC-004, REL-007, AUD-002 · ADR-003 · Use case UC2-A
- Definition of Done: DoD checklist + transition and notification tests.

### US-026 — As an officer, I want to be notified when a case moves to "Pre-Site Resubmitted", so that I can review the resubmission promptly.
- Acceptance criteria: resubmission creates an in-app notification for officers; the notification bell shows an unread count; the item links to the application; mark-as-read works; email delivery is mocked.
- Priority: MVP (delivery: Mocked) · Day 2 · Dependencies: US-018 · Requirements: FR-021 · Use case UC2-B
- Definition of Done: DoD checklist + notification test on resubmit.

### US-027 — As an officer, I want updated sections highlighted and a way to compare the current submission with previous versions, so that I review only what changed.
- Acceptance criteria: sections and documents that differ from the previous revision carry a "Changed" marker (documents compared by content hash); `GET /applications/{id}/compare?from&to` returns field-level old/new values and document add/remove/replace; the compare view shows current vs previous (any-two-revisions selector is SCOPE S4); single-revision applications show a disabled compare with an explanation.
- Priority: MVP · Day 2 · Dependencies: US-018 · Requirements: FR-022, FR-023, UX-006 · ADR-007 · Use case UC2-B
- Definition of Done: DoD checklist + diff unit tests and compare endpoint test.

### US-028 — As an officer, I want to see whether each previously flagged issue was addressed and mark it resolved, so that nothing is forgotten across rounds.
- Acceptance criteria: feedback whose target changed in the new revision is automatically "Addressed (rev N)"; I can mark an item Resolved; unaddressed items stay Open; states and rounds are visible to both roles.
- Priority: MVP · Day 2 · Dependencies: US-027 · Requirements: FR-024, AUD-003 · Use case UC2-B
- Definition of Done: DoD checklist + resolution lifecycle test.

### US-029 — As an officer, I want a complete audit trail of feedback and resubmission rounds, so that every action on an application is accountable.
- Acceptance criteria: a History tab lists events in order with type, actor, timestamp and payload summary; covers submissions, status changes, feedback lifecycle, document uploads and verification outcomes; no edit or delete exists; operators receive 403 on the endpoint.
- Priority: MVP · Day 2 · Dependencies: US-025 · Requirements: FR-025, AUD-001…AUD-006, SEC-009 · ADR-008 · Use case UC2-D
- Definition of Done: DoD checklist + event sequence test for the whole journey.

### US-030 — As a user, I want to see the status label that matches my role, so that operators and officers each see the wording defined for them.
- Acceptance criteria: every status in the assessment table maps to the officer label and the operator label exactly; the operator API returns only the operator label (never the internal code); the officer API returns the internal code and officer label.
- Priority: MVP · Day 1 · Dependencies: US-000 · Requirements: FR-008, FR-026 · ADR-003, ADR-005
- Definition of Done: DoD checklist + label table unit test against the assessment.

### US-031 — As an officer, I want to schedule and complete a site visit, route the case to approval and approve or reject it with a note, so that applications reach a final outcome.
- Acceptance criteria: transitions follow `STATE_MACHINE.md`; the decision note is stored and shown to the operator on Approved/Rejected; because UC3 is deferred, Site Visit Done may go directly to Pending Approval.
- Priority: MVP · Day 2 · Dependencies: US-025 · Requirements: FR-027 · Use case UC2-C
- Definition of Done: DoD checklist + outcome transition tests.

### US-032 — As an operator, I want to see only the final outcome (Approved or Rejected) and never the internal approval stage, so that internal processing is not exposed to me.
- Acceptance criteria: an application in Pending Approval shows "Pending Approval" to me and "Route to Approval" to officers; my API responses contain no internal status codes, audit events or officer-only notes; enforced by separate response models.
- Priority: MVP · Day 2 · Dependencies: US-030 · Requirements: FR-026, SEC-001 · ADR-005 · Threat model T3
- Definition of Done: DoD checklist + schema test asserting field absence.

---

## E4 — Admin Oversight & Monitoring

Not in the assessment brief; added as a product decision (SCOPE.md, S7). Read-only on applications.

### US-070 — As an admin, I want an operations dashboard with application counts by status, idle applications and today's submissions, so that I can see whether anything is stuck.
- Acceptance criteria: `GET /admin/overview` returns counts per internal status, applications with no activity for more than 7 days (reference, status, days idle), and submissions/resubmissions today; dashboard renders them with loading, empty and error states; operators and officers receive 403.
- Priority: Nice-to-have · Day 3 · Dependencies: US-001, US-029 · Requirements: FR-029, FR-030, SEC-003 · Use case UC4-A
- Definition of Done: DoD checklist + role test + overview endpoint test.

### US-071 — As an admin, I want an AI verification health panel, so that I know whether document verification is working and how it performs.
- Acceptance criteria: runs in the last 24 h, counts by outcome, failure/unavailable rate, average and p95 latency, provider and model in use; "Provider: none (mock)" when no key is configured.
- Priority: Nice-to-have · Day 3 · Dependencies: US-070, US-002 · Requirements: FR-029, NFR-007 · Use case UC4-A
- Definition of Done: DoD checklist + metrics endpoint test with seeded runs.

### US-072 — As an admin, I want a cross-application audit feed and read-only access to any application, so that I can investigate issues without database access.
- Acceptance criteria: latest 50 audit events across all applications with actor, type, application reference and time; clicking opens the application in the officer view with all actions hidden and the API rejecting admin mutations with 403.
- Priority: Nice-to-have · Day 3 · Dependencies: US-070 · Requirements: FR-030, AUD-006 · Use case UC4-A
- Definition of Done: DoD checklist + admin mutation returns 403 test.

### US-073 — As an admin, I want to manage users (create, change role, deactivate), so that I control who has access and in which role.
- Acceptance criteria: `GET /admin/users` lists users with name, email, role, active flag, created and last-active; `POST /admin/users` creates a user with a role (email unique, 409 on duplicate); `PATCH /admin/users/{id}` changes role and/or deactivates/reactivates; a change that would leave no active admin returns 409; an admin cannot change their own role; every change writes an audit event (`user.created`, `user.role_changed`, `user.deactivated`, `user.reactivated`); deactivated users get 401 on their next request; UI: users table with role filter, Add user drawer, Change role and Deactivate with confirmation; operators and officers receive 403.
- Priority: Nice-to-have · Day 3 · Dependencies: US-070, US-001 · Requirements: FR-030, SEC-003 · Threat model T19 · Use case UC4-A
- Definition of Done: DoD checklist + role test + last-admin protection test + audit event test.

### US-039 — As an officer, I want feedback decisions to be safe and clear: resolve only items the operator saw, undo a withdraw or resolve for 10 seconds, and never see a composer on a locked case, so that I do not make mistakes I cannot take back.
- Acceptance criteria: Mark resolved is offered only for items released to the operator (open after release, or addressed); a draft item that was never sent offers Withdraw only and the API returns 409 for resolving an unreleased item; after Withdraw or Mark resolved a toast offers Undo for 10 seconds, undo restores the previous resolution, is audited (`feedback.restored`) and is refused by the server after the grace window or once the state no longer allows it; the composer closes itself when the case stops being editable and the lock reason is shown instead; item actions sit on their own row on phones.
- Priority: MVP · Day 3 (added 19 Sep from phone screenshots) · Dependencies: US-023, US-028 · Requirements: FR-018, FR-024, AUD-001 · Branch `feat/us-039-feedback-undo`
- Definition of Done: backend tests for the release rule and undo (window, audit, authorization); component test for the toast undo; browser check at 390 and 1440.

## UC3 — On-Site Assessment & Post-Site Clarification (DEFERRED)

Deferred per `SCOPE.md`. The post-site states and transitions exist and are unit-tested in the state machine; the checklist data model and screens are not built.

### US-060 — As an officer, I want to capture site visit findings per checklist item, so that inspections are documented consistently. — Deferred
### US-061 — As an officer, I want to save the checklist as a draft while on site, so that I can finish it later. — Deferred
### US-062 — As an officer, I want to mark individual checklist items as "Need Further Clarification", so that the operator is asked only about those. — Deferred
### US-063 — As the system, I want the case to move automatically to "Awaiting Post-Site Clarification" when the checklist is submitted, so that status stays consistent. — Deferred (transition exists and is tested)
### US-064 — As an operator, I want to see only the flagged checklist items with the officer's comment, so that I am not overwhelmed by the full checklist. — Deferred
### US-065 — As an operator, I want to respond to each flagged item and upload supporting documents, so that I can resolve clarifications efficiently. — Deferred
### US-066 — As a user, I want multiple clarification rounds per item with a full audit trail, so that every exchange is traceable. — Deferred

Production requirements for UC3 are listed in `SCOPE.md` (Deferred / Mocked table).
