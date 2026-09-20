# PermitFlow

*This branch (`dev`) carries work toward v0.4.0 (use case 3 and the admin panel, planned in `docs/05-planning/RELEASE_PLAN_V0_4_0.md`). The submitted release is tag `v0.3.0` on `main`, live at permitflow.space; the development copy of this branch runs at dev.permitflow.space.*

## Live: [permitflow.space](https://permitflow.space)

![PermitFlow: the officer's review queue with the application, checks and feedback of a licence case](docs/14-debrief/video/permitflow-launch-poster.jpg)

https://github.com/user-attachments/assets/942739f7-e2bd-4360-b525-ecf960a7e796

*Launch video, 70 seconds. The narrated walkthrough (4 min 36 s) and the technical video (5 min 40 s) are in `docs/14-debrief/video/`.*

A regulatory licensing platform built for a 3-day full-stack assessment. An operator (the business owner, or an agent applying for the business) applies for a Food Establishment Licence through a guided form with checked uploads; a licensing officer reviews the submission, leaves feedback tied to a section or a document, and requests a resubmission in which only the flagged parts reopen. Every status change, feedback round and decision is audited; approval issues a licence certificate. An advisory AI verifier reads each uploaded document against the form before submission. It never decides anything.

**Try it:** production, v0.3.0, at https://permitflow.space (one example application waiting in the officer's queue); development at https://dev.permitflow.space. Demo accounts below. Local setup takes about ten minutes.

**Ten minutes to review it:** the technical deck's handout PDF in `docs/14-debrief/technical-deck/`, then `SCOPE.md`, then `docs/11-reviews/ASSESSMENT_TRACEABILITY.md` (every line of the brief mapped to code, test and evidence).

## Run locally

Requirements: Docker (for PostgreSQL), Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 24. Git LFS only for the videos and the prototype PDF under `docs/`.

```bash
cp .env.example .env
# The app refuses to start with the placeholder secret; set any 16+ random characters (macOS/Linux):
sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=$(openssl rand -hex 32)|" .env && rm .env.bak
docker compose up -d db          # PostgreSQL 16 on localhost:5432 (+ permitflow_test database)

cd backend
uv sync
uv run alembic upgrade head
uv run python scripts/seed.py           # demo accounts, see below
uv run uvicorn app.main:app --reload   # http://localhost:8000/api/v1/health, docs at /api/docs

cd ../frontend
npm install
npm run dev                            # http://localhost:3000
```

Local quotas: an operator may hold 20 open drafts and run 60 AI checks a day (the mock provider counts too). For local work set `MAX_DRAFTS_PER_USER=0` and `AI_RUNS_PER_USER_PER_DAY=0` in `.env`.

## Demo accounts

`backend/scripts/seed.py` creates two accounts (idempotent); sample documents, clean and with planted issues, are in `docs/12-demo/documents/`. The same accounts exist in every environment, and the password is shared on purpose: this is a demonstration, the sign-in page and the privacy policy say so, and no real personal data should be entered.

| Role | Email | Password |
|------|-------|----------|
| Operator (Tan Wei Ling) | operator@permitflow.example.sg | `PermitFlow!2026` |
| Licensing officer (Rahim bin Abdullah) | officer@permitflow.example.sg | `PermitFlow!2026` |

No admin account yet (the admin epic is v0.4.0), no self-registration or password reset by design (`SCOPE.md`, Deferred). Sign-in attempts are limited to 20 a minute per client.

## Scope

`SCOPE.md` is the decision record: what is built, simplified, mocked and deferred, and every assumption made where the brief is ambiguous.

- Use cases 1 and 2 are complete: sectioned form with validation and draft save, drag-and-drop uploads with a live AI check per document, submission as an immutable revision, officer queue and case view with the AI findings, feedback tied to a section or a document with templates, resubmission in which only the flagged parts reopen, revision compare, resolution tracking, role-specific status labels, notifications, audit trail, licence certificate on approval.
- Use case 3 (site-visit checklist) is deferred; its three statuses and transitions exist in the state machine and are tested, the checklist screens are not built.
- Beyond the brief: withdrawal, draft deletion, feedback undo and reopen, a public landing page, policy pages, an accessibility gate.

## Stack and architecture

FastAPI, SQLAlchemy 2, Alembic and Pydantic v2 on PostgreSQL 16; React 19, TypeScript strict, Vite, Tailwind, TanStack Query, React Hook Form and Zod; pytest on a real database, vitest, Playwright; GitHub Actions, images on GHCR, Railway with two environments. Why each: `docs/03-architecture/decisions/ADR-009-stack-and-delivery-pipeline.md`.

A modular monolith (`api → services → domain / repositories → models`, `domain/` pure Python) with the state machine as a data table (`backend/app/domain/workflow.py`), same-transaction audit rows, immutable revision snapshots and the AI behind a provider interface. The layering is enforced by a test (`backend/tests/unit/test_layering.py`). Start with `docs/03-architecture/ARCHITECTURE.md` and `STATE_MACHINE.md`; the twelve ADRs are indexed in `docs/03-architecture/decisions/README.md`.

```
backend/   FastAPI + SQLAlchemy 2 + Alembic
frontend/  React + TypeScript + Vite
docs/      01-discovery … 14-debrief, one README per folder; docs/README.md is the index
```

## Security

Argon2 password hashes; short-lived JWTs re-checked against the user row and the sign-in's session row on every request, one live session per account with a take-over from the sign-in page and a 60-minute idle limit (US-093); no fallback secret (the app refuses to start without a real `JWT_SECRET`). Authorization is server-side on every route (role per router, ownership as 404, sub-resource checks), with an authorization test per application-scoped endpoint. Uploads: allowlist, 10 MB, magic-byte check, server-generated keys, served only through authorised endpoints. Abuse limits: 240 requests a minute per client, sign-in limits, 20 open drafts, 60 AI checks a day per applicant and 1,000 per platform, counted in the database. Security headers and CSP on both tiers; gitleaks, pip-audit, bandit and npm audit block the build. Threats and controls: `docs/06-security/THREAT_MODEL.md`; the hardening checklist with a test per item: `docs/06-security/SECURITY_REVIEW.md`; privacy, legal and accessibility: `docs/11-reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md`.

## Tests

```bash
cd backend && uv run pytest && uv run ruff check . && uv run mypy
cd frontend && npm test && npm run lint && npm run typecheck && npm run build
cd frontend && npm run e2e          # Playwright against the running stack (backend :8000 with AI_PROVIDER=mock, Vite :3000)
```

831 backend cases from 232 test functions on a real PostgreSQL (the state-machine sweep alone is 597), 209 frontend tests, eleven Playwright specs (the journey, nine scenarios, the accessibility gate), 245 API-level edge checks (`backend/scripts/uat_edges.py`). Coverage: backend 95 %, frontend 81 % statements, both enforced in CI. Layers, commands and what each protects: `docs/08-testing/TEST_STRATEGY.md`; manual acceptance record: `docs/10-uat/UAT_PLAN.md`.

## Environment variables

`.env.example` documents every variable; `docs/09-operations/OPERATIONS.md` explains each one, per environment. `JWT_SECRET` is required everywhere, tests included. The frontend needs no `.env` locally (it defaults to `http://localhost:8000/api/v1`).

## CI/CD and deployment

![Deployment: build once, promote by tag, production behind a person](docs/03-architecture/diagrams/views/deployment.png)

`main` is production, `dev` is integration, one branch per story merged with `--no-ff`; `main` is protected and receives only pull requests from `dev` with seven green checks (`docs/09-operations/BRANCHING.md`).

`ci.yml` runs seven blocking jobs on every push and pull request: backend, frontend, end to end with the accessibility gate, secret scan, the six-stage AI gate (`ai-gate.yml`, on the mock provider), dependency and code audit, images. `ai-eval.yml` runs the same golden and fairness sets against the real model nightly and on changes to the AI path. Images are built once and pushed to GHCR; a merge to `dev` deploys the development environment automatically; production is pinned to a release image and deployed by hand behind the owner's approval, with health gates after every rollout. Environments, secrets, migrations and rollback by layer: `docs/09-operations/OPERATIONS.md`.

## Observability

`GET /api/v1/metrics` serves Prometheus counters and histograms behind a bearer token (off unless `METRICS_TOKEN` is set): requests by route and status, latency, rate-limit and quota refusals, document checks by outcome with their latency, transitions, applications by status, and the OpenAI tokens each check bills. `docker compose --profile observability up -d` runs Prometheus with six alert rules and Grafana on :3001 with the provisioned dashboard (API health, document checks, their cost at list price, the queue); the same services run on Railway, Grafana at https://grafana.dev.permitflow.space, and Telegram carries the alerts, an hourly digest per environment and a command bot (`/status`, `/cost`, `/queue`). Details, every metric, the dashboard and what is still missing: `docs/13-observability/OBSERVABILITY.md`.

## AI verification

Every uploaded document is checked in the background against the form (`backend/app/services/verification.py`): text is extracted (PDF and TXT), sent to a provider behind `VerificationProvider`, and the structured result is validated and post-processed by deterministic rules before it is stored. `AI_PROVIDER=mock` (default) is deterministic and offline; `AI_PROVIDER=openai` uses `gpt-4.1-mini` with a strict JSON schema at temperature 0. Results are advisory: they never change a status, and the operator sees a plain outcome while the officer also sees confidence, evidence and the model. With `LANGSMITH_API_KEY` set, checks are traced with inputs hidden by default. Design: `docs/07-ai/AI_VERIFICATION_DESIGN.md`; measurements: `docs/07-ai/AI_EVALUATION.md`; how the answers are kept trustworthy, in one page: `docs/07-ai/AI_ASSURANCE.md`.

## AI Usage

Claude Code (Claude Opus 5 for most sessions, Claude Fable 5.1 for some) in the Cursor terminal was the pair for the whole build: solutioning documents, design system and prototype, every story's code and tests, documentation and the sprint rituals. It worked under two standing instruction files, one of them checked in as `CLAUDE.md`: the three personas, operators never receive internal status codes, the layering, every status change through the workflow table, the AI never mutates state, the per-story checklist. Subagents with separate briefs ran the design critiques, edge-case reviews, bug hunts and an independent review against the brief; Claude in Chrome ran the persona run-throughs and the dashboard steps the CLI could not do, with my own sign-in and no secret through the agent. OpenAI is used inside the product only.

Every story ran the full suites, `ruff`, `mypy --strict` and `tsc --strict`, and a browser check at three widths before it moved to Done; every reviewer finding was reproduced before a fix; I read every diff before a commit and every push needed my yes. Where the AI was wrong is written down: invented enum values and a valid verdict on an expired certificate, a scope-creeping story, a transition the state machine did not allow, a scratch file in a commit, UTC licence dates, a harness fault first blamed on the model.

The full record, with the prompts grouped by the decision they carry, what was discarded and how the debrief videos were made: `AI_USAGE.md`. Slides 18 to 21 of the technical deck cover the same ground.

## Release notes

v0.3.0 (19 September 2026) is the version at https://permitflow.space. Next, v0.4.0: the admin panel and use case 3. An entry per release, in the users' words: `RELEASE_NOTES.md`; the engineering record: `CHANGELOG.md`.

## What I would do next

Each item has a row with severity in `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md`.

1. Use case 3: the checklist model, the officer's capture screen with draft save, per-item clarification, the operator's targeted response. The statuses and transitions already exist. About 1.5 days.
2. A worker for the AI checks (Redis or a Postgres `SKIP LOCKED` queue) so checks survive deploys and scale apart from the API; ADR-004 has one call site to change.
3. Object storage with signed URLs and a virus scan, a backup and restore drill, a retention policy.
4. httpOnly cookie sessions with CSRF protection, CSP nonces, the rate windows in Redis or at the edge.
5. Observability, second half: acknowledgement and escalation for the Telegram alerts, nginx and Postgres exporters, one Prometheus per environment, a runbook per alert (readiness row 24).
6. AI assurance beyond 14 golden cases: a labelled set grown from officer overrides, a red-team suite, calibrated confidence, in-region tracing, a multilingual injection classifier, Project Moonshot as the Singapore assurance evidence (`docs/07-ai/AI_ASSURANCE.md`, Limits).
