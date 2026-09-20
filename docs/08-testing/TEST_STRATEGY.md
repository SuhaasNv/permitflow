# Test strategy

What each layer of tests protects, where it lives and how to run it. Written at the end of Sprint 2 (18 Sep 2026) from what exists; updated whenever a layer is added. Story: US-005. Requirements cross-reference: `../02-requirements/REQUIREMENTS.md`.

## Principles

- Tests run against real infrastructure where it is cheap: the backend suite uses a real Postgres database (`permitflow_test`), migrated from scratch at session start and truncated between tests. No SQLite substitutes, no mocked ORM.
- The AI provider is the one thing that is mocked by default. `tests/conftest.py` forces `AI_PROVIDER=mock` unless `TEST_LIVE_AI=1`, so the suite is deterministic and free. Live provider runs are recorded in `../07-ai/AI_VERIFICATION_DESIGN.md` and the evaluation set in `../07-ai/AI_EVALUATION.md` (US-004).
- Every endpoint has an authorization test (wrong role, wrong owner, wrong state) alongside its happy path. This is the threat model's control T2/T3 made executable.
- The state machine is tested exhaustively (every state, every target, every role) rather than by sampling.
- One end-to-end journey covers the critical loop in a real browser. It is deliberately a single test: it protects the product's one promise and is not a place for edge cases, which belong in the integration layer.

## Layers

