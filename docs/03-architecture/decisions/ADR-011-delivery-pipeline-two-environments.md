# ADR-011: Delivery pipeline: images built once, two Railway environments, production behind a person

Date: 19 September 2026. Stories: US-006, US-007, US-052. Status: accepted, built (production first deployed with v0.3.0).

## Context
ADR-009 chose GitHub Actions and Railway. As the CI grew (seven jobs, end-to-end tests inside the job, an AI evaluation gate, dependency and secret audits) the questions became: where are the containers built, how do `dev` and `main` map to environments, what stops a green CI on a weekend from changing production, and how much observability tooling is worth adding in a three-day window.

## Constraints
- A reviewer must be able to open a stable URL; a broken deploy must not take it down silently.
- Development and production must share nothing (database, files, secrets), so test data never appears in the demo.
- Production changes need a human decision; development should not.
- One engineer: every extra tool is a thing to keep green.

## Options Considered

### Option A: Railway builds from the repository on push
- Pros: zero pipeline code.
- Cons: the artefact Railway runs is not the one CI tested; two builds per change; no rollback by tag; Railway's builder decides the Python and Node versions.

### Option B: CI builds both images once, pushes them to GHCR, Railway pulls by tag; `dev` deploys `development` automatically, `main` deploys `production` after a required reviewer approves the GitHub Actions job; the deploy job waits for the new rollout and gates on health
- Pros: the tested artefact is the deployed artefact; `sha-<commit>` tags give rollback by retagging; the approval gate is a GitHub environment rule, visible in the run; health gates fail the job instead of leaving a dead site.
- Cons: two registries of truth (GHCR tag, Railway deployment) to keep in mind; `railway redeploy` returns before the rollout, so the job must poll the new deployment.

### Option C: Option B plus promptfoo for the prompt (threshold gate and red team), Langfuse or LangSmith tracing, Semgrep and CodeQL, Trivy on the images, and a staging environment
- Pros: richer evidence, per-run traces, prompt red-teaming.
- Cons: three more services and keys to configure and explain; the prompt gate that matters (golden set in CI) already exists in `evals/`; SAST findings would need a triage pass the schedule does not have.

## Decision
Option B, the "cut" version of C. Recorded for later under "What I would do next": promptfoo, Project Moonshot (AI Verify Foundation) for Singapore assurance evidence, Semgrep, CodeQL and Trivy. (LangSmith tracing, the live evaluation workflow and blocking audits were built later the same day; see the amendments in the ADR index.) Two Railway environments (`development`, `production`) with their own Postgres, `uploads` volume, variables and domains; images pulled from GHCR (`:dev`, `:main`, `sha-<commit>`); `deploy.yml` runs on `workflow_run` after a green CI on `dev` or `main` (and by hand with an environment choice), checks that the environment's secrets exist, calls `railway redeploy --from-source` per service, polls `railway deployment list` until the new deployment is `SUCCESS`, then curls `/api/v1/health`, `/healthz` and the frontend's `config.js`. The `production` GitHub environment requires the repository owner's approval and only accepts `main`. Seeding is a one-off command per environment (`railway ssh ... scripts/seed.py`). Both environments are served on the owner's domain with one convention (`permitflow.space` and `api.permitflow.space` for production, `dev.permitflow.space` and `api.dev.permitflow.space` for development) with Railway-managed TLS (US-052); the railway.app hosts stay as fallbacks.

## Rationale
Build once, promote by tag, gate on a person and on health: the shortest pipeline that a reviewer can read in one file and that cannot deploy something CI did not test.

## Consequences

### Positive
- Rollback is `railway redeploy` of a previous `sha-` tag; no rebuild.
- The approval step doubles as a change record: who approved which commit, when.
- Development gets every merge to `dev` within about eight minutes of the push.

### Negative / Tradeoffs
- Single region, one replica per service, no blue/green: a deploy is a short restart (Railway healthchecks keep the old container until the new one answers).
- The deploy job depends on the Railway CLI's output shape for polling.
- Migrations run on container start (`alembic upgrade head`); a bad migration fails the health gate rather than being rehearsed on a staging copy.

## Validation
- `deploy.yml` runs #3 and #4 green on development (automatic and manual), including the wait-for-rollout fix after run #2 tested the old container.
- Development URLs answer their health checks; `config.js` names the development API.
- Production: variables, volume, domains and the approval rule are configured; first deploy at v0.3.0 (`docs/09-operations/OPERATIONS.md`).
