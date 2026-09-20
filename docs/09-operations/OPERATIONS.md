# PermitFlow: operations guide

Status: growing with each story. Everything here describes what exists in the code today.

## Local setup

See `README.md` (Docker for PostgreSQL, uv for the backend, npm for the frontend). `docker compose up -d db` starts PostgreSQL 16 and creates two databases on first start: `permitflow` (development) and `permitflow_test` (pytest). `docker compose --profile full up` also builds and runs the backend container with a volume at `/data/uploads`.

## Environment variables

| Variable | Default | Used by | Notes |
|----------|---------|---------|-------|
| `APP_ENV` | `development` | backend | `development`, `test` or `production`. `test` selects `TEST_DATABASE_URL` and disables the login rate limiter. |
| `DATABASE_URL` | local Postgres | backend | Postgres only (`postgresql+psycopg://`). |
| `TEST_DATABASE_URL` | local `permitflow_test` | pytest, CI | Truncated between tests. |
| `JWT_SECRET` | empty | backend | Required (at least 16 random characters) in every environment, tests included; the `.env.example` placeholder is refused; the app does not start without it. |
| `JWT_EXPIRES_MINUTES` | `480` | backend | 8 hours. |
| `CORS_ORIGINS` | `http://localhost:3000` | backend | Comma separated allowlist. |
| `UPLOAD_DIR` | `./data/uploads` | backend | Local disk storage; Railway volume at `/data/uploads`. |
| `UPLOAD_MAX_BYTES` | `10485760` | backend | 10 MB. |
| `LOGIN_RATE_LIMIT_PER_MINUTE` | `10` | backend | Failed attempts per IP per minute. |
| `RATE_LIMIT_PER_MINUTE` | `240` | backend | Every request per client IP, sliding minute; 429 with `Retry-After` beyond it. 0 disables. Per process (US-058). |
| `LOGIN_ATTEMPTS_PER_MINUTE` | `20` | backend | Sign-in attempts of any outcome per client IP per minute (each costs an Argon2 hash). 0 disables. |
| `MAX_DRAFTS_PER_USER` | `20` | backend | Open drafts an operator may hold; the next create is a 409. 0 disables. |
| `AI_RUNS_PER_USER_PER_DAY` | `60` | backend | Verification runs per applicant over a rolling day; beyond it a run is stored `unavailable` (`daily_limit_reached`) and nothing is sent to the model. 0 disables. |
| `AI_RUNS_PER_DAY` | `1000` | backend | The platform-wide ceiling on model calls per rolling day: the cost brake. 0 disables. |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_TIMEOUT_SECONDS` | 10 / 20 / 5 | backend | SQLAlchemy pool per process; when every connection is busy for longer than the timeout the request is answered 503 `unavailable` (US-044). Size for the number of uvicorn workers times concurrent requests |
| `TRUSTED_PROXIES` | empty | backend | Comma-separated proxy IPs whose `X-Forwarded-For` is trusted for every per-client limiter, or `*` when the platform edge proxy is the only peer (Railway) |
| `TEST_LIVE_AI` | unset | tests | Set to `1` to let the pytest suite call the live OpenAI provider; otherwise tests force `AI_PROVIDER=mock` regardless of `.env`. |
| `AI_PROVIDER` | `mock` | backend | `mock` or `openai`. |
| `OPENAI_API_KEY` | empty | backend | Required when `AI_PROVIDER=openai`. |
| `OPENAI_MODEL` | `gpt-4.1-mini` | backend | Structured outputs required; `gpt-4.1-mini` measured fastest and cheapest for extraction on 19 Sep 2026 (see `docs/07-ai/AI_VERIFICATION_DESIGN.md`). |
| `AI_TIMEOUT_SECONDS` | `30` | backend | Per call. |
| `AI_CONFIDENCE_THRESHOLD` | `0.6` | backend | Below this, `verified` becomes `needs_review`. |
| `AI_MAX_TEXT_CHARS` | `20000` | backend | Extraction cap sent to the provider. |
| `LANGSMITH_API_KEY` | empty | backend | Turns on LangSmith tracing of every OpenAI check (US-055). Empty: no tracing, no network call. |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` | backend | Must match the organisation's region (fixed at sign-up): `eu.api.` for EU, `apac.api.` for APAC (Sydney). |
| `LANGSMITH_PROJECT` | `permitflow` | backend | Project name the traces land in; use one per environment (`permitflow-dev`, `permitflow`). |
| `LANGSMITH_HIDE_INPUTS` | `true` | backend | Keeps the document text and form section out of the trace; outputs (status, codes, confidence, summary, evidence quotes of at most 300 characters) stay. `false` only in development. |
| `METRICS_TOKEN` | empty | backend | Turns on `GET /api/v1/metrics` for Prometheus (US-077); the scraper presents it as a bearer token. Empty: the route answers 404. Generate with `openssl rand -hex 24`; one value per environment, the same value in that environment's Prometheus scrape config. |
| `METRICS_TARGET`, `METRICS_SCHEME`, `ENVIRONMENT_LABEL` | `host.docker.internal:8000`, `http`, `local` | Prometheus (Compose) | Where the local Prometheus scrapes and how it labels the environment; `backend:8000` with the `full` profile. Not read by the app. |
| `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`, `GRAFANA_ROOT_URL` | `admin`, `permitflow`, `http://localhost:3001` | Grafana (Compose) | The local Grafana sign-in and its public URL. Not read by the app. |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | frontend | Build-time, read from `frontend/.env` (not the repo root). In the container the runtime `API_URL` wins. |

