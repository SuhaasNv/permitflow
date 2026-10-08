# Releasing PermitFlow

How a version moves from `dev` to production. Adopted on 8 Oct 2026 at the owner's request. It is first used for v0.4.1.

The idea comes from how phone operating systems ship: a release candidate is a build you test as if it were the release, and **the release is that tested candidate with the label removed**. A problem found in a candidate is fixed on `dev` and becomes a new candidate. It is never patched on `main`.

Branching rules stay in `BRANCHING.md`, and environments, deploys and rollback in `OPERATIONS.md`. This file is the order of the steps.

## Names

| Stage | Where | Version in the five version files | Git tag | Images |
|---|---|---|---|---|
| Work in progress | `dev`, story branches | the last release or candidate, unchanged | none | `:dev`, `sha-<commit>` |
| Release candidate | `dev` | `X.Y.Z-rc.N` (`backend/pyproject.toml` and `uv.lock`: `X.Y.ZrcN`) | `vX.Y.Z-rc.N` on the `dev` commit | `:vX.Y.Z-rc.N` |
| Release | `main` | `X.Y.Z` | `vX.Y.Z` on the `main` merge commit | `:vX.Y.Z`, production pinned to `sha-<merge>` |

The five version files are `frontend/package.json`, `frontend/package-lock.json`, `backend/pyproject.toml`, `backend/uv.lock` and `backend/app/core/version.py`. CI refuses a tag that differs from `frontend/package.json`.

## 1. Cut a release candidate

Do this when `dev` holds everything the version should contain and the full local run is green.

1. On a `chore/rc-X.Y.Z-rc.N` branch from `dev`, set the version to `X.Y.Z-rc.N` in the five files. Add a candidate section to `RELEASE_NOTES.md`: `## vX.Y.Z-rc.N, D Month YYYY: title`, with the usual audience blocks, describing what this candidate changed, in the users' words. It sits among the releases in date order, newest first. The development environment lists it on What's new with a Release candidate label; production hides every candidate section, so the notes of a released version never mention candidates.
2. Merge it into `dev` with `--no-ff`. Run the full local run (pytest, ruff, mypy, the AI gate, vitest, lint, typecheck, build, Playwright). Push `dev`, which needs the owner's yes.
3. Once CI is green on that commit, tag it: `git tag -a vX.Y.Z-rc.N -m "PermitFlow vX.Y.Z-rc.N"` and `git push origin vX.Y.Z-rc.N` (yes). The tag's CI run writes the `:vX.Y.Z-rc.N` images.
4. Wait for the development deploy. Check that `https://api.dev.permitflow.space/api/v1/health` reports `X.Y.Z-rc.N` and the tagged commit.

## 2. Test the candidate on dev

- Run the stories' acceptance checks in a browser on https://dev.permitflow.space as each role, at 390, 820 and 1280 px. Use scratch applications for anything destructive.
- Record the run in `docs/10-uat/UAT_PLAN.md`: date, candidate, what passed and what failed.
- **Any fix goes to `dev` through a story or fix branch**, then becomes the next candidate (`rc.N+1`, steps 1 to 2 again). Nothing is fixed on `main`.

A candidate is **stable** when the full local run is green, CI on its commit is green, the dev deploy reports it, and the browser run passed with no open finding of medium severity or above.

## 3. Release

1. On a `chore/release-vX.Y.Z` branch from the stable candidate's commit, change only:
   - the five version files: `X.Y.Z-rc.N` becomes `X.Y.Z`
   - `RELEASE_NOTES.md`: the release section `## vX.Y.Z, D Month YYYY: title`, gathering what the candidates changed (the release day and the title only in the heading, never a mention of candidates; the candidates stay listed on the development environment)
   - `CHANGELOG.md`: the release entry
   - the README and other documents, if they name the current production version

   **Nothing else.** Merge it into `dev`, push (yes), and wait for CI.
2. Open the pull request from `dev` into `main` (yes). Merge it when every check is green (yes).
3. Tag the merge commit `vX.Y.Z` and push the tag (yes). The tag's CI run writes `:vX.Y.Z`. **The release guard** (`scripts/release_guard.py`, run in CI on every `v*` tag) fails the release if:
   - the tag is not `vX.Y.Z`
   - the version files disagree with the tag
   - no `vX.Y.Z-rc.N` tag exists for the version
   - any shipped file (`backend/`, `frontend/` and `docker/`, apart from the version lines) differs between the last candidate tag and the release tag
4. Deploy production (yes). Stage both production services onto `sha-<merge>` in Railway, review the staged change, and commit it (`OPERATIONS.md`, Deployment).
5. Verify with checks only the new version passes:
   - `/health` reports `X.Y.Z` and the merge commit
   - metrics answer 401 without the token
   - the site and `/releases` answer with the new bundle
   - one request that uses something new in this version
6. Run the seed once if the version adds seeded accounts. For the version that carries US-103, also rotate production's `operator@`, `officer@` and `officer2@` demonstration accounts, which still hold the published password (owner's yes in that turn; `OPERATIONS.md`, "Release step: the production demonstration accounts"). Record the image row in `OPERATIONS.md`. Mark the release story Done in Notion.

**Rollback:** set both production services back to the previous release's `sha-` tag and redeploy (`OPERATIONS.md`, Rollback).

## Approvals

Every push, merge into `main`, tag and deploy needs the owner's yes at that moment (project `CLAUDE.md` and BRANCHING rule 7). An advance approval given for a chain of steps, such as "when it is stable, push it to main", holds only while every check passes. The first failure stops the chain and is reported.

## When the image scan or a scanner fails on a release tag

The `images` job builds each image, scans it with Trivy (HIGH and CRITICAL with a fix) and only then logs in to GHCR and pushes. A failure on a `vX.Y.Z` tag therefore means **no image was pushed**. Triage it on `dev`, like any problem found in a candidate:

1. Read the finding in the run log. If a package in the base image has a fix, bump the base image or add the upgrade step in the Dockerfile on a `fix/` branch from `dev`, merge it, and cut a new candidate (section 1).
2. If the finding cannot be fixed yet or does not apply, add it to `.trivyignore` on `dev`: the id, the reason it does not apply, who accepted it, and an expiry date (review within 30 days), then cut a new candidate. A bare id without a reason and a date is not accepted.
3. Release the new candidate under the next version number. **Never delete, move or re-push the failed tag, and never re-tag the same version** on a different commit: a version names exactly one commit, and the release guard and the `:vX.Y.Z` image depend on it. The failed tag stays as the record.

Re-running the failed job on the same tag run is not a re-tag: it is the right move when the cause was the scanner's own infrastructure. The Trivy database is fetched from the public ECR mirror with three attempts, and Semgrep is retried once; if both attempts fail the job fails rather than skipping the scan, so re-run it once the mirror or the Semgrep registry answers again. A scan that did not run never clears a release.

## Not yet: building once and promoting

Production still runs an image **rebuilt** from the `main` merge commit, not the exact image tested on dev. The source is the same, and the release guard proves it. The images differ because the version is compiled in (`backend/app/core/version.py`, the frontend bundle).

Planned for v0.5.0: read the version at runtime (the backend from the environment, the frontend from `config.js`, as the API URL already is). Production would then run the tested candidate's image digest, relabelled at deploy time, without a rebuild.
