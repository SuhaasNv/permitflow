# Releasing PermitFlow

How a version moves from `dev` to production. Adopted on 8 Oct 2026 at the owner's request. It is first used for v0.4.1.

The idea comes from how phone operating systems ship: a release candidate is a build you test as if it were the release, and **the release is that tested candidate with the label removed**: the same image, not a rebuild (see "Build once, promote by digest" below). A problem found in a candidate is fixed on `dev` and becomes a new candidate. It is never patched on `main`.

Branching rules stay in `BRANCHING.md`, and environments, deploys and rollback in `OPERATIONS.md`. This file is the order of the steps.

## Names

| Stage | Where | Version in the five version files | Git tag | Images |
|---|---|---|---|---|
| Work in progress | `dev`, story branches | the last release or candidate, unchanged | none | `:dev`, `sha-<commit>` |
| Release candidate | `dev` | `X.Y.Z-rc.N` (`backend/pyproject.toml` and `uv.lock`: `X.Y.ZrcN`) | `vX.Y.Z-rc.N` on the `dev` commit | `:vX.Y.Z-rc.N` |
| Release | `main` | `X.Y.Z` | `vX.Y.Z` on the `main` merge commit | `:vX.Y.Z`, `:main` and `sha-<merge>`: the last candidate's images under new names (same digest, nothing built); production pinned to `sha-<merge>` |

The five version files are `frontend/package.json`, `frontend/package-lock.json`, `backend/pyproject.toml`, `backend/uv.lock` and `backend/app/core/version.py`. CI refuses a tag that differs from `frontend/package.json`.

## 1. Cut a release candidate

Do this when `dev` holds everything the version should contain and the full local run is green.

1. On a `chore/rc-X.Y.Z-rc.N` branch from `dev`, set the version to `X.Y.Z-rc.N` in the five files. Add a candidate section to `RELEASE_NOTES.md`: `## vX.Y.Z-rc.N, D Month YYYY: title`, with the usual audience blocks, describing what this candidate changed, in the users' words. It sits among the releases in date order, newest first. The development environment lists it on What's new with a Release candidate label; production hides every candidate section, so the notes of a released version never mention candidates.

   **Every candidate also writes or updates the upcoming release's own section**, `## vX.Y.Z, D Month YYYY: title`, in the same file, gathering what the candidates so far changed (no mention of candidates; the heading carries the planned release day). Nobody knows in advance which candidate will be the last, and the release commit may not touch `RELEASE_NOTES.md` (the notes are bundled into the frontend image, so the file is part of what the guard compares). What's new hides every section newer than the running version, with candidates ordered before their release (`0.5.0-rc.2` < `0.5.0-rc.10` < `0.5.0`): a candidate on dev never shows the release section, and production running `X.Y.Z` does. The release guard fails a release whose last candidate has no `## vX.Y.Z, ` section.
2. Merge it into `dev` with `--no-ff`. Run the full local run (pytest, ruff, mypy, the AI gate, vitest, lint, typecheck, build, Playwright). Push `dev`, which needs the owner's yes.
3. Once CI is green on that commit, tag it: `git tag -a vX.Y.Z-rc.N -m "PermitFlow vX.Y.Z-rc.N"` and `git push origin vX.Y.Z-rc.N` (yes). The tag's CI run does not rebuild: it names the image dev already built and is running for that commit (`sha-<commit>`) as `:vX.Y.Z-rc.N`, by digest. Tag only after CI is green on the commit and the dev deploy has run, so that image exists. **If it does not, the tag run fails and builds nothing** ("no dev image sha-<commit> ...: dev never built this commit, so it cannot be a candidate"): wait for the dev push run of that commit to finish, then re-run the failed job. Never work around it with a build on the tag.
4. Wait for the development deploy. Check that `https://api.dev.permitflow.space/api/v1/health` reports `X.Y.Z-rc.N` and the tagged commit.

## 2. Test the candidate on dev

