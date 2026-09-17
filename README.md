# PermitFlow

A regulatory licensing platform: business operators apply for a Food Establishment Licence, licensing officers review, give contextual feedback and request targeted resubmissions, and every uploaded document is checked by an advisory AI verifier. Built as a 3-day engineering assessment.

Status: Sprint 1 in progress. What exists today is listed in `CHANGELOG.md`; scope is in `SCOPE.md`; documentation index in `docs/README.md`.

## Run locally

Requirements: Docker (for PostgreSQL), Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 24.

```bash
cp .env.example .env            # defaults work for local development
docker compose up -d db          # PostgreSQL 16 on localhost:5432 (+ permitflow_test database)

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload   # http://localhost:8000/api/v1/health, docs at /api/docs

cd ../frontend
npm install
npm run dev                            # http://localhost:5173
```

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

Sections on AI verification, security, CI/CD, deployment, AI usage and "what I would do next" are added as the corresponding stories land (see `docs/planning/SPRINTS.md`).