| Layer | Where | Tool | Count (19 Sep 2026, Sprint 3) | Protects |
|-------|-------|------|-------------------------|----------|
| Backend unit | `backend/tests/unit/` | pytest | 16 files, 651 tests | Pure domain: `workflow` (588 parametrised transitions over 14 states and 3 actors, plus guards), `labels`, `form_schema`, `diff`, `uploads` (magic bytes, allowlist), `verification_rules` (injection check, evidence rules), `extraction`, `openai_wire` (pinned enums, date in prompt), `openai_provider_paths` (stubbed SDK: bounded trimming, timeout and connection failures as unavailable, malformed answers as provider errors, factory selection), `mock_provider`, `security` (hashing, tokens), `settings`, `layering` (api → services → domain, `domain/` imports nothing from FastAPI or SQLAlchemy) |
| Backend integration | `backend/tests/integration/` | pytest + FastAPI `TestClient` + Postgres | 31 files, 170 tests | Every API endpoint through HTTP: create, sections, documents (upload limits, sha256 no-change, download), verification (claim, stale pending), submit (completeness guard, Revision 1), officer queue and case, feedback (create, withdraw, resolve, release), resubmission (readiness, locked targets, Revision N+1, addressed), compare, outcome, audit trail, notifications, auth (limiter, timing), abuse limits (`test_abuse_limits.py`, US-058: sign-in flood, draft cap, daily verification quota, general limiter, hardening headers), health and error envelope, edge cases (`test_edge_cases.py`, from `../11-reviews/EDGE_CASE_REVIEW.md`), the site visit appointment (`test_site_visit.py`, US-084: propose from Under Review, accept then done, counter then accept, keep or a third date, reschedule by either side, confirm without a reply through an injected clock, keep after a reschedule, the six-round cap, date rules, authorization and ownership, the officer's name masked for operators), the checklist (`test_checklist.py`, US-060: the template, create-or-get under the lock and the closed route to approval, the two-tab race, the save rules and the replay, authorization; US-062 and US-063: the submit guards, the freeze, the audit order, one notification, the clean walk to approval and the second visit), sessions (`test_sessions.py`, US-093: a second sign-in refused with the other device named, take-over and its audit, the revoked token's 401 with the reason, a wrong password reveals nothing, sign-out, idle expiry and activity through an injected clock, tokens without or with a forged session id, every role, the gauge), storage (`test_storage_budget.py`, US-085: EXIF and orientation gone from a JPG, text chunks gone from a PNG with the colour profile kept, an unreadable image refused with nothing kept, the budget refusing the file that would pass it and naming the room, every version and the evidence counted), the administrator (`test_admin.py`, US-070 to US-073: the overview's counts, turns, today and checks, the idle list and the day boundary in Singapore time, the feed's keyset pages and user rows, every GET 200 with no actions and every mutation 403 for an admin, the directory rules, the next-request effect of a change, the last admin, two admins at once, account creation) |
| Frontend unit and component | `frontend/src/**/*.test.{ts,tsx}` | vitest + Testing Library + jsdom | 41 files, 222 tests | `zodFromSchema` (server schema to client validation), `format`, `unsaved` guard, `StatusBadge`, `NotificationsBell`, `LoginPage`, `RequireRole`, `CompletionCard`, `DashboardPage` grouping, `SectionForm` (save, lock, updated-elsewhere, server refusal), operator `queries`, officer `QueuePage` and `CasePage` (stale 409, re-run refusal, template prefill); since US-053: API client (error envelope, 204, network failure, 401 handler), `documents` (allowlist and size pre-check, XHR upload with progress and the same envelope, downloads with object URL cleanup), 27 route and method contracts against the API table, `DocumentSlot` (every verification state, staleness, replace), `DropZone`, `FormPage` (respond-mode walk, locked sections), `ReviewAndHistory` (submit readiness, history), `AuthContext` (sign-in, expiry, cache clearing), `AppShell` (rail per role, session warning window, sign-out guard), `router` (role gates), `CompareAndAudit`, `Dialog`, shared states |
| End to end | `frontend/e2e/journey.spec.ts` | Playwright (Chromium) | 1 journey, about 25 s (the visit is arranged through the proposal dialog and accepted through the API before Mark site visit done, US-084) | The critical loop against the running stack: operator applies, uploads four documents, submits; officer starts review, adds feedback, requests resubmission; operator sees the notice, cannot edit the untouched section, fixes the flagged one, resubmits; officer sees Changed and Addressed markers, resolves, schedules and completes the site visit, routes to approval, previews the licence and approves; the officer downloads the licence from the case, the audit trail shows it issued, and the operator downloads it from the outcome panel (US-051) |
| End to end, one spec per workflow (US-042, US-084, US-060, US-093, US-073) | `frontend/e2e/scenarios/01..10-*.spec.ts` | Playwright (Chromium) | 10 specs, about 2 min | Each workflow on its own, each ending on the audit trail: (1) apply through the UI and every AI check lands; (2) the submission reaches the queue and the review starts, both sides notified; (3) the officer flags with free text and a template, withdraws and undoes, requests resubmission, the operator sees it on top and locked elsewhere; (4) two resubmission rounds with compare, resolution and approval; (5) the operator withdraws with a reason, the officer is told; (6) rejection needs a note, the operator sees the outcome; (7) the site visit: the officer proposes in the dialog, the operator counters with a reason, the officer accepts the operator's date, the operator asks to move it, the officer keeps the date, marks the visit done, and the audit trail and the operator's notifications carry every step; (8) the checklist: opened from the case once the visit is confirmed, findings recorded, the draft saved and surviving a reload, the case summarising it, the transitional route to approval closed; (9) one session per account: two browser contexts, the first records a finding on the checklist, the second is refused, takes over and opens the same draft, the first lands on the sign-in page with the reason and the time, and signs in again once the second signs out; (10) the administrator: the overview, a case read without a control, the feed with a user row, the spare account changed and restored. Officer-side scenarios seed their application through the API (`E2E_API_URL`) so each stays short and independent |
| Accessibility (US-057) | `frontend/e2e/a11y.spec.ts` | Playwright + axe-core | 8 tests, about 1 min | WCAG 2.0, 2.1 and 2.2 A and AA rules plus best practice on 15 screens at desktop width, 7 at 390 px (target size included), the feedback composer and a confirmation dialog; keyboard sign-in; skip link. Any violation fails with its selector. Runs in the CI end-to-end job as part of `npm run e2e`; `npm run e2e:a11y` runs it alone |
| Observability (US-077) | `backend/tests/integration/test_metrics.py`, plus assertions in `test_openai_provider_paths.py` and `test_rate_limit.py` | pytest | 4 tests | The metrics route is off without a token and refuses a wrong one; the families the dashboard reads exist after a round (requests by route, transitions, verification outcomes, the by-status gauge); the scrape does not count itself; the provider counts the tokens OpenAI reports; the limiter exempts the scrape |
| Static | both | ruff, ruff format, mypy strict; oxlint, tsc strict, vite build | | Types and style. `any` is not used anywhere in the frontend; mypy runs in strict mode |
| Secrets | repo | gitleaks (CI) | | No credentials committed |