- Run the stories' acceptance checks in a browser on https://dev.permitflow.space as each role, at 390, 820 and 1280 px. Use scratch applications for anything destructive.
- Record the run in `docs/10-uat/UAT_PLAN.md`: date, candidate, what passed and what failed.
- **Any fix goes to `dev` through a story or fix branch**, then becomes the next candidate (`rc.N+1`, steps 1 to 2 again). Nothing is fixed on `main`.

A candidate is **stable** when the full local run is green, CI on its commit is green, the dev deploy reports it, and the browser run passed with no open finding of medium severity or above.

## 3. Release

1. On a `chore/release-vX.Y.Z` branch from the stable candidate's commit (the label commit), change only:
   - the five version files: `X.Y.Z-rc.N` becomes `X.Y.Z`, the version lines and nothing else in them
   - `CHANGELOG.md`: the release entry
   - the README and other documents, if they name the current production version

   **Nothing else, and not `RELEASE_NOTES.md`**: the release section was written in the candidate (section 1). If the release day or the wording must change, that is a new candidate. Merge the label commit into `dev`, push (yes), and wait for CI. CI builds this commit like any `dev` commit, for the `:dev` image; production does not run that build.
2. Open the pull request from `dev` into `main` (yes). Merge it when every check is green (yes). The push to `main` builds nothing: CI runs the release guard on the merge commit (`release_guard.py vX.Y.Z --rev <merge>`) and gives the last candidate's images the names `:main` and `sha-<merge>`.
3. Tag the merge commit `vX.Y.Z` and push the tag (yes). The tag's CI run again builds nothing: it runs the guard and writes `:vX.Y.Z` (and `sha-<merge>`) on the candidate's digest. **The release guard** (`scripts/release_guard.py`, run in CI on the push to `main` and on every `v*` tag) fails the release if:
   - the tag is not `vX.Y.Z`
   - the version files disagree with the tag
   - no `vX.Y.Z-rc.N` tag exists for the version
   - the last candidate's `RELEASE_NOTES.md` has no `## vX.Y.Z, ` release section
   - any shipped file (`backend/`, `frontend/`, `docker/`, `docker-compose.yml` and `RELEASE_NOTES.md`, apart from the version lines) differs between the last candidate tag and the release tag
4. Deploy production (yes). Stage both production services onto `sha-<merge>` in Railway (that name is the candidate's digest), review the staged change, and commit it; then run the deploy job with the version: `gh workflow run deploy.yml --ref main -f environment=production -f version=X.Y.Z`. It sets `APP_VERSION=X.Y.Z` on the backend and frontend and fails unless `/health` and `config.js` report `X.Y.Z` (`OPERATIONS.md`, Deployment).
5. Verify with checks only the new version passes:
   - `/health` reports `X.Y.Z` and **the candidate's commit** (the commit the image was built from), not the merge commit; the commit shown on production is the tested candidate's, and `sha-<merge>` and `:vX.Y.Z` name that same image
   - metrics answer 401 without the token
   - the site and `/releases` answer with the new bundle
   - one request that uses something new in this version
6. Run the seed once if the version adds seeded accounts. For the version that carries US-103, also rotate production's `operator@`, `officer@` and `officer2@` demonstration accounts, which still hold the published password (owner's yes in that turn; `OPERATIONS.md`, "Release step: the production demonstration accounts"). Record the image row in `OPERATIONS.md`. Mark the release story Done in Notion.

**Rollback:** set both production services back to the previous release's `sha-` tag and redeploy with `-f version=<that release>` (`OPERATIONS.md`, Rollback).

## Approvals

Every push, merge into `main`, tag and deploy needs the owner's yes at that moment (project `CLAUDE.md` and BRANCHING rule 7). An advance approval given for a chain of steps, such as "when it is stable, push it to main", holds only while every check passes. The first failure stops the chain and is reported.

## When the image scan or a scanner fails on a release tag

