# ADR-009: Technology stack, testing layers and CI/CD

## Context
Stack choice is free per the assessment but must be justified. The stack must maximise velocity for one engineer over three days while producing code a reviewer recognises as production-shaped.

## Constraints
- Type safety on both sides (no `any`, typed Python).
- Structured LLM output support.
- Simple deployment; CI must gate merges.

## Options Considered

### Option A: FastAPI + SQLAlchemy 2 + Pydantic v2 + Postgres; React + TypeScript + Vite + Tailwind + TanStack Query + React Hook Form + Zod; pytest / Vitest / Playwright; GitHub Actions; Railway
- Pros: Pydantic gives validated request/response models and doubles as the LLM output validator; OpenAPI drives frontend types; TanStack Query handles polling and cache invalidation; all tools are mainstream and well documented; the developer environment already has Node 24, Python 3.12, uv, Docker, Railway CLI.
- Cons: two languages in one repo.

### Option B: Full TypeScript (Next.js + Prisma + tRPC)
- Pros: one language; end-to-end types without codegen.
- Cons: server-side background work and LLM tooling are less ergonomic; Next.js deployment couples UI and API; Prisma migrations and JSON typing are weaker than SQLAlchemy/Pydantic for this domain.

### Option C: Django + HTMX
- Pros: batteries included (auth, admin).
- Cons: the drag-and-drop upload with live status and the diff/compare UI are richer than HTMX comfortably supports in the time; less aligned with the preferred frontend direction.

## Decision
Option A. Testing layers: unit (state machine, authorization, diff, AI validation, form schema), integration (API + Postgres lifecycle), one Playwright E2E for the critical journey, an AI evaluation set. CI: `ci.yml` runs frontend lint/typecheck/test/build, backend lint (ruff) / typecheck (mypy) / tests on a Postgres service, Playwright against the built app, and gitleaks. Deployment is a separate `deploy.yml` (manual trigger or on `main` after CI) using the Railway CLI.

## Rationale
Every choice serves a requirement: Pydantic for validation at both API and AI boundaries, TanStack Query for real-time status, Zod + RHF for inline validation, Playwright for the journey the assessment cares about, Railway for a deploy the reviewer can open.

## Consequences

### Positive
- Familiar, boring, explainable.
- Frontend types generated from OpenAPI reduce drift.

### Negative / Tradeoffs
- Two toolchains in CI (slightly longer pipeline).
- Railway single-region deployment; no blue/green.

## Validation
- CI green on the main branch; branch protection requires it.
- README setup verified on a clean clone.
