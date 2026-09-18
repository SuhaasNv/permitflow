# Test strategy

What each layer of tests protects, where it lives and how to run it. Written at the end of Sprint 2 (19 Sep 2026) from what exists; updated whenever a layer is added. Story: US-005. Requirements cross-reference: `../requirements/REQUIREMENTS.md`.

## Principles

- Tests run against real infrastructure where it is cheap: the backend suite uses a real Postgres database (`permitflow_test`), migrated from scratch at session start and truncated between tests. No SQLite substitutes, no mocked ORM.
- The AI provider is the one thing that is mocked by default. `tests/conftest.py` forces `AI_PROVIDER=mock` unless `TEST_LIVE_AI=1`, so the suite is deterministic and free. Live provider runs are recorded in `../ai/AI_VERIFICATION_DESIGN.md` and the evaluation set in `../ai/AI_EVALUATION.md` (US-004).
- Every endpoint has an authorization test (wrong role, wrong owner, wrong state) alongside its happy path. This is the threat model's control T2/T3 made executable.
- The state machine is tested exhaustively (every state, every target, every role) rather than by sampling.
- One end-to-end journey covers the critical loop in a real browser. It is deliberately a single test: it protects the product's one promise and is not a place for edge cases, which belong in the integration layer.

## Layers

| Layer | Where | Tool | Count at Sprint 2 close | Protects |
|-------|-------|------|-------------------------|----------|
| Backend unit | `backend/tests/unit/` | pytest | 12 files | Pure domain: `workflow` (528 parametrised transitions), `labels`, `form_schema`, `diff`, `uploads` (magic bytes, allowlist), `verification_rules` (injection check, evidence rules), `extraction`, `openai_wire` (pinned enums, date in prompt), `mock_provider`, `security` (hashing, tokens), `settings`, `layering` (api → services → domain, `domain/` imports nothing from FastAPI or SQLAlchemy) |
| Backend integration | `backend/tests/integration/` | pytest + FastAPI `TestClient` + Postgres | 19 files | Every API endpoint through HTTP: create, sections, documents (upload limits, sha256 no-change, download), verification (claim, stale pending), submit (completeness guard, Revision 1), officer queue and case, feedback (create, withdraw, resolve, release), resubmission (readiness, locked targets, Revision N+1, addressed), compare, outcome, audit trail, notifications, auth (limiter, timing), health and error envelope, edge cases (`test_edge_cases.py`, from `../reviews/EDGE_CASE_REVIEW.md`) |
| Frontend unit and component | `frontend/src/**/*.test.{ts,tsx}` | vitest + Testing Library + jsdom | 18 files, 46 tests | `zodFromSchema` (server schema to client validation), `format`, `unsaved` guard, `StatusBadge`, `NotificationsBell`, `LoginPage`, `RequireRole`, `CompletionCard`, `DashboardPage` grouping, `SectionForm` (save, lock, updated-elsewhere), operator `queries`, officer `QueuePage` and `CasePage` |
| End to end | `frontend/e2e/journey.spec.ts` | Playwright (Chromium) | 1 journey, about 30 s | The critical loop against the running stack: operator applies, uploads four documents, submits; officer starts review, adds feedback, requests resubmission; operator sees the notice, cannot edit the untouched section, fixes the flagged one, resubmits; officer sees Changed and Addressed markers, resolves, schedules and completes the site visit, routes to approval and approves; operator sees the outcome |
| End to end, one spec per workflow (US-042) | `frontend/e2e/scenarios/01..06-*.spec.ts` | Playwright (Chromium) | 6 specs, about 70 s | Each workflow on its own, each ending on the audit trail: (1) apply through the UI and every AI check lands; (2) the submission reaches the queue and the review starts, both sides notified; (3) the officer flags with free text and a template, withdraws and undoes, requests resubmission, the operator sees it on top and locked elsewhere; (4) two resubmission rounds with compare, resolution and approval; (5) the operator withdraws with a reason, the officer is told; (6) rejection needs a note, the operator sees the outcome. Officer-side scenarios seed their application through the API (`E2E_API_URL`) so each stays short and independent |
| Static | both | ruff, ruff format, mypy strict; oxlint, tsc strict, vite build | | Types and style. `any` is not used anywhere in the frontend; mypy runs in strict mode |
| Secrets | repo | gitleaks (CI) | | No credentials committed |

Backend total at Sprint 2 close: 620 tests.

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
cd frontend && npm run e2e               # journey + six scenarios
cd frontend && npx playwright test e2e/scenarios
E2E_API_URL=http://localhost:8001/api/v1 npm run e2e   # when the backend runs on another port
cd frontend && npm run e2e:ui            # Playwright UI mode
E2E_BASE_URL=https://staging.example npm run e2e   # against a deployed environment
```

The E2E test signs in with the seeded `operator@permitflow.example.sg` and `officer@permitflow.example.sg` accounts (`backend/scripts/seed.py`) and creates its own application, so it can be re-run without cleanup. It uploads generated text files (allowlisted `.txt`), which the mock provider verifies.

## What is not covered, and why

| Gap | Reason | Plan |
|-----|--------|------|
| Visual regression | No screenshot comparison; layouts are verified by hand at 1440, 820 and 390 per story and captured in `../design/screens/as-built/` | Deferred; a Playwright screenshot assertion per screen would be the next step |
| Live AI in CI | Costs money and is non-deterministic | Evaluation set run by hand and recorded (US-004) |
| Load and soak | Out of scope for the assessment | Noted in `../reviews/PRODUCTION_READINESS_REVIEW.md` (Day 3) |
| Accessibility audit | Manual checks only (labels, focus order, `aria-live` on status) | `axe` run per screen would be the next step |

## Definition of Done link

Playwright runs in CI (US-006): the `e2e` job starts Postgres, the migrated and seeded backend on the mock provider, and a production build served by `vite preview`, then runs every spec; the report is uploaded on failure.

A story is not Done until its tests exist and are green at every layer it touches (`../planning/DEFINITION_OF_DONE.md`, "Tests"). Every endpoint added in Sprint 2 shipped with an authorization test in the same commit.