The `images` job builds each image, scans it with Trivy (HIGH and CRITICAL with a fix) and only then logs in to GHCR and pushes. A failure on `dev`, or on a candidate tag that had to build, therefore means **no image was pushed** (a release tag builds nothing, so it cannot fail a scan; it can only fail the guard or find no candidate image). Triage it on `dev`, like any problem found in a candidate:

1. Read the finding in the run log. If a package in the base image has a fix, bump the base image or add the upgrade step in the Dockerfile on a `fix/` branch from `dev`, merge it, and cut a new candidate (section 1).
2. If the finding cannot be fixed yet or does not apply, add it to `.trivyignore` on `dev`: the id, the reason it does not apply, who accepted it, and an expiry date (review within 30 days), then cut a new candidate. A bare id without a reason and a date is not accepted.
3. Release the new candidate under the next version number. **Never delete, move or re-push the failed tag, and never re-tag the same version** on a different commit: a version names exactly one commit, and the release guard and the `:vX.Y.Z` image depend on it. The failed tag stays as the record.

Re-running the failed job on the same tag run is not a re-tag: it is the right move when the cause was the scanner's own infrastructure. The Trivy database is fetched from the public ECR mirror with three attempts, and Semgrep is retried once; if both attempts fail the job fails rather than skipping the scan, so re-run it once the mirror or the Semgrep registry answers again. A scan that did not run never clears a release.

## Build once, promote by digest

Production runs the image the candidate was tested as (US-111, from v0.5.0). The version is not compiled in: the backend reads `APP_VERSION` from its environment at start (the file literal is the fallback), and the frontend's `entrypoint.sh` writes `appVersion` into `config.js` from the same variable (`window.__PERMITFLOW__.appVersion`, falling back to the version compiled in). Release notes are bundled in the image, which is why every candidate carries the release section and What's new hides sections newer than the running version.

| Event | CI job | What happens |
|---|---|---|
| Pull request, push to `dev` | `images` | build, Trivy scan, push (`:dev`, `sha-<commit>`; pull requests do not push); the registry digests are in the run summary and the `image-digests` artifact |
| Candidate tag `vX.Y.Z-rc.N` | `images` | the commit's `sha-<commit>` images exist (dev built and scanned them, and the development environment runs them): they are tagged `:vX.Y.Z-rc.N` by digest, nothing is built; digests in the summary and the `image-digests` artifact. If either is missing the job fails with a clear message and builds nothing: re-run it once the dev push run has finished |
| Push to `main` (the merge of the label commit) | `promote` | the release guard on the merge commit, then the last candidate's images are tagged `:main` and `sha-<merge>` with `docker buildx imagetools create`; each new tag is checked to have the candidate's digest |
| Tag `vX.Y.Z` | `promote` | the release guard on the tag, then `:vX.Y.Z` and `sha-<tagged commit>` on the same digest; digests in the `promoted-digests` artifact |

The candidate is the highest `vX.Y.Z-rc.N` tag. A push to `main` whose version is still a candidate fails the guard: `main` only receives releases.

What follows from it:

- **The release is the candidate.** The label commit differs from the candidate only in the version lines, `CHANGELOG.md` and documents; the guard proves it, and `RELEASE_NOTES.md` and every file under `backend/`, `frontend/` and `docker/` are identical.
- **`/health` in production reports the candidate's commit.** `commit` is the `GIT_SHA` baked into the image, so it is the tested candidate's commit, not the `main` merge commit; `version` is `APP_VERSION`, `X.Y.Z`. The Telegram bot, the metrics (`permitflow_build_info`) and the What's new build line show the same pair.
- **Two environment variables are part of a production release**, set by the deploy job: `APP_VERSION=X.Y.Z` on the production backend and on the production frontend. Without it production would report the candidate's version (`X.Y.Z-rc.N`) and the deploy job's last gate fails. A rollback sets it to the version being rolled back to.
- **The candidate image is the image dev ran.** The build is made once, by the push of the commit to `dev`, and scanned then; the candidate tag, the push to `main` and the release tag only add names to that digest. The digest in the `promoted-digests` artifact of a release is the digest of the candidate's `image-digests` artifact.
