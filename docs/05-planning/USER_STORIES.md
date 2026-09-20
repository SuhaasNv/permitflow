# PermitFlow — User Stories

This file and the Notion board ("PermitFlow — Xtremax Assessment" → Epics / Stories) are kept in sync: same epic names, same story IDs, same titles. Priority values match the Notion `Priority` select (MVP, Nice-to-have, Deferred, Mocked). Requirement IDs refer to `docs/02-requirements/REQUIREMENTS.md`; use cases UC0-A … UC4-A refer to `docs/02-requirements/USE_CASES.md` (grouped by the same epics). Definition of Done: `DEFINITION_OF_DONE.md`.

Story format: **US-xxx — As a [user], I want [capability], so that [value].**

---

## E0 — Foundation, AI Pipeline & Delivery

### US-000 — As an engineer, I want a runnable backend, frontend and database skeleton, so that every feature builds on a working base.
- Acceptance criteria: `docker compose up` starts Postgres; `alembic upgrade head` creates the schema; `GET /api/v1/health` returns 200 with database status and 503 when the database is down; every error (including FastAPI's own 401/403/422) uses `{ "error": { "code", "message", "details"? } }` via explicit exception handlers; security headers and CORS allowlist are set; the app refuses to start without a real `JWT_SECRET` in every environment (no fallback secret in the code); the frontend dev server renders the app shell; CI skeleton runs lint and type checks.
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
- Acceptance criteria: a golden set with expected outcomes (built: fourteen cases, the eight demo PDFs plus wrong type, missing information, ambiguous, empty, oversized and two prompt-injection styles) run through the real pipeline by `backend/evals/run.py`; a results table, a JSON report and a pass threshold; the mock run is a blocking CI stage with a configuration audit (since US-056 the "Golden set" stage of `ai-gate.yml`); the OpenAI run is recorded with its date in `docs/07-ai/AI_EVALUATION.md` (since US-054 it runs as `ai-eval.yml`).
- Priority: Nice-to-have · Day 3 · Dependencies: US-002, US-006 · Requirements: AI-008 · Branch `feat/us-004-ai-evaluation`
- Definition of Done: runner executes against mock and OpenAI providers; CI job green; document updated.

### US-005 — As an engineer, I want unit, integration and end-to-end tests for the critical journey, so that regressions are caught before they ship.
- Acceptance criteria: unit tests for the state machine (every state/target/role), labels, diff, editability, AI validation; integration tests for the full loop and authorization; one Playwright journey (submit → flag → fix only flagged → resubmit → compare); all green in CI.
- Priority: MVP · Day 1–3 (continuous) · Dependencies: US-000 · Requirements: all · `docs/08-testing/TEST_STRATEGY.md`
- Definition of Done: CI green with all layers.

### US-006 — As an engineer, I want a CI pipeline that lints, type-checks, tests, builds and scans for secrets, so that broken or unsafe code is never considered done.
- Acceptance criteria: GitHub Actions workflow runs frontend lint/typecheck/test/build, backend ruff/mypy/pytest on a Postgres service, Playwright E2E, gitleaks and a Docker build; required on pull requests.
- Priority: MVP · Day 1 (skeleton), Day 3 (complete) · Dependencies: US-000 · Requirements: NFR-004, NFR-005
- Definition of Done: branch protection requires the workflow (in place since 20 Sep 2026: `main` takes pull requests only, seven required checks); green on `main`.

### US-007 — As a reviewer, I want the application deployed with seeded accounts, so that I can try it without local setup.
- Acceptance criteria: two images built once in CI and pushed to GHCR (backend; frontend nginx with the API URL injected at start); Railway `development` and `production` environments, each with its own Postgres, uploads volume, secrets and domains, deployed from `dev` and `main` by `deploy.yml` with pre and post-deploy gates; migrations run on container start; seed run once per environment by hand; `/health` and `/healthz` green.
- Priority: MVP · Day 3 · Dependencies: US-006 · Requirements: NFR-006 · `docs/09-operations/OPERATIONS.md`
- Definition of Done: UAT executed on the deployed URL.

### US-052 — As a reviewer, I want the production deployment reachable on the project's own domain (permitflow.space), so that the demo URL is memorable and looks like a real service.
- Acceptance criteria: one naming convention per environment on the owner's domain: production `https://permitflow.space` (and `www`) for the frontend and `https://api.permitflow.space` for the API; development `https://dev.permitflow.space` and `https://api.dev.permitflow.space`; all with Railway-managed TLS; per environment `CORS_ORIGINS`, the frontend `API_URL`, the GitHub environment variables (`FRONTEND_URL`, `BACKEND_URL`) and the deploy health gates use the new hosts; the railway.app hosts keep working as fallbacks; `README.md` and `docs/09-operations/OPERATIONS.md` name the hosts and the DNS records (owner adds them at the registrar).
- Priority: Nice-to-have · Day 3 (added 19 Sep, domain bought by the owner) · Dependencies: US-007 · Requirements: NFR-006 · Beyond the brief
- Definition of Done: all four hosts answer their health checks over HTTPS; the next development deploy and the v0.3.0 production deploy pass their gates against them.

### US-053 — As an engineer, I want unit and integration coverage of the business logic to sit at industry level (about 80 percent statements, measured with every source file counted), so that the tests protect behaviour rather than count buttons.
- Acceptance criteria: coverage measured with all source files included (`coverage.include` in `vite.config.ts`, `pytest --cov`); frontend at or above 80 percent statements, backend at or above 80 percent (it stands at 96); new tests target behaviour: the API client's error envelope and 401 handling, upload validation and progress, the document slot's verification states and staleness, the respond-mode walk, submit readiness, the session warning window, sign-in and cache clearing, history, compare and audit rendering, the OpenAI provider's error paths with a stubbed SDK; thresholds enforced in CI so coverage cannot regress; `docs/08-testing/TEST_STRATEGY.md` and the README carry the numbers.
- Priority: MVP · Day 3 (added 19 Sep, before the v0.3.0 release) · Dependencies: US-005 · Requirements: NFR-004 · Branch `test/us-053-coverage`
- Definition of Done: thresholds green in CI; no test asserts presentation only; numbers recorded.

### US-054 — As a reviewer, I want the AI's answers evaluated against the real model on a schedule and on every change to the AI module, so that the quality claim is a green check with history rather than a paragraph.
- Acceptance criteria: a separate workflow `ai-eval.yml` runs the 14-case golden set through the real pipeline with `--provider openai` (temperature 0), blocking at 14 of 14; triggers: nightly, manual (with an optional lower pass rate), and pushes to `dev` or `main` touching `app/infra/ai`, `verification_rules.py`, `app/infra/extraction` or `evals`; never on pull requests; refuses to run without the `OPENAI_API_KEY` repository secret; the harness stamps provider, model and prompt version in the JSON result; per-case table (status, codes, latency) in the run summary; result files kept 90 days; `docs/07-ai/AI_EVALUATION.md`, `README.md`, `OPERATIONS.md` and `TEST_STRATEGY.md` describe it.
- Priority: Nice-to-have · Day 3 (added 19 Sep, after the coverage story) · Dependencies: US-004 · Requirements: AI-008 · Branch `feat/us-054-ai-eval-workflow`
- Definition of Done: the workflow is green on the first manual run after the owner sets the secret; the mock job in `ci.yml` unchanged and green.

### US-055 — As an officer or reviewer, I want every AI check traced (prompt version, model, tokens, latency, raw answer) and every evaluation run kept as an experiment, so that a wrong check can be explained from its trace and a prompt change has a history.
- Acceptance criteria: LangSmith tracing behind `LANGSMITH_API_KEY` (off without it, no behaviour change); one parent run per check carrying the verification run id, application id, document id, document type and prompt version, the OpenAI call as a child run; inputs hidden by default (`LANGSMITH_HIDE_INPUTS`), endpoint per region (`LANGSMITH_ENDPOINT`), project per environment; tracing lives in `infra/ai/tracing.py`, never in `domain`, and a tracing failure cannot fail a check; `evals.run --langsmith` records a run as an experiment on the golden dataset; `ai-eval.yml` uses it when the secret exists; threat model T21; ADR-006 amended; env documented in `.env.example`, README, OPERATIONS.
- Priority: Nice-to-have · Day 3 (added 19 Sep, after US-054) · Dependencies: US-002, US-054 · Requirements: AI-007, AI-008, AI-009 · Branch `feat/us-055-langsmith-tracing` · Beyond the brief
- Definition of Done: unit tests green; a trace of a live check visible in the owner's LangSmith project (development); documented.

### US-056 — As a reviewer, I want the AI checks to run as a named gate of their own (model approval, contracts, golden set, adversarial, fairness, verdict) with a fairness check that swaps applicant names, so that "how do you evaluate the AI" is answered by a run summary anyone can read.
- Acceptance criteria: `ai-gate.yml` as a reusable workflow called from `ci.yml` (still blocks images and deploys), six jobs each named in the run summary; the old `ai` job removed from `ci.yml`; `evals.run --group` filter; `evals/fairness.py`: 7 name sets (Chinese, Malay, Indian, Eurasian, Western and the baseline) × 3 scenarios = 21 runs, every variant must match its baseline's status and codes, `--fail` exit code, JSON output; fairness runs in the gate on the mock and in `ai-eval.yml` on the live model, both blocking; `docs/07-ai/AI_ASSURANCE.md` one-page explainer (layers, two pipelines, what the first fairness run found, limits, tools chosen and not); README, OPERATIONS, TEST_STRATEGY, AI_EVALUATION, PRODUCTION_READINESS_REVIEW updated.
- Priority: Nice-to-have · Day 3 (added 19 Sep, after US-055) · Dependencies: US-004, US-054 · Requirements: AI-008 · Branch `feat/us-056-ai-gate` · Beyond the brief
- Definition of Done: AI gate green on `dev`; fairness 21 of 21 on the live model recorded; explainer written.

### US-057 — As the owner, I want the site reviewed for legal, privacy and accessibility exposure (policies, consent, tracking, embeds, contrast, keyboard, labels, claims, copyright, applicable law), so that a demonstration with public credentials and a live AI provider does not mislead anyone or leak more than it says.
- Acceptance criteria: `/privacy`, `/terms` and `/cookies` pages written from the code (operator named, repository linked, no email; PDPA purposes, transfers to OpenAI, LangSmith and Railway, retention, rights), linked from the landing footer and the app shell; a "demonstration only, no real data" notice on sign-in and on the documents page; no cookie banner, with the reason recorded; refund policy recorded as not applicable; fonts self-hosted (no third-party request from the browser at all), OFL notices kept with the files; an axe-core gate in Playwright (WCAG 2.0, 2.1, 2.2 A and AA plus best practice) on every public and signed-in screen at desktop and phone width, the feedback composer and a dialog, run in CI; keyboard sign-in and skip-link tests; contrast of every text token against every surface computed and the one failing token corrected; landing copy re-read for unsupported claims; `docs/11-reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md` answers the owner's checklist item by item with evidence, lists the laws considered and the risks flagged; threat model T22; the owner's prompt recorded in `AI_USAGE.md`.
- Priority: Nice-to-have · Day 3 (added 19 Sep, after US-056) · Dependencies: US-047, US-008 · Requirements: SEC-012, UX-001 · Branch `feat/us-057-legal-accessibility` · Beyond the brief
- Definition of Done: a11y gate green locally and in CI; policies render at 1280 and 390 without overflow; review document complete; nothing in it that the code does not do.

### US-058 — As the owner, I want the service to resist abuse (a hammered sign-in, draft spam, a run on the expensive AI endpoint, scraping) and to pass a hardening checklist, so that a public demonstration with published credentials cannot be knocked over or run up a bill.
- Acceptance criteria: a per-client sliding-window limit on every request (`RATE_LIMIT_PER_MINUTE`) and on sign-in attempts of any outcome (`LOGIN_ATTEMPTS_PER_MINUTE`), 429 with `Retry-After` in the error envelope, inside CORS, health exempt, proxy-aware; quotas counted in the database: open drafts per operator (`MAX_DRAFTS_PER_USER`, 409), verification runs per applicant and per platform per rolling day (`AI_RUNS_PER_USER_PER_DAY`, `AI_RUNS_PER_DAY`; over quota the run is stored `unavailable` with `daily_limit_reached`, no model call, officer copy explains); CSP, HSTS, Permissions-Policy, COOP on the API and CSP (one API origin rendered from `API_URL`), HSTS, Permissions-Policy on nginx; `pip-audit` fixed and blocking, `bandit` blocking at medium, `npm audit` blocking at high, images wait for the audit; unit and integration tests for every limit; `docs/06-security/SECURITY_REVIEW.md` answers the owner's checklist and the four attacks item by item; threat model T13 and T16 amended; env vars documented; the owner's prompt recorded in `AI_USAGE.md`.
- Priority: Nice-to-have · Day 3 (added 19 Sep, after US-057) · Dependencies: US-001, US-002, US-007 · Requirements: SEC-010, NFR-003 · Branch `feat/us-058-abuse-resistance` · Beyond the brief
- Definition of Done: 748 backend tests green; the built frontend image serves the rendered CSP and the bundle runs under it with zero violations; CI audit job green and blocking; review document complete.

### US-059 — As the owner, I want a pitch deck, a technical deck and three videos made from the repository after the code is frozen, so that the debrief shows the product and the decisions the way the code supports them.
- Acceptance criteria: a pitch deck (11 slides) and a technical deck (18 slides: brief, scope, assumptions, the board, architecture, four ADRs, branching, deployment, CI, readiness, AI usage, next steps) as PowerPoint with speaker notes and a handout PDF each, built from one content file per deck; a launch video (about 70 s), a narrated walkthrough of both roles and a short technical video, all 1920 x 1080 at 60 fps with subtitles, recorded on the development environment only; four diagrams (solution architecture, branching, deployment, CI/CD) rated against the code before use; every fact on a slide pulled from the repository; the launch video plays inline in the README; everything under `docs/14-debrief/` with videos in Git LFS; how it was made recorded in `AI_USAGE.md`.
- Priority: Nice-to-have · Day 3 (added 19 Sep, after the v0.3.0 release) · Dependencies: US-008, US-052 · Requirements: none (debrief material, not product) · Branches `chore/debrief-assets`, `docs/agile-evidence`, `chore/technical-video-final`, `docs/readme-video-inline` · Beyond the brief
- Definition of Done: decks and videos approved by the owner; `docs/14-debrief/README.md` indexes them; README, `docs/README.md`, `CHANGELOG.md` and `AI_USAGE.md` describe them; production untouched during recording.

### US-074 — As the owner, I want the whole submission assessed by independent reviewers against the brief and the findings fixed or recorded, so that what the repository claims survives a hiring panel's verification.
- Acceptance criteria: four read-only reviews with separate briefs (documentation truth, backend, frontend, delivery and security) and two more on a second model (reviewer's first two hours, acceptance criteria against code); every finding verified in the code before it is acted on; fixed: operator refusals without internal codes, the layering test hole, the audit purge as the one delete path, no fallback JWT secret, release image tags only from git tags with production pinned to the release image, the deploy job waiting for a new deployment id, least-privilege workflow tokens, audit trail refetched after officer actions, check progress from server states only, `FRONTEND_ARCHITECTURE.md` rewritten from the tree, gate stages named for what they prove, review documents recounted, T19 marked planned, rollback plan and migration compatibility rule written; `main` protected (pull request from `dev`, seven required checks, owner included) and `dev` protected against force pushes; findings kept as decisions listed in `PRODUCTION_READINESS_REVIEW.md` rows 21 and 22.
- Priority: MVP · Day 3 (added 20 Sep, after the release) · Dependencies: US-050, US-058, US-059 · Requirements: FR-026, SEC-006, SEC-009, NFR-001 · Branches `fix/us-050-review-findings-2`, `fix/review-round-2`, `docs/rollback-plan` · Pull requests #1 and #2
- Definition of Done: 753 backend and 153 frontend tests green; CI green on `main` through the protected path; `CHANGELOG.md` "Review fixes (20 Sep 2026)" lists every change; scores recorded in `docs/11-reviews/FINAL_REVIEW.md`.

### US-075 — As the owner, I want one final review of the whole repository, the code and every document, with an edge-case acceptance run, so that nothing avoidable is found by the panel on submission day.
- Acceptance criteria: every suite re-run from a cold clone (backend, frontend, Playwright with the accessibility gate); three independent read-only reviews (backend correctness and authorization, frontend behaviour and copy rules, documentation against code) with every finding verified in the code before it is acted on; an API-level edge-case run that drives every refusal path and boundary (auth, drafts, uploads, submission, officer guards, resubmission, compare, licence, withdrawal, deletion, notifications, quota, health) and is recorded in `docs/10-uat/UAT_PLAN.md` with the script kept in the repository; fixed: a failed background refetch wiping unsaved work, a check stuck past its window never offering Re-run, the upload size gate running after the body was parsed, quota refusals counting toward the quota, the verification task holding a pooled connection through the model call, provider reason codes reaching operators, an inaccurate `has_note`, an orphaned licence PDF on a failed commit, the health 503 outside the error body; documents corrected where they disagreed with the code (architecture, domain model, state machine, threat model, counts); findings accepted as decisions listed in `PRODUCTION_READINESS_REVIEW.md` row 23.
- Priority: MVP · Day 3 (added 20 Sep, the night before submission) · Dependencies: US-074 · Requirements: FR-026, SEC-005, NFR-001, REL-001 · Branch `feat/us-075-final-check` (not merged into `dev` by the session; the owner merges after reading the diff)
- Definition of Done: 756 backend and 158 frontend tests green, Playwright 12 of 12 locally, 166 of 166 edge checks; `CHANGELOG.md` "Final check (20 Sep 2026)" lists every change; `AI_USAGE.md` records the prompts of the session.

### US-076 — As an officer, I want the review queue to show only what the applicant has submitted, so that an unsubmitted edit never reaches me before the applicant sends it.
- Acceptance criteria: the queue's business name and premises address come from the latest submitted revision (the working copy only when no revision exists), verified by a test that edits the working copy after submission; the draft quota takes a row lock on the operator's user row before counting, verified by a test that proves a second transaction cannot take the row while the check is in progress; `LicenceService`, `DraftDeletionService` and the verification task issue no SQLAlchemy statements of their own (a `LicenceRepository` and three `DocumentRepository` methods), and the layering test fails on any SQLAlchemy import in `services/` other than `Session`; readiness row 23 and the issues register updated.
- Priority: MVP · Day 3 (added 20 Sep after a cold review of the repository, which rated the queue defect as the one shipped defect worth fixing before submission) · Dependencies: US-075 · Requirements: FR-015, FR-012, SEC-010 · Branch `fix/us-076-review-defects`
- Definition of Done: backend suite green with the three new tests (759 cases from 170 functions); `ruff`, `mypy --strict` clean; `ARCHITECTURE.md` states the services rule; `CHANGELOG.md` entry.

### US-077 — As the platform owner, I want an observability layer (Prometheus metrics from the API, Grafana dashboards and alert rules), so that I can see whether the API is healthy, whether the document checks are healthy and what they cost, and whether the queue is moving, without reading logs.
- Acceptance criteria: `GET /api/v1/metrics` in the Prometheus text format, served only when `METRICS_TOKEN` is set and only with that bearer token (404 without a configured token, 401 without or with a wrong one), exempt from the per-client rate limit, never counting its own scrapes; counters and histograms with the `permitflow_` prefix and low-cardinality labels: HTTP requests by method, route template and status with a latency histogram, 429 refusals, verification runs by outcome and provider with a latency histogram, quota refusals by quota, committed transitions by target status and actor, applications by status (a gauge refreshed on each scrape), OpenAI tokens per call by model and kind (prompt, cached, completion); a Compose profile (`observability`) with Prometheus (six alert rules on the SLO) and Grafana (a provisioned dashboard generated from `docker/observability/grafana/build_dashboard.py`: header, an environment selector, a stat strip, then rows for API health, document checks, cost at the model's list price, queue); the same two services on Railway in the development environment, Prometheus private and scraping both environments over the owner's domain with a token each, Grafana public at `grafana.dev.permitflow.space`; no document text, no ids and no personal data in any metric.
- Priority: Nice-to-have · Day 3 (added 20 Sep after the cold review of the decks named observability as the missing production-readiness story) · Dependencies: US-058, US-054 · Requirements: NFR-002, REL-006, SEC-011 · Beyond the brief · Branch `feat/us-077-observability`
- Definition of Done: four tests in `tests/integration/test_metrics.py` plus the provider and limiter tests extended; the dashboard rendered with data on every panel (`notes/observability/grafana-local.png`); `ARCHITECTURE.md` (module, API table, diagram), `docs/13-observability/OBSERVABILITY.md` with three dashboard renders, `OPERATIONS.md` (variables, Observability section, Railway services), `THREAT_MODEL.md` T23, `TEST_STRATEGY.md`, `SCOPE.md` C9, readiness row 24 rewritten as built; the solution-architecture and deployment views regenerated; both decks updated; `CHANGELOG.md` entry.

### US-008 — As a reviewer, I want clear documentation of scope, architecture, AI usage, testing and operations, so that every decision is explainable.
- Acceptance criteria: README (setup, env vars, tests, AI usage, what I would do next), SCOPE.md, ADRs, threat model, test strategy, UAT plan, operations guide, production readiness review, assessment traceability, CHANGELOG.
- Priority: MVP · Day 3 (continuous) · Dependencies: all
- Definition of Done: every document reflects the implemented system; no fake content.

### US-009 — As the team, I want a reviewed UI design system and clickable prototype before implementation, so that every screen is built from an agreed, requirement-traced design.
- Acceptance criteria: design direction, tokens and type scale; screen inventory with IDs, personas, requirements and states; operator and officer flows; component inventory; UI state inventory including the upload → verification lifecycle; frontend architecture; requirement traceability; a clickable prototype covering login, operator submission, resubmission, officer review, feedback, compare, audit, admin, phone and tablet; two independent design-critique passes with findings applied; brand mark and logo.
- Priority: MVP · Design phase (17–18 Sep) · Dependencies: US-000 docs · Requirements: UX-001…UX-008 · `docs/04-design/`
- Definition of Done: `docs/04-design/README.md` links the prototype; every screen in the inventory exists on the canvas; no contradiction with STATE_MACHINE or DOMAIN_MODEL.

---

### US-034 — As the system, I want login, upload, verification and audit hardened against the near-misses found in review, so that abuse and restarts cannot corrupt or stall an application.
- Acceptance criteria: the login limiter keys on the socket address and honours `X-Forwarded-For` only from `TRUSTED_PROXIES`; a successful login does not reset the failure window; unknown emails cost the same hash check; an upload whose `Content-Length` exceeds the cap is refused before the body is read and rejected uploads leave no partial file; downloads work for any file name and return 404 when the file is missing; `NaN` in a number field is a 422; injection phrases are flagged even when the model calls the document unreadable; runs left `pending` by a restart are failed on startup and the pending-to-running claim is atomic; re-run takes the row lock and is audited; section saves are audited with field names only; error reasons served to clients come from a fixed vocabulary; notifications are delivered only after the commit; admin cannot download documents until US-072 grants it.
- Priority: MVP · Day 2 · Dependencies: US-001, US-012, US-002 · Requirements: SEC-005, SEC-010, REL-003, AUD-001 · Threat model T4, T5, T13 · Source: `docs/11-reviews/EDGE_CASE_REVIEW.md` items 17 to 31 · Branch `fix/us-034-backend-edge-cases`
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

### US-042 — As an engineer, I want one Playwright scenario per workflow (apply with AI checks, reaches the officer, officer flags, two resubmission rounds, withdraw, rejection), each asserting the audit trail, so that every path is proven separately and recorded.
- Acceptance criteria: six independent specs under `frontend/e2e/scenarios`; every spec ends by opening the audit trail as the officer and asserting the expected event sequence; each spec creates its own application and is re-runnable; traces kept on failure; listed in `docs/08-testing/TEST_STRATEGY.md`.
- Priority: MVP · Day 3 (requested 19 Sep) · Dependencies: US-005, US-038 · Requirements: all · Branch `feat/us-042-scenario-suite`
- Definition of Done: all six green locally against the mock provider; README and TEST_STRATEGY updated.

### US-043 — As a user on any screen size, I want the layout audit findings fixed (tables at 820 and 1280, audit trail columns, sticky review rail, stepper labels, tap targets), so that no screen is unreadable or unreachable at a common width.
- Acceptance criteria: every High and Medium item in `docs/11-reviews/LAYOUT_AUDIT.md` fixed and re-measured at the width it was found; Low items fixed where cheap, the rest marked open in the audit doc; no regression at 390, 820, 1024, 1280 and 1440.
- Priority: MVP · Day 3 (from the layout audit, 19 Sep) · Dependencies: US-037 · Requirements: UX-001 · Branch `fix/us-043-layout-audit`
- Definition of Done: audit doc status column updated; as-built screenshots refreshed for the changed screens.

### US-044 — As an operator on a busy server, I want an unexpected server error to reach my browser as a proper error with a request id, so that I am not told the server is unreachable when it is not.
- Acceptance criteria: unhandled exceptions are answered inside the CORS layer so the browser receives the JSON error envelope and request id; engine pool sized for the expected concurrency and documented; pool exhaustion surfaces as a clear 503 rather than a 30 s hang; a test injects an exception and asserts the envelope plus the CORS header for an allowed origin.
- Priority: MVP · Day 3 (from the layout audit backend observation, 19 Sep) · Dependencies: US-000 · Requirements: REL-001, NFR-004 · Branch `fix/us-044-error-cors-pool`
- Definition of Done: test green; `docs/09-operations/OPERATIONS.md` and `docs/06-security/THREAT_MODEL.md` (availability) updated.

### US-046 — As a user signing in, I want to show or hide my password and a sign-in page without unnecessary text, so that I can type it right without distraction.
- Acceptance criteria: an eye toggle inside the password field (accessible name Show password / Hide password), keyboard reachable, never submits the form; the helper text about the 10-attempt pause and shared sign-in is removed (the limiter still applies and the 429 message still explains it).
- Priority: Nice-to-have · Day 3 (requested 19 Sep) · Dependencies: US-001 · Requirements: UX-002 · Branch `feat/us-046-password-toggle`
- Definition of Done: `LoginPage.test.tsx` updated; browser check at 390 and 1440.

### US-047 — As a visitor, I want the landing hero to feel alive and branded (accent on the headline, tinted document tiles, an ink band with drifting light behind the What you need panel), so that the first impression is polished rather than flat.
- Acceptance criteria: brand red on "Apply once." and on the four document tiles, PDF chips stay quiet; the band behind the panel bleeds to the right edge of the screen at desktop widths, uses the ink tone with two soft lights drifting slowly and stops under `prefers-reduced-motion`; the panel is centred inside the band at every desktop width and flows under the copy below `lg`; the footer no longer links to staff sign-in.
- Priority: Nice-to-have · Day 3 (from user screenshots, 19 Sep; a full red band was tried and rejected as too heavy) · Dependencies: US-009 · Requirements: FR-031 · Branches `feat/landing-accent`, `fix/landing-red-band`, `feat/us-047-landing-band`
- Definition of Done: measured at 1024, 1440 and 2000: equal gaps either side of the panel, band reaches the viewport edge, no horizontal overflow.

### US-048 — As a signed-in user, I want to be warned only when my session is about to end, so that the top bar does not raise questions the rest of the time.
- Acceptance criteria: the top bar shows nothing about the session while more than 30 minutes remain; inside 30 minutes it shows "Session ends in n min", updated every minute, emphasised inside 5 minutes; at expiry the proactive sign-out and the sign-in explanation stay as they were (US-033).
- Priority: MVP · Day 3 (from the user's walkthrough, 19 Sep) · Dependencies: US-001, US-033 · Requirements: UX-002, SEC-006 · Branch `fix/us-048-session-warning`
- Definition of Done: `lib/session.test.ts`; browser check at 8 h, 12 min and 3 min remaining.

### US-050 — As the team, I want the findings of three independent bug-hunting reviews (backend rules, frontend interaction, seams) fixed and recorded, so that the release ships without the defects a reviewer would find first.
- Acceptance criteria: every High and Medium finding in `docs/11-reviews/BUG_HUNT_REVIEW.md` fixed with a regression test where one can capture it; Low findings fixed or explicitly kept with the reason; all suites green afterwards.
- Priority: MVP · Day 3 (requested 19 Sep) · Dependencies: everything shipped before it · Requirements: all · Branch `fix/us-050-bug-hunt`
- Definition of Done: review doc written; backend, vitest and the seven Playwright specs green.

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
- Priority: MVP · Day 1 (pulled forward from Day 2 with the pipeline) · Dependencies: US-012, US-002 · Requirements: FR-005, AI-002, AI-006 · Use case UC1-A
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
- Priority: MVP · Day 2 · Dependencies: US-011, US-015 · Requirements: SEC-006, UX-002, REL-005 · Source: `docs/11-reviews/EDGE_CASE_REVIEW.md` items 1 to 16 · Branch `fix/us-033-operator-edge-cases`
- Definition of Done: DoD checklist + `lib/unsaved.test.ts`, `queries.test.ts`, Chrome check of the sign-out guard and Save and exit.

### US-038 — As an operator, I want to withdraw my submitted application with an optional reason, so that the licensing office stops working on something I no longer need.
- Acceptance criteria: Withdraw is available to the owner from every post-submission, non-terminal status; drafts are simply left and decided applications cannot be withdrawn (409); optional reason (up to 1000 characters) stored with the application, shown to the officer on the case and to the operator in an outcome panel; Withdrawn is a terminal status labelled Withdrawn for both roles and nothing can be edited, resubmitted or transitioned afterwards; officers are notified in-app; the audit trail records the status change with the operator as actor; officers and admins get 403.
- Priority: Nice-to-have · Day 3 (added 19 Sep on request) · Dependencies: US-015, US-025 · Requirements: FR-032 · `docs/03-architecture/STATE_MACHINE.md` · Branch `feat/us-038-withdraw-application`
- Definition of Done: state machine tests cover the new edges; `tests/integration/test_withdrawal.py`; `ApplicationPage.test.tsx`; browser check on both sides; STATE_MACHINE, DOMAIN_MODEL, ARCHITECTURE, REQUIREMENTS, SCOPE, USE_CASES, SCREEN_INVENTORY, UI_STATES, USER_JOURNEY updated.

### US-040 — As an operator responding to feedback, I want the flagged sections marked with a warning in the form rail and the stepper, so that I can see at a glance where the officer asked for changes.
- Acceptance criteria: while the application is Pending Pre-Site Resubmission, sections with open released feedback show a warning marker (dot plus label, never colour alone) in the form rail, the stepper and the documents row; untouched sections keep their complete marker but are visibly locked; the marker becomes an addressed marker once the section changed in this round; fits 1440, 820 and 390.
- Priority: MVP · Day 3 (added 19 Sep from a phone screenshot) · Dependencies: US-017 · Requirements: FR-011, UX-003 · Branch `feat/us-040-flagged-markers`
- Definition of Done: component test for the rail markers; browser check on the resubmission flow.

### US-041 — As an operator responding to feedback, I want the form to walk me through only the flagged items and lead me straight to Resubmit, so that I always know what is left and how to send my changes back.
- Acceptance criteria: while Pending Pre-Site Resubmission, Save and continue moves to the next flagged section, then the documents page if a document was flagged, then the application page where Resubmit lives (locked sections are never a destination); the form shows a readiness banner ("Responding to feedback: n flagged items" / "Ready to resubmit: n of m changed") with a link back; locked sections are non-navigable in the rail and stepper; the application page shows a readiness alert above the feedback notice and each changed item reads "Changed, ready to resubmit"; the documents page primary reads Go to resubmit once ready.
- Priority: MVP · Day 3 (added 19 Sep: Save and continue landed on a locked section, no clear path to Resubmit) · Dependencies: US-018 · Requirements: FR-011, UX-003 · Branch `feat/us-041-respond-flow` (also delivers US-040)
- Definition of Done: `respond.test.ts` for the next-target rule; browser check of the respond flow at 1440 and 390 on a scratch application.

### US-045 — As an operator, I want to delete a draft I no longer need, so that abandoned drafts do not clutter my list.
- Acceptance criteria: a draft can be deleted by its owner from the application page (Discard draft when nothing was entered, Delete draft otherwise) after a confirmation that names the reference; `DELETE /applications/{id}` removes the application, its sections, documents (files on disk), verification runs and audit events; submitted applications answer 409 (withdraw instead), other operators 404, officers and admins 403. A draft was never part of the licensing record, so nothing is kept (SCOPE assumption 14).
- Priority: Nice-to-have · Day 3 (requested 19 Sep: drafts are created the moment New application is pressed; a product decision, FR-034) · Dependencies: US-010 · Requirements: FR-034 · Branch `feat/us-045-delete-draft` · Beyond the brief
- Definition of Done: `tests/integration/test_draft_deletion.py`; `ApplicationPage.test.tsx`; browser check; docs updated. Same branch fixes the Declarations resubmission dead end: re-confirming stamps `confirmed_at`, which the diff reports as "Confirmed on".

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
- Acceptance criteria: only allowed targets for the current state are offered; Request resubmission requires at least one open feedback item and releases the round's feedback to the operator; Mark site visit scheduled requires no `open` items; Reject requires a note and is available from every non-terminal post-submission state; invalid transitions return 409 and stale `expected_version` returns 409; the operator receives an in-app notification carrying the operator label; email delivery is mocked (logged).
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
- Follow-up (19 Sep 2026, run-through): the Approve dialog warns when documents in the current revision still have unresolved check results (issues found, needs review, not checked) and says approving records that the officer reviewed them; the button stays enabled because checks are advisory (AI-005). Decided against a hard gate. Same day: Return to review (Pending Approval back to Under Review) so an officer who notices something at the decision step can add feedback or request a resubmission instead of rejecting; one transition row, no new status.
- Priority: MVP · Day 2 · Dependencies: US-025 · Requirements: FR-027 · Use case UC2-C
- Definition of Done: DoD checklist + outcome transition tests.

### US-032 — As an operator, I want to see only the final outcome (Approved or Rejected) and never the internal approval stage, so that internal processing is not exposed to me.
- Acceptance criteria: an application in Pending Approval shows "Pending Approval" to me and "Route to Approval" to officers; my API responses contain no internal status codes, audit events or officer-only notes; enforced by separate response models.
- Priority: MVP · Day 2 · Dependencies: US-030 · Requirements: FR-026, SEC-001 · ADR-005 · Threat model T3
- Definition of Done: DoD checklist + schema test asserting field absence.

---

### US-039 — As an officer, I want feedback decisions to be safe and clear: resolve only items the operator saw, undo a withdraw or resolve for 10 seconds, and never see a composer on a locked case, so that I do not make mistakes I cannot take back.
- Acceptance criteria: Mark resolved is offered only for items released to the operator (open after release, or addressed); a draft item that was never sent offers Withdraw only and the API returns 409 for resolving an unreleased item; after Withdraw or Mark resolved a toast offers Undo for 10 seconds, undo restores the previous resolution, is audited (`feedback.restored`) and is refused by the server after the grace window or once the state no longer allows it; the composer closes itself when the case stops being editable and the lock reason is shown instead; item actions sit on their own row on phones.
- Priority: MVP · Day 3 (added 19 Sep from phone screenshots) · Dependencies: US-023, US-028 · Requirements: FR-018, FR-024, FR-033, AUD-001 · Branch `feat/us-039-feedback-undo`
- Definition of Done: backend tests for the release rule and undo (window, audit, authorization); component test for the toast undo; browser check at 390 and 1440.

### US-049 — As an officer reviewing a resubmission, I want to mark an addressed item as not fixed so it reopens with the same text, so that I can request the next round without retyping the feedback.
- Acceptance criteria: Not fixed on an addressed item (only while Under Review) sets it back to Open with the same message and target, takes it out of the operator's view until the next round is requested (freeze rule kept), is audited as `feedback.reopened` and counts as open so Request resubmission is available; Undo for 10 s like withdraw and resolve; the operator then sees the item as Needs your change again with the same text and history keeps both rounds.
- Priority: MVP · Day 3 (from the user's walkthrough, 19 Sep: a replaced document flips the item to Addressed, leaving nothing open to send) · Dependencies: US-028, US-039 · Requirements: FR-024 · Branch `feat/us-049-reopen-feedback`
- Definition of Done: `tests/integration/test_feedback_reopen.py`; scenario 04 extended with a not-fixed round; STATE_MACHINE, ARCHITECTURE, USER_JOURNEY updated.

### US-051 — As an operator whose application is approved, I want to download my licence certificate as a PDF, and as an officer I want to preview it before approving, so that the approval ends in a document the business can show.
- Acceptance criteria: on Approve the backend renders a PDF certificate (fictional issuing unit, licence number `FEL-<year>-<n>`, business, UEN, premises, holder, valid one year in Singapore calendar dates, approving officer, decision date, application reference, verification code) inside the approval transaction, stores it under a server key on the uploads volume, records it in `licences` and audits `licence.issued`; the operator's approval notification names the licence; officers get a watermarked preview page while the application awaits a decision (nothing stored) and Download licence on the case after approval; the operator gets Download licence (PDF) in the outcome panel; owner or officer only, admin 403, 404 before approval; rejection issues nothing.
- Priority: Nice-to-have · Day 3 (requested 19 Sep, beyond the brief) · Dependencies: US-031 · Requirements: FR-035 · Branch `feat/us-051-licence-certificate` (merged after the browser review)
- Definition of Done: `tests/unit/test_licence_render.py`, `tests/integration/test_licence.py`; the Playwright journey covers preview and both downloads; STATE_MACHINE side effect, DOMAIN_MODEL, ARCHITECTURE, USER_JOURNEY, SCREEN_INVENTORY, SCOPE updated.

## E4 — Admin Oversight & Monitoring (deferred: not started, cut per the Sprint 3 cut order)

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