Backend total on 21 Sep 2026 (v0.4.0 branch, after the admin epic): 850 test cases from 249 test functions (after US-093: 831 from 232; 20 Sep, after US-084: 798 from 208) (`test_site_visit_rules.py` adds the working-day, notice, deadline and round-cap rules; the route lock test walks every route); the state-machine sweep in `test_workflow.py` alone contributes 588 parametrised cases, so the count of distinct tests is the smaller number. Sprint 3 close was 748, Sprint 2 close 620.

## Coverage (US-053)

Measured with every source file counted, not only the files a test happens to import. The thresholds are enforced in CI (`ci.yml`, backend and frontend jobs), so a change that drops below them fails the build.

| Suite | Command | Result (21 Sep 2026) | Threshold |
|-------|---------|----------------------|-----------|
| Backend (`app/`, branch coverage on) | `uv run pytest --cov=app` (`[tool.coverage.*]` in `pyproject.toml`) | 95 % statements, 850 test cases (21 Sep 2026) | `--cov-fail-under=80` |
| Frontend (`src/**/*.{ts,tsx}` minus tests, fixtures and `main.tsx`) | `npm run test:coverage` (v8, `coverage.include` in `vite.config.ts`) | 82 % statements, 84 % lines, 79 % functions, 73 % branches, 222 tests (21 Sep 2026) | statements 80, lines 80, functions 75, branches 65 |

What the numbers do not say: a covered line is a line that ran, not a line whose behaviour is asserted. The tests added for US-053 were chosen by behaviour first (the acceptance criteria list them in `../05-planning/USER_STORIES.md`); the percentage is the check that nothing was left untested, not the goal. Playwright coverage is not counted: it runs against a built bundle.

## Shared journey helpers

`backend/tests/journeys.py` builds applications in any state with one call (`draft`, `complete_draft`, `submitted`, `under_review`, `add_feedback`, `flag_and_request`, `transition`, `upload`) so that an integration test reads as the scenario it protects rather than as setup. `factories.py` seeds users per role.

## How to run

```bash
# Backend (needs Postgres from docker compose; creates permitflow_test itself)
cd backend && uv run pytest              # all
cd backend && uv run pytest tests/unit   # pure domain only, no database
cd backend && TEST_LIVE_AI=1 uv run pytest tests/integration/test_verification.py   # against OpenAI, needs OPENAI_API_KEY

# Frontend
cd frontend && npm test                  # vitest, once
cd frontend && npm run test:watch

# End to end (backend on :8000 with AI_PROVIDER=mock and seeded users, Vite on :3000)
cd frontend && npm run e2e               # journey + nine scenarios + the accessibility gate
cd frontend && npx playwright test e2e/scenarios
E2E_API_URL=http://localhost:8001/api/v1 npm run e2e   # when the backend runs on another port
cd frontend && npm run e2e:ui            # Playwright UI mode
E2E_BASE_URL=https://staging.example npm run e2e   # against a deployed environment
```

The E2E test signs in with the seeded `operator@permitflow.example.sg` and `officer@permitflow.example.sg` accounts (`backend/scripts/seed.py`) and creates its own application, so it can be re-run without cleanup. It uploads generated text files (allowlisted `.txt`), which the mock provider verifies.

## What is not covered, and why

| Gap | Reason | Plan |
|-----|--------|------|
| Visual regression | No screenshot comparison; layouts are verified by hand at 1440, 820 and 390 per story and captured in `../04-design/screens/as-built/` | Deferred; a Playwright screenshot assertion per screen would be the next step |
| Live AI on every push | Costs money and is non-deterministic | Covered separately (US-054, US-056): `ai-eval.yml` runs the golden set and the fairness check against OpenAI nightly, by hand, and when the AI module or the set changes; blocking at 14 of 14 and 21 of 21, results kept 90 days. The mock-provider AI gate (`ai-gate.yml`, six stages) runs on every push from CI |
| Load and soak | Out of scope for the assessment | Noted in `../11-reviews/PRODUCTION_READINESS_REVIEW.md` (Day 3) |
| Accessibility, assistive technology | axe covers what a rule can check; no screen-reader session has been run with VoiceOver or NVDA | A VoiceOver pass over the apply and review journeys would be the next step |

## Definition of Done link

Playwright runs in CI (US-006): the `e2e` job starts Postgres, the migrated and seeded backend on the mock provider, and a production build served by `vite preview`, then runs every spec; the report is uploaded on failure.

A story is not Done until its tests exist and are green at every layer it touches (`../05-planning/DEFINITION_OF_DONE.md`, "Tests"). Every endpoint added in Sprint 2 shipped with an authorization test in the same commit.
