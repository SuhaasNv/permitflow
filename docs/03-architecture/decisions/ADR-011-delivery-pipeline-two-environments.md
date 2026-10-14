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
Option B, the "cut" version of C. Recorded for later under "What I would do next": promptfoo, Project Moonshot (AI Verify Foundation) for Singapore assurance evidence, Semgrep, CodeQL and Trivy. (LangSmith tracing, the live evaluation workflow and blocking audits were built later the same day; see the amendments in the ADR index.) Two Railway environments (`development`, `production`) with their own Postgres, `uploads` volume, variables and domains; images pulled from GHCR (`:dev`, `:main`, `sha-<commit>`); `deploy.yml` runs on `workflow_run` after a green CI on `dev`, and by hand with an environment choice (production is always by hand: a `workflow_run` job executes on the default branch, which the production environment does not admit), checks that the environment's secrets exist, calls `railway redeploy --from-source` per service, polls `railway deployment list` until the new deployment is `SUCCESS`, then curls `/api/v1/health`, `/healthz` and the frontend's `config.js`. The `production` GitHub environment requires the repository owner's approval and only accepts `main`. Seeding is a one-off command per environment (`railway ssh ... scripts/seed.py`). Both environments are served on the owner's domain with one convention (`permitflow.space` and `api.permitflow.space` for production, `dev.permitflow.space` and `api.dev.permitflow.space` for development) with Railway-managed TLS (US-052); the railway.app hosts stay as fallbacks.

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

## Amendment: security scanners join the pipeline (US-103, v0.5.0, 9 Oct 2026)

Context. The decision above left Semgrep and Trivy for "what I would do next" because a static-analysis pass needs a triage the schedule did not have. By v0.4.1 the gates (pip-audit, bandit, npm audit, gitleaks) were stable, and the second security audit named the container images, the source rules and the deployed site as the unscanned parts.

Decision. Add five stages, none of them a new service to host:
- **Semgrep** (`p/owasp-top-ten`, `p/python`, `p/typescript`) as a `semgrep` job in `ci.yml`, blocking at ERROR severity; `images` needs it. It runs through `uvx` at a pinned version, so no third-party action is in the path.
- **Trivy** on both built images inside the `images` job, before the push: the image is built into the runner, scanned, then built again for the push (a cache hit). Blocking at HIGH and CRITICAL where a fix exists; `.trivyignore` holds accepted findings with a reason and a date.
- **gitleaks over the whole history** as its own workflow (`secret-history.yml`), weekly and on demand, using the pinned release binary with a checksum so it can scan every ref (`--log-opts="--all"`). The push scan in `ci.yml` stays.
- **OWASP ZAP baseline** against the development site as a job after `deploy` in `deploy.yml`, report only (`continue-on-error`, no issues written), with the report uploaded as an artifact. It sits in `deploy.yml` and not in a workflow of its own because a `workflow_run` trigger runs the default branch's copy, and the scan must follow the deploy that was just made.
- **Dependabot** (`uv`, `npm`, `github-actions`), weekly, grouped, into `dev`.

Options considered. A Semgrep GitHub Action or Semgrep Cloud (needs an account and a token; the CLI needs neither). Trivy against the registry image after the push (it would scan on `dev` only, after a vulnerable image already exists in GHCR, and never on a pull request). CodeQL (a second static-analysis engine; deferred, the Semgrep packs cover the same classes for this stack). A ZAP full or active scan (it sends attack traffic; not against a site others use, and not without the owner's yes). The gitleaks action for the history scan (its behaviour on scheduled events is not documented as a full-history scan; the binary with `--all` is explicit).

Consequences. A fixable HIGH in a base image now fails the build until the Dockerfile or the base tag moves (the frontend image needed `apk upgrade` before the first run). A vulnerability published tomorrow can break a green `dev` without any code change, which is the point. The required checks on `main` are set in the repository settings: the `Semgrep` job is not a required check until the owner adds it, but `Images` (which needs it and runs Trivy) is already one, so it is gated either way. The new actions are pinned to commit SHAs with the version in a comment and Dependabot keeps them current; the older actions in `ci.yml` still use version tags. The scheduled history scan, Dependabot and the `workflow_run`-driven ZAP job take effect only once their files are on the default branch.

Revisit when: the ZAP report shows the same alerts for a month with nothing actionable (tune it with a rules file, or stop), a real finding needs an ignore mechanism Semgrep lacks, or a staging environment exists and an active scan can run against it.

Links: US-103 (`docs/05-planning/USER_STORIES.md`), `docs/06-security/SECURITY_REVIEW.md` (scanner table and the planted-secret proof), `docs/09-operations/OPERATIONS.md` (CI section).

## Amendment: the scanned image is the pushed image, and the pipeline's supply chain is pinned (9 Oct 2026, wave 1 review)

Context. The review of the US-103 pipeline found four weaknesses in the `images` job: Trivy ran as a third-party action after `docker/login-action` had written a `packages: write` token to the runner; the scanned image and the pushed image were two separate builds, so the scan proved a cache hit, not the artefact; a Trivy database or Semgrep rules outage could block a release tag; and the older actions were pinned to tags (movable), not commit SHAs.

Options considered. (a) Scan the pushed image by digest after the push, to a staging tag: the scan then covers the exact artefact, but a vulnerable image already exists in GHCR, and a failed scan leaves a tag to clean up. (b) Keep two builds and rely on the cache: the status quo, rejected because nothing proves they are the same image. (c) Build once, load into the runner, scan, then push the loaded image: the artefact is the scanned one and nothing reaches GHCR unless the scan passed. Chosen: (c). The cost is that a pushed image carries no buildx provenance attestation (`docker push` of a loaded image has none), which nothing here consumes.

Decision. Trivy is the pinned release binary (version and SHA-256 in the job's `env`, as gitleaks is in `secret-history.yml`), replacing `aquasecurity/trivy-action`; the GHCR login moves after both scans; the image that was scanned is tagged and pushed with `docker push`. The Trivy database comes from the public ECR mirror with three attempts, and the job fails, never skips, if they all fail. Semgrep is retried once when a run cannot complete. Every action in `ci.yml`, `deploy.yml`, `ai-gate.yml`, `ai-eval.yml` and `secret-history.yml` is pinned to a commit SHA with the version in a comment, and the Railway CLI in `deploy.yml` is installed at an exact version. This supersedes "scanned, then built again for the push" and "the older actions still use version tags" in the amendment above.

Consequences. A Trivy failure on a release tag is triaged on `dev` (base image bump, or a `.trivyignore` entry with a reason, an owner and an expiry) and released as a new candidate; the tag is never moved or re-used (`docs/09-operations/RELEASING.md`). Dependabot's weekly `github-actions` pull request now rewrites a SHA and its comment together.

Revisit when: the pipeline needs image attestations or an SBOM (then push by digest from buildx and attest), or the public ECR mirror stops being maintained.

Links: `docs/09-operations/OPERATIONS.md` (CI section), `docs/09-operations/RELEASING.md`, `docs/06-security/SECURITY_REVIEW.md`.