## Seeding

`cd backend && uv run python scripts/seed.py` creates the demo operator (`operator@permitflow.example.sg`) and officer (`officer@permitflow.example.sg`) if they do not exist. `SEED_PASSWORD` sets their password (default `PermitFlow!2026`). The public demonstration keeps that password on purpose (README, privacy policy); any deployment that is not a demonstration must set its own value and reset it on a schedule.

## Uploads

Files are written under `UPLOAD_DIR` as `<application_id>/<random>.<ext>` (never the client file name), atomically via a `.part` temp file. Issued licence certificates live beside them as `<application_id>/licence-<licence_no>.pdf`, written by the approval transaction and referenced from `licences.stored_key` with a `sha256` (US-051). Deleting a document only clears `is_current`; the file stays for the revision history. Tests use `./data/test-uploads` and clean it after every test.

## Health

`GET /api/v1/health` → `200 {"status":"ok","database":"ok"}` or `503 {"status":"degraded","database":"unreachable"}`. Provider configuration is never exposed here.

## Logs

JSON lines on stdout: one `request` line per request with `request_id`, method, path, status, duration and user id. The request id is echoed in the `X-Request-ID` response header and shown to users on 500 responses. No payloads or document text are logged.

## Migrations

`cd backend && uv run alembic upgrade head`. New migration: `uv run alembic revision --autogenerate -m "<what>"`, then review the file. The container image runs `alembic upgrade head` on start.

Compatibility rule (since 20 Sep 2026): a migration must leave the schema readable by the previous release. Add columns nullable or with a default; never rename or drop a column or table in the same release as the code that stops using it (drop it one release later). This is what keeps an image rollback safe: the older image runs against the newer schema without knowing it changed. Reviewed by hand on every migration; the five migrations shipped so far follow it.

## CI (US-006)

![CI/CD: the four GitHub Actions workflows and their jobs](../03-architecture/diagrams/views/ci-cd-pipeline.png)

`.github/workflows/ci.yml`, seven jobs: backend (ruff, mypy, pytest on a Postgres service), frontend (lint, typecheck, vitest, build), AI gate (calls `ai-gate.yml`: model approval, contracts, golden set, adversarial, fairness, verdict; all on the mock provider, blocking), dependency and code audit (pip-audit, bandit, npm audit, all blocking since US-058), E2E (the full stack started inside the job: Postgres service, `alembic upgrade head`, `scripts/seed.py`, uvicorn on :8000 with `AI_PROVIDER=mock` and a CI-only `JWT_SECRET`, `vite preview` on :3000, then `npm run e2e`), gitleaks, and images (both Docker images built; on `dev` and `main` pushed to GHCR, after every other job is green). The E2E job needs the two test suites first. On failure it prints the last 200 lines of both server logs and uploads `playwright-report` and `test-results` as an artifact for seven days. CI does not deploy; `deploy.yml` does, after CI (see Deployment). `ai-eval.yml` is the fourth workflow (with `ai-gate.yml`, which CI calls): the golden set and the fairness check against the real OpenAI model, nightly at 04:00 Singapore, by hand, and on pushes to `dev` or `main` that touch the AI module or the set; blocking at 14 of 14; needs the `OPENAI_API_KEY` repository secret and skips nothing silently (it fails with a clear error when the secret is missing).

