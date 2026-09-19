# PermitFlow: 3-Day Delivery Plan

Dates as planned: design phase = 17 September 2026 (US-009, `docs/04-design/`); Day 1 = 18 September 2026, Day 2 = 19 September 2026, Day 3 = 20 September 2026. As executed (git history, Singapore time): design phase 17 Sep evening; Sprint 1 closed 18 Sep 02:16; Sprint 2 closed 18 Sep 13:48; Sprint 3 ran from 18 Sep afternoon into 19 Sep. The three sprints kept their scope and rituals; only the calendar compressed. The final hours of Day 3 are protected for testing, deployment, documentation and review, not features.

## Day 1: Foundation and operator submission

Goal: an operator can log in, create an application, fill the form, upload documents (verified by the mock provider), and submit. State machine and authorization exist and are unit-tested.

| Block | Work | Output |
|-------|------|--------|
| Morning | Discovery, requirements, scope, solutioning, ADRs, domain model, state machine, threat model, architecture, stories, plan | `docs/**`, `SCOPE.md` |
| Midday | Repo skeleton: backend (FastAPI, SQLAlchemy, Alembic, settings, logging, error handling, health), frontend (Vite, TS strict, Tailwind, router, query client), docker compose, CI skeleton | `backend/`, `frontend/`, `.github/workflows/ci.yml` |
| Afternoon | Models + migration; auth (argon2, JWT, seed script); workflow module + labels + tests; form schema + validation; application create/list/get/section update; documents upload/replace/download with storage; verification pipeline with mock provider and background task; submit → Revision 1; audit + notifications | Backend for US-000, 001, 002 (mock), 010–015, 030 |
| Evening | Frontend: login, operator dashboard, application form (sections from schema, RHF + Zod), upload with drag-and-drop and polling status, progress, submit; integration tests for lifecycle so far | UI for the same stories; Day 1 checkpoint in `CHANGELOG.md` |

Exit criteria: US-000, 001, 002 (mock), 010, 011, 012, 014, 015, 030 Done; state machine and authorization unit tests green; CI green.

## Day 2: Officer review, feedback, resubmission, compare, audit

Goal: the full loop works twice in a row with revisions, highlights, compare, resolution tracking and audit trail; OpenAI provider wired.

| Block | Work | Output |
|-------|------|--------|
| Morning | Officer queue and application view; Start review; feedback create/withdraw/resolve with templates; transitions with guards, version check, notifications; officer view models | US-020, 021, 022, 023, 024, 025, 031, 032 backend + UI |
| Midday | Resubmission: editability rules, resubmit service with diff, feedback → addressed, Revision N+1; operator resubmission UI (feedback on top, anchored, only flagged editable); history tab | US-016, 017, 018, 019 |
| Afternoon | Compare endpoint and view; changed markers; resolution tracking UI; audit trail endpoint and tab; notifications UI (bell, list) | US-026, 027, 028, 029 |
| Evening | OpenAI provider with structured outputs (Pydantic parse); injection heuristic; malformed output tests; live status polish (US-013); integration tests for the whole loop; UI polish for loading/empty/error states | US-013, 002 (OpenAI provider), 003; Day 2 checkpoint |

Exit criteria: two full rounds work end to end locally; integration tests cover the loop; operator visibility tests pass.

## Day 3: Hardening, testing, deployment, documentation

Goal: deployed, tested, documented, honestly reviewed.

| Block | Work | Output |
|-------|------|--------|
| Morning | Playwright E2E critical journey; remaining unit tests (diff edge cases, editability, rate limit); security pass (headers, upload checks, CORS); error handling review; AI evaluation set and run | US-005, 004; `docs/07-ai/AI_EVALUATION.md`, `docs/08-testing/TEST_STRATEGY.md` |
| Midday | Complete CI (frontend + backend + E2E + gitleaks + Docker build); Railway deployment (backend, Postgres, volume, frontend); seed on deploy; health check | US-006, 007; `docs/09-operations/OPERATIONS.md` |
| Afternoon | UAT run on deployed URL (`docs/10-uat/UAT_PLAN.md`); bug fixes; three-viewport UI check | UAT results recorded |
| Evening (protected) | README, AI_USAGE.md, CHANGELOG, production readiness review, assessment traceability, final review; final cleanup; tag release | `README.md`, `AI_USAGE.md`, `docs/11-reviews/*` |

Exit criteria: CI green on main; deployed URL passes UAT; all submission checklist items satisfied.

## Cut order (apply in this order if behind; decided up front so the debrief answer is a single list)

1. Admin epic (US-070–073): role value stays in the enum, nothing else.
2. Compare any two revisions → current vs previous only (SCOPE S4).
3. AI evaluation runner → keep the fixture set, document a manual run (US-004).
4. Dynamic Zod-from-schema → static Zod schemas mirroring the backend form schema.
5. Queue status filter, re-run verification action, draft document delete (SCOPE S1–S3).
6. p95 latency and AI-health metrics (part of the admin epic anyway).
7. Notification bell → plain notifications list page.
8. Comment templates UI → plain dropdown (templates endpoint stays; templates are M9 so they are never removed).
9. Playwright reduced to the single shortest journey.

Nothing on the MUST list in `SCOPE.md` is cut; if the MUST list is at risk, the answer is a smaller UI (plain tables) with the same API and tests, not fewer behaviours.

## Risks and responses

| Risk | Response |
|------|----------|
| OpenAI provider integration takes longer than planned | Mock provider is the default; the real provider is a Day 2 evening task and can slip to Day 3 morning without blocking anything |
| Compare/diff UI eats time | Backend diff is simple; the UI can start as a plain table of changed fields and be refined only if time remains |
| Railway deployment issues | Docker Compose full stack is the fallback demo; deployment documented as attempted with the failure noted honestly |
| Playwright flakiness | Keep one deterministic journey with the mock provider; run against a local build in CI |
| Scope creep into UC3 | Hard no until Day 3 afternoon, and only if everything else is Done; realistically it remains deferred |
