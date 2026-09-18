# PermitFlow

A regulatory licensing platform: business operators apply for a Food Establishment Licence, licensing officers review, give contextual feedback and request targeted resubmissions, and every uploaded document is checked by an advisory AI verifier. Built as a 3-day engineering assessment.

Status: Sprint 2 in progress (19 Sep 2026). Shipped so far: operator application, checked uploads and submission (Sprint 1); officer queue, case review with AI evidence, contextual feedback and templates, status transitions with notifications, operator resubmission of flagged parts only, revision compare and feedback resolution (Sprint 2). Details in `CHANGELOG.md`; scope in `SCOPE.md`; documentation index in `docs/README.md`. What exists today is listed in `CHANGELOG.md`; scope is in `SCOPE.md`; documentation index in `docs/README.md`.

## Run locally

Requirements: Docker (for PostgreSQL), Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 24.

```bash
cp .env.example .env            # defaults work for local development
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

## Demo accounts

`scripts/seed.py` creates two accounts (idempotent). Password for both: the value of `SEED_PASSWORD`, default `PermitFlow!2026`.

| Role | Email |
|------|-------|
| Operator | operator@permitflow.example.sg |
| Licensing officer | officer@permitflow.example.sg |

Sign in at http://localhost:3000/login. Each role lands in its own workspace; a URL for another role shows "Not available for your role" and the API answers 403.

## Security (so far)

Argon2 password hashes; JWT access tokens (8 h) with the role claim, re-checked against the user row on every request; failed-login rate limit 10 per minute per IP (429); generic 401 for wrong email or password; security headers and CORS allowlist; the app refuses to start without `JWT_SECRET` outside the test environment.

## Tests and checks

```bash
cd backend && uv run pytest && uv run ruff check . && uv run mypy
cd frontend && npm test && npm run lint && npm run typecheck && npm run build
```

Backend tests run against the real `permitflow_test` database: the Alembic migrations are applied from scratch at the start of the session and every table is truncated between tests. The AI provider is forced to `mock` in tests unless `TEST_LIVE_AI=1`.

The critical journey (apply, submit, flag, fix only the flagged part, resubmit, compare, resolve, approve) runs in a real browser with Playwright against the running stack:

```bash
# backend on :8000 with AI_PROVIDER=mock and seeded users, Vite on :3000
cd frontend && npm run e2e        # journey plus six scenario specs (E2E_API_URL if the backend is not on :8000)
```

Layers and what each protects: `docs/testing/TEST_STRATEGY.md`.

## Environment variables

See `.env.example`; every variable is documented there and in `docs/operations/OPERATIONS.md`. `JWT_SECRET` is required outside `APP_ENV=test`.

## Project layout

```
backend/   FastAPI + SQLAlchemy 2 + Alembic (api → services → domain / repositories → models)
frontend/  React + TypeScript + Vite + Tailwind + TanStack Query + React Hook Form + Zod
docs/      requirements, architecture, ADRs, design system and prototype, planning, security, operations
```

## Branching and deployment

`main` is production, `dev` is integration, work happens on `feat/*` branches: `docs/operations/BRANCHING.md`.

Two images (backend, frontend) are built once in CI and pushed to GHCR; Railway pulls them. Push to `dev` deploys the `development` environment, push to `main` deploys `production`, each with its own database, uploads volume and secrets, gated on health after deploy. Development: https://frontend-development-afe2.up.railway.app. Details, secrets, seeding and rollback: `docs/operations/OPERATIONS.md`.

## CI

`.github/workflows/ci.yml` runs on every push and pull request to `main` and `dev`, five jobs:

| Job | What it does |
|-----|--------------|
| Backend | `uv sync`, ruff (lint and format), mypy strict, pytest against a Postgres 16 service |
| Frontend | `npm ci`, oxlint, tsc, vitest, vite build |
| E2E | Starts Postgres, migrates and seeds, serves the backend on :8000 with the mock provider, builds the frontend and serves it with `vite preview` on :3000, then runs the Playwright journey and the six scenario specs; server logs and the Playwright report are attached when it fails |
| Secret scan | gitleaks over the full history |
| AI verification | Configuration audit, provider contract tests, the golden set through the real pipeline on the mock provider (blocking at 100 %), verdict in the run summary and as an artifact |
| Dependency audit | pip-audit and npm audit (production dependencies), reported in the run summary, non-blocking |
| Images | Builds the backend and frontend images; on `dev` and `main` pushes them to GHCR tagged with the branch and `sha-<commit>` |

`deploy.yml` runs after a green CI on `dev` or `main` and redeploys the matching Railway environment from the new images (see Branching and deployment).

The E2E job waits for the backend and frontend suites, so a broken unit test never spends the browser minutes.

## AI verification

Every uploaded document is checked in the background against the application form (`backend/app/services/verification.py`): text is extracted (PDF and TXT; images are stored but reported as unreadable), sent to a provider behind the `VerificationProvider` interface, and the structured result is validated and post-processed by deterministic rules before it is stored. `AI_PROVIDER=mock` (default) uses a deterministic provider with no network; `AI_PROVIDER=openai` uses the OpenAI API with `OPENAI_API_KEY` and `OPENAI_MODEL` (default `gpt-4.1-mini`). Results are advisory: they never change an application's status, and the operator sees a plain-language outcome while the officer also sees confidence, evidence and the model used. Design and prompt contract: `docs/ai/AI_VERIFICATION_DESIGN.md`.

**CI for the AI.** The `ai` job in `ci.yml` audits the configuration (pinned wire schema, prompt version, default model, provider wiring), runs the provider contract tests, then runs fourteen golden cases (the demo PDFs, edge cases and two prompt-injection styles) through the real pipeline with the mock provider and fails below 100 %; the verdict is written to the run summary. The same set is run by hand against OpenAI whenever the prompt or model changes and the result is recorded with the date in `docs/ai/AI_EVALUATION.md` (14 of 14 on 20 Sep 2026). A dependency audit job (pip-audit, npm audit on production dependencies) reports without blocking.

Sections on AI usage and "what I would do next" are added as the corresponding stories land (see `docs/planning/SPRINTS.md`).
