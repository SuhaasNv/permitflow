# Changelog

All notable milestones. Format: one section per sprint close plus in-sprint milestones. Story IDs refer to `docs/planning/USER_STORIES.md`.

## Sprint 1 (in progress, 18 Sep 2026)

- US-000 Project skeleton: FastAPI app with standard error body, security headers, CORS, JSON request logging, `/api/v1/health` (503 when the database is down); SQLAlchemy models for the whole domain model and Alembic migration `0001`; Docker Compose PostgreSQL with a separate test database; pytest fixtures that migrate from scratch and truncate between tests; layering tests; React + TypeScript + Vite + Tailwind shell with design tokens and typed API client; GitHub Actions CI skeleton (backend lint/type/test on Postgres, frontend lint/type/test/build, gitleaks).

## Design phase (17–18 Sep 2026)

- US-009 UI/UX design phase: design system, 23-artboard prototype, design documentation, two critique passes. See `docs/design/README.md`.