## Deployment (US-007)

### Shape

![Deployment: images built once in CI, pulled by tag into two Railway environments, production behind an approval](../03-architecture/diagrams/views/deployment.png)

One Railway project (`permitflow`), two environments that share nothing:

| | development | production |
|---|---|---|
| Deploys from | `dev` | `main` (release tags `v0.<sprint>.0`) |
| Images | `ghcr.io/suhaasnv/permitflow-backend:dev`, `...-frontend:dev` (moving tags, every merge) | pinned `sha-<commit>`: `sha-2226d11` since 20 Sep 2026 (v0.3.0 plus the post-release fixes recorded in `CHANGELOG.md`, deployed at the owner's decision without a new version; the git tag `v0.3.0` and the `:v0.3.0` images still name the 19 Sep build `38df991`) |
| Frontend | https://dev.permitflow.space (US-052; Railway host https://frontend-development-afe2.up.railway.app) | https://permitflow.space (also `www`; Railway host https://frontend-production-2d8b.up.railway.app) |
| API | https://api.dev.permitflow.space/api/v1 (US-052; Railway host https://backend-development-4e04.up.railway.app/api/v1) | https://api.permitflow.space/api/v1 (Railway host https://backend-production-19cd.up.railway.app/api/v1) |
| State (19 Sep 2026) | live: deployed on every merge to `dev`, seeded | live since v0.3.0 (19 Sep, 17:00 SGT): images `ghcr.io/suhaasnv/permitflow-{backend,frontend}:main` attached, first deployment committed from the Railway staging area, then the approved `deploy.yml` run redeployed with the health gates; seeded once; production UAT recorded in `docs/10-uat/UAT_PLAN.md`; reset after the UAT and left with one example application (Serangoon Spice House, Application Received) |
| Database | own Postgres 18 service | own Postgres 18 service |
| Uploads | volume `uploads` at `/data/uploads` | own volume at `/data/uploads` |
| AI | `AI_PROVIDER=openai`, `gpt-4.1-mini` | same |

Two images, built once in CI and pulled by Railway (Railway never builds): `backend/Dockerfile` (uvicorn, runs `alembic upgrade head` on start) and `frontend/Dockerfile` (Vite build served by nginx; the API URL is written into `config.js` at container start from `API_URL`, so one image serves both environments). Images are public packages on GHCR, tagged `sha-<commit>` and with the branch name on every branch push. A release tag (`:v0.3.0`) is written only by the CI run for that git tag (`on: push: tags: v*`), and that run refuses a tag that does not match `frontend/package.json`; so a release image is immutable and a later merge to `main` cannot overwrite it (this was not the case before 20 Sep 2026: `v<version>` was written on every `main` push, and the `:v0.3.0` tag did get rewritten with documentation-only commits; the running production containers were and are the `sha-38df991` build).

### Continuous deployment, one push at a time

1. Push to `dev` (or `main`). `ci.yml` runs: backend, frontend, AI verification, gitleaks, dependency audit, then the E2E job against a stack started in the runner.
2. Green → the `images` job builds both images and pushes them to GHCR (`:dev` or `:main`, plus `sha-<commit>`). Pull requests build but never push. A `v*` tag push runs CI again and writes the `:v0.x.0` tags.
3. `deploy.yml` runs when CI completed successfully on that branch. Using the environment's `RAILWAY_TOKEN` it calls `railway redeploy --from-source` for `backend` and `frontend` in the matching Railway environment, which pulls the new images.
4. The job records the deployment id that is live before the redeploy and then waits until Railway reports a deployment with a different id as SUCCESS (a redeploy call returns before the rollout, and the old containers keep answering meanwhile; accepting the first SUCCESS in the list would pass on the previous rollout, which the job did until 20 Sep 2026); Railway's own health checks (`/api/v1/health`, `/healthz`) gate the rollout too.
5. Production: the production services do not track a branch tag; each is pinned to the release image `sha-<commit>` in Railway. A release is: merge the `dev` pull request into `main`, tag `v0.x.0`, wait for the tag's CI run, set both production services to `sha-<release commit>` (Railway dashboard, service Settings, Source), then run the deploy job by hand: `gh workflow run deploy.yml --ref main -f environment=production`. The job pauses at the GitHub `production` environment until a required reviewer (the repository owner) approves it in the Actions run. Development needs no approval. Known limit, found at the v0.3.0 release: a `workflow_run`-triggered job executes on the repository's default branch (`dev`), and the production environment's branch policy admits only `main`, so an automatic production job would be rejected before its first step. The workflow therefore listens for CI on `dev` only and production is deployed by hand: `gh workflow run deploy.yml --ref main -f environment=production` after CI is green on `main`; the approval gate still applies. (Making `main` the default branch would restore the automatic path; not done, because `dev` is where pull requests land.) Either environment can also be redeployed from its current images by hand with "Run workflow" on the Deploy workflow (choose the environment), for example after a platform incident.
6. Post-deploy gates: `/api/v1/health` and `/healthz` must answer 200 within about seven minutes, and the frontend's `config.js` must name that environment's API. A failed gate marks the deployment red; the previous containers keep serving until the new ones are healthy (Railway's default).

The GitHub `production` environment only accepts deployments from `main`. Development and production cannot affect each other: separate databases, volumes, secrets, URLs, and a project token scoped to one environment each.

### Secrets and variables

| Where | Name | Purpose |
|---|---|---|
| Railway backend service (per environment) | `APP_ENV`, `DATABASE_URL` (`${{Postgres.DATABASE_URL}}`), `JWT_SECRET` (distinct per environment), `JWT_EXPIRES_MINUTES`, `CORS_ORIGINS` (that environment's frontend URL), `UPLOAD_DIR=/data/uploads`, `TRUSTED_PROXIES=*` (the Railway edge is the only peer), `AI_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT`, `LANGSMITH_PROJECT`, `LANGSMITH_HIDE_INPUTS` (optional, tracing), `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `PORT=8000` | runtime configuration |
| Railway frontend service (per environment) | `PORT=8080`, `API_URL` | written into `config.js` at start |
| GitHub environment secret (`development`, `production`) | `RAILWAY_TOKEN` | a Railway **project token** scoped to that one environment (Project settings, Tokens); created by the owner in the dashboard |
| GitHub repository variable | `RAILWAY_PROJECT_ID` | which project to redeploy |
| GitHub repository secret | `OPENAI_API_KEY` | the live AI evaluation (`ai-eval.yml`); a key of its own, so it can be rotated apart from the runtime key (`gh secret set OPENAI_API_KEY`) |
| GitHub repository secret and variable (optional) | `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT` | when present, `ai-eval.yml` also records each run as a LangSmith experiment (US-055); the secret is set, the endpoint is the US default |
| GitHub environment variables | `BACKEND_URL`, `FRONTEND_URL` | the post-deploy gates |

`postgresql://` URLs from Railway are accepted as-is: settings add the `+psycopg` driver.

### Seeding

The database starts empty. `scripts/seed.py` creates the two demo accounts only (idempotent). It is not part of a deploy on purpose, a deploy must never touch data; run it once per environment: `railway ssh --environment development --service backend -- .venv/bin/python scripts/seed.py` (and `--environment production` for production). Development was seeded on 19 Sep 2026; production on 19 Sep 2026 after the v0.3.0 deploy. Accounts and password in every environment: `operator@permitflow.example.sg` and `officer@permitflow.example.sg`, password `PermitFlow!2026` (the `SEED_PASSWORD` default; deliberately public for the demonstration, see the privacy policy). To change it, set `SEED_PASSWORD` and re-run the seed: existing accounts keep their password (the script is create-only), so a rotation is a new seed plus a manual update, or a reset of the environment.

### Custom domain (US-052)

Both environments live on the owner's domain with one convention: the environment name is a subdomain, the API is `api.` in front of it.

| | Frontend | API |
|---|---|---|
| production | `permitflow.space`, `www.permitflow.space` | `api.permitflow.space` |
| development | `dev.permitflow.space` | `api.dev.permitflow.space` |

In Railway, per environment: frontend service → Settings → Networking → Custom domain (the frontend hosts); backend service → the API host. Railway shows the CNAME target for each; the owner adds those records at the registrar (the apex `permitflow.space` may need the registrar's ALIAS/ANAME record or Railway's provided A records; the others are plain CNAMEs). Then set per environment: backend `CORS_ORIGINS` to that environment's frontend origins, frontend `API_URL` to that environment's API host plus `/api/v1`; GitHub environment variables `FRONTEND_URL` and `BACKEND_URL` to the same hosts so the deploy health gates check them. The railway.app hosts keep working as fallbacks. TLS is issued by Railway once DNS resolves (minutes to an hour).

### Observability (US-077)

What the platform tells about itself, in three layers: structured request logs with a request id (every request, `core/logging.py`), LangSmith traces for the AI checks (US-055, inputs hidden), and, since 20 Sep, Prometheus metrics with a Grafana dashboard and alert rules.

**The endpoint.** `GET /api/v1/metrics` (`api/v1/metrics.py`) renders the process's counters and histograms in the Prometheus text format. It is off unless `METRICS_TOKEN` is set, requires that token as a bearer, is exempt from the per-client limiter (the monitor must keep answering while a client is being refused) and does not count its own scrapes. Labels are route templates and enum values; no id, no text, no personal data ever enters a label. Metric families: `permitflow_http_requests_total{method,route,status}`, `permitflow_http_request_seconds{method,route}`, `permitflow_rate_limited_total`, `permitflow_verification_runs_total{outcome,provider}`, `permitflow_verification_run_seconds{provider}`, `permitflow_quota_refusals_total{quota}`, `permitflow_transitions_total{target,actor}`, `permitflow_applications{status}` (a gauge read from the database on each scrape), `permitflow_openai_tokens_total{model,kind}` (prompt, cached, completion, from the usage OpenAI reports on every call). Counters are per process and reset on restart; Prometheus's `rate` and `increase` handle that.

**Locally.** `docker compose --profile observability up -d` starts Prometheus (`:9090`, scraping `host.docker.internal:8000` every 15 s with the token from `.env`, rendered from `docker/observability/prometheus.local.yml` by `prometheus-start.sh`; alert rules from `alerts.yml`) and Grafana (`:3001`, sign-in from `GRAFANA_ADMIN_*`, the Prometheus datasource and the dashboard provisioned from `docker/observability/grafana/`). The dashboard JSON is generated: edit `build_dashboard.py`, run it, Grafana picks the file up within 30 s. Sections: a header and stat strip; "Is the API healthy?" (requests by status class, latency p50/p95/p99.5 against the 500 ms objective, 5xx share, slowest routes, rate-limit refusals, quota refusals); "Are the document checks healthy?" (finished per hour by outcome, check time against the 3 minute objective, failed-or-unavailable share, by provider); "What are the document checks costing?" (spend in the selected range, tokens, cost per check, projected monthly spend, tokens and dollars per hour, at gpt-4.1-mini's list price of USD 0.40 per million input tokens, 0.10 cached, 1.60 output; an estimate, the invoice is the truth); "Is the queue moving?" (applications by status, transitions per hour, waiting on the officer, waiting on the operator). The `Environment` variable selects `local`, `development` or `production`.

**Alert rules** (`docker/observability/alerts.yml`, evaluated by Prometheus; routing to a channel is the next step): `PermitFlowApiDown` (no scrape for 2 min), `PermitFlowApiErrorBurst` (5xx above 1 % for 5 min), `PermitFlowApiSlow` (p99.5 above 500 ms for 10 min), `PermitFlowChecksFailing` (failed or unavailable above 20 % for 15 min), `PermitFlowChecksSlow` (check p95 above 3 min), `PermitFlowRateLimiting` (more than one refusal a second for 10 min).

**On Railway** (development environment, two services from the public images, no image build): `prometheus` (`prom/prometheus:v3.5.0`, private network only, volume at `/prometheus`, 30 day retention) renders its config at start from the variables `PROMETHEUS_CONFIG` (`docker/observability/prometheus.railway.yml`: two jobs, `api.dev.permitflow.space` and `api.permitflow.space` over HTTPS, one token each from `DEV_METRICS_TOKEN` and `PROD_METRICS_TOKEN`) and `PROMETHEUS_ALERTS`; `grafana` (`grafana/grafana-oss:12.1.0`, volume at `/var/lib/grafana`, healthcheck `/api/health`) writes its provisioning files at start from `GF_PROVISION_DATASOURCE`, `GF_PROVISION_DASHBOARDS` and `GF_DASHBOARD_PERMITFLOW`, reads Prometheus at `http://prometheus.railway.internal:9090`, and is public at `https://grafana.dev.permitflow.space` (CNAME to the Railway host, sign-in only, no anonymous access, no sign-up). Each backend carries its own `METRICS_TOKEN`; a token is rotated by setting the new value on the backend and in the Prometheus variable, then redeploying both. The start commands are recorded in `notes/observability/railway-secrets.sh` alongside the variable names; secrets are set by the owner, never through the assistant.

**What is not there yet:** Alertmanager (the rules fire inside Prometheus and show on its Alerts page; nothing pages anyone), an nginx exporter for the frontend tier, `postgres_exporter`, and a second Prometheus for production isolation (one instance scrapes both environments today, which is fine for a demonstration and wrong for a real authority).

### Rollback

Three layers, one solved, two planned.

**Code (solved).** Every image carries a `sha-<commit>` tag and every release a `v<version>` tag, and production is pinned to a `sha-` tag, so a rollback is: set the two production services back to the previous release's `sha-` tag in the Railway dashboard and run the deploy job (approval and health gates apply). Development tracks `:dev` and rolls back by pointing at a `sha-` tag the same way. Migrations are forward-only; a rollback that needs a schema change is a new migration.

**Schema (rule, not tooling).** There is no `alembic downgrade` in production. The compatibility rule under Migrations (add nullable, drop one release later) is what makes a code rollback safe across a release that changed the schema; the older image reads the newer tables. A release that cannot honour the rule ships its schema change one release ahead of the code that needs it.

**Data (planned, readiness rows 13 and 14).** Today: Railway's managed Postgres backups (point-in-time restore from the dashboard), no backup of the uploads volume, no restore drill. Before real users: a nightly `pg_dump` and a copy of the uploads volume to object storage (30 days), one restore drill into a scratch environment, and a staging environment cloned from production data so a migration is rehearsed before it reaches production. Order: backups and the drill first, staging second.

**Observability.** The two monitoring services roll back like any image service (previous tag, redeploy); their data volumes persist. A wrong dashboard or rule is a variable: set the previous file content and redeploy.

**Configuration.** A wrong variable (a CORS origin, a quota, a model name) is rolled back by setting the previous value in Railway (Variables) and redeploying; Railway keeps the variable history per service, so the previous value is visible there. The values that matter are listed in the Secrets and variables table above; nothing is derived at build time except the frontend's `API_URL`, which is read at container start.

**AI prompt.** The verifier's prompt is versioned in code (`PROMPT_VERSION` in `openai_provider.py`, stamped on every run and trace). A bad prompt is rolled back like any code change: previous pin, deploy job. Runs made under the bad version stay in the database with their version, so they can be listed and re-run (the re-run button, or a script over `verification_runs` where `prompt_version = ...`).

**Secrets.** Rotation, not rollback: a new `JWT_SECRET` signs every user out (8 hour tokens, accepted); `OPENAI_API_KEY` and `LANGSMITH_API_KEY` are replaced in Railway and, for the evaluation workflow, in the GitHub repository secret, then the service restarts. The OpenAI key is due for rotation after the assessment; the LangSmith key expires on its own after three months.

**A rollout that never became healthy** needs no rollback: Railway keeps the old containers serving until the new ones pass `/api/v1/health` and `/healthz`, and the deploy job goes red.

### Verified

Development: both health endpoints 200 after the first commit, demo accounts seeded, and `e2e/scenarios/02-reaches-officer.spec.ts` passed against the live URLs (19 Sep 2026).

Custom domain (US-052, 19 Sep 2026): five hostnames registered on Railway, ten DNS records at Namecheap (ALIAS at the apex, four CNAMEs, five `_railway-verify` TXT records, one per hostname), all five certificates issued within about 30 minutes. `CORS_ORIGINS` and `API_URL` set per environment; GitHub environment variables moved to the new hosts. Deploy run #6 (manual, development) green with the gates against `https://dev.permitflow.space` and `https://api.dev.permitflow.space`; scenario 02 passed through the domain with the CORS header confirmed. Note learned: Railway needs a TXT verification record per hostname, not only at the apex; deploy run #5 failed its config.js gate only because it ran between the variable change and the GitHub variable update.
