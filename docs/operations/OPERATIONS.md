# PermitFlow: operations guide

Status: growing with each story. Everything here describes what exists in the code today.

## Local setup

See `README.md` (Docker for PostgreSQL, uv for the backend, npm for the frontend). `docker compose up -d db` starts PostgreSQL 16 and creates two databases on first start: `permitflow` (development) and `permitflow_test` (pytest). `docker compose --profile full up` also builds and runs the backend container with a volume at `/data/uploads`.

## Environment variables

| Variable | Default | Used by | Notes |
|----------|---------|---------|-------|
| `APP_ENV` | `development` | backend | `development`, `test` or `production`. `test` selects `TEST_DATABASE_URL`, disables the login rate limiter and relaxes the JWT secret check. |
| `DATABASE_URL` | local Postgres | backend | Postgres only (`postgresql+psycopg://`). |
| `TEST_DATABASE_URL` | local `permitflow_test` | pytest, CI | Truncated between tests. |
| `JWT_SECRET` | empty | backend | Required (≥ 16 chars) outside `APP_ENV=test`; the app refuses to start otherwise. |
| `JWT_EXPIRES_MINUTES` | `480` | backend | 8 hours. |
| `CORS_ORIGINS` | `http://localhost:3000` | backend | Comma separated allowlist. |
| `UPLOAD_DIR` | `./data/uploads` | backend | Local disk storage; Railway volume at `/data/uploads`. |
| `UPLOAD_MAX_BYTES` | `10485760` | backend | 10 MB. |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | backend | Failed attempts per IP per minute. |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_TIMEOUT_SECONDS` | 10 / 20 / 5 | SQLAlchemy pool per process; when every connection is busy for longer than the timeout the request is answered 503 `unavailable` (US-044). Size for the number of uvicorn workers times concurrent requests |
| `TRUSTED_PROXIES` | empty | Comma-separated proxy IPs whose `X-Forwarded-For` is trusted for the login rate limit; set to the platform edge IPs in production |
| `TEST_LIVE_AI` | unset | tests | Set to `1` to let the pytest suite call the live OpenAI provider; otherwise tests force `AI_PROVIDER=mock` regardless of `.env`. |
| `AI_PROVIDER` | `mock` | backend | `mock` or `openai`. |
| `OPENAI_API_KEY` | empty | backend | Required when `AI_PROVIDER=openai`. |
| `OPENAI_MODEL` | `gpt-4.1-mini` | backend | Structured outputs required; `gpt-4.1-mini` measured fastest and cheapest for extraction on 19 Sep 2026 (see `docs/ai/AI_VERIFICATION_DESIGN.md`). |
| `AI_TIMEOUT_SECONDS` | `30` | backend | Per call. |
| `AI_CONFIDENCE_THRESHOLD` | `0.6` | backend | Below this, `verified` becomes `needs_review`. |
| `AI_MAX_TEXT_CHARS` | `20000` | backend | Extraction cap sent to the provider. |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | frontend | Build-time. |

## Seeding

`cd backend && uv run python scripts/seed.py` creates the demo operator and officer if they do not exist. `SEED_PASSWORD` sets their password (default `PermitFlow!2026`); set it to something else in any shared environment.

## Uploads

Files are written under `UPLOAD_DIR` as `<application_id>/<random>.<ext>` (never the client file name), atomically via a `.part` temp file. Deleting a document only clears `is_current`; the file stays for the revision history. Tests use `./data/test-uploads` and clean it after every test.

## Health

`GET /api/v1/health` → `200 {"status":"ok","database":"ok"}` or `503 {"status":"degraded","database":"unreachable"}`. Provider configuration is never exposed here.

## Logs

JSON lines on stdout: one `request` line per request with `request_id`, method, path, status, duration and user id. The request id is echoed in the `X-Request-ID` response header and shown to users on 500 responses. No payloads or document text are logged.

## Migrations

`cd backend && uv run alembic upgrade head`. New migration: `uv run alembic revision --autogenerate -m "<what>"`, then review the file. The container image runs `alembic upgrade head` on start.

## CI (US-006)

`.github/workflows/ci.yml`: backend (ruff, mypy, pytest on a Postgres service), frontend (lint, typecheck, vitest, build), E2E (the full stack started inside the job: Postgres service, `alembic upgrade head`, `scripts/seed.py`, uvicorn on :8000 with `AI_PROVIDER=mock` and a CI-only `JWT_SECRET`, `vite preview` on :3000, then `npm run e2e`), gitleaks, and a Docker build of the backend image. The E2E job needs the two test suites first. On failure it prints the last 200 lines of both server logs and uploads `playwright-report` and `test-results` as an artifact for seven days. Nothing in CI deploys: deployment is Railway's job (below).

## Deployment (planned, US-007)

Two Railway environments: `development` (deploys from `dev`) and `production` (deploys from `main`), each with its own PostgreSQL and its own variables. Backend from `backend/Dockerfile` with a volume at `/data/uploads`; frontend as a static site built with `VITE_API_URL` pointing at that environment's API.
