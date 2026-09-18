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

Backend tests run against the real `permitflow_test` database: the Alembic migrations are applied from scratch at the start of the session and every table is truncated between tests.

## Environment variables

See `.env.example`; every variable is documented there and in `docs/operations/OPERATIONS.md`. `JWT_SECRET` is required outside `APP_ENV=test`.

## Project layout

```
backend/   FastAPI + SQLAlchemy 2 + Alembic (api → services → domain / repositories → models)
frontend/  React + TypeScript + Vite + Tailwind + TanStack Query + React Hook Form + Zod
docs/      requirements, architecture, ADRs, design system and prototype, planning, security, operations
```

## Branching and deployment

`main` is production, `dev` is integration, work happens on `feat/*` branches: `docs/operations/BRANCHING.md`. Two Railway environments are planned: `development` from `dev` and `production` from `main`.

## AI verification

Every uploaded document is checked in the background against the application form (`backend/app/services/verification.py`): text is extracted (PDF and TXT; images are stored but reported as unreadable), sent to a provider behind the `VerificationProvider` interface, and the structured result is validated and post-processed by deterministic rules before it is stored. `AI_PROVIDER=mock` (default) uses a deterministic provider with no network; `AI_PROVIDER=openai` uses the OpenAI API with `OPENAI_API_KEY` and `OPENAI_MODEL` (default `gpt-4.1-mini`). Results are advisory: they never change an application's status, and the operator sees a plain-language outcome while the officer also sees confidence, evidence and the model used. Design and prompt contract: `docs/ai/AI_VERIFICATION_DESIGN.md`.

Sections on CI/CD, deployment, AI usage and "what I would do next" are added as the corresponding stories land (see `docs/planning/SPRINTS.md`).
