# ADR-017: One build per commit; a release is the tested candidate's image under a new name

Date: 10 October 2026. Story: US-111 (wave 5 of v0.5.0). Status: accepted. Amends ADR-011 (its "the tested artefact is the deployed artefact" held for the source, not for the image). Related: ADR-009 (stack and pipeline), US-103 (Trivy in the images job, the release guard), US-094 and US-110 (What's new and release candidates), `docs/09-operations/RELEASING.md`.

## Context

Until v0.4.1 the release ritual produced a tested candidate on `dev` and then a different image: the push to `main` and the release tag each rebuilt both images from the `main` merge commit. The release guard (`scripts/release_guard.py`) proved the source of the release equalled the last candidate's apart from the version lines, so the claim "production runs what was tested" rested on a build being reproducible, not on identity. Two builds of one source can differ (base image updated between runs, a dependency resolved differently, a timestamp), and the vulnerability scan of the candidate said nothing about the release image.

The rebuild existed because the version was compiled in: `APP_VERSION` is a literal in `backend/app/core/version.py`, the frontend takes `__APP_VERSION__` from `package.json` at build time, and the What's new page bundles `RELEASE_NOTES.md` through Vite. A release image had to say `0.5.0`, a candidate image said `0.5.0-rc.3`, so the release had a different image.

## Constraints

- No change in how a release is reasoned about: a release candidate is tested as if it were the release, and the release is that candidate with the label removed (`RELEASING.md`).
- The release guard keeps working, and the five version files keep carrying the version (the label commit still changes them).
- Railway never builds; services pull from GHCR by tag. No new infrastructure.
- Production must report the release version, not the candidate's, and the build commit it reports must stay true.
- The frontend image already reads its API URL from the environment at start (`config.js`); the pattern is established.

## Options considered

### Option A: keep rebuilding from the merge commit
Simple, and the guard makes it safe in practice. The identity of the tested and the deployed image stays unproven, the scan and the end-to-end evidence are about a different image, and every release pays for a second build.

### Option B: rebuild from the candidate tag with the version as a build argument
One source, one command, but still two images. It removes the version-line commit from the picture without removing the second build.

### Option C: build once, read the version at run time, promote by digest (chosen)
Make the version a run-time input and give the tested image its release names without building anything.

## Decision

Option C.

**Version at run time.** The backend reads the `APP_VERSION` environment variable at start and falls back to the literal in `version.py`; the literal line stays, so the guard and the five version files are untouched in form. The frontend's `entrypoint.sh` writes `appVersion` from the same variable into `config.js` when it is set, and the app reads `window.__PERMITFLOW__.appVersion`, falling back to the compiled-in version, through one function (`features/releases/version.ts`). `BUILD_COMMIT` stays the `GIT_SHA` baked in at build: it names the commit the image was built from.

**One build per commit.** The images job builds, scans with Trivy and pushes on every push to `dev` (`:dev`, `sha-<commit>`). A candidate tag `vX.Y.Z-rc.N` is placed on a commit CI has already built: the tag run looks for that commit's `sha-<commit>` images and, when both exist, tags them `:vX.Y.Z-rc.N` with `docker buildx imagetools create` by digest, then verifies the digest. Only if an image is missing (the tag came before the dev run finished) does it build and scan as before. The push to `main` and the release tag `vX.Y.Z` run a `promote` job instead of the images job: the release guard (on the merge commit, before the tag exists, via `--rev`), then the last candidate's images get `:main`, `:vX.Y.Z` and `sha-<commit>` by digest. Every name is checked against the candidate's digest, and the digests are written to the run summary and an artifact. The deploy job, run by hand for production, sets `APP_VERSION=X.Y.Z` on both services and fails unless `/health` and `config.js` report it.

**Release notes.** The notes are bundled in the image, so a promoted candidate cannot gain a section after it is built. Every candidate therefore writes or updates the upcoming `## vX.Y.Z, D Month YYYY: title` section next to its own, and What's new hides every section newer than the running version, with candidates ordered before their release (`0.5.0-rc.10 < 0.5.0`). A candidate on dev never shows the release section; production running `X.Y.Z` does, and still hides candidates. `RELEASE_NOTES.md` joins the files the release guard treats as shipped, and the guard fails a release whose last candidate has no release section, so the label commit changes only version lines, the changelog and documents.

## Rationale

- The strongest form of "tested artefact is deployed artefact" is the same digest. The evidence gathered on dev (browser run, the scan, the dev uptime) is about the image that production runs.
- The guard stays useful: it still proves the source of the label commit equals the candidate's, which is what keeps the promoted image honest about the commit it reports.
- The mechanism is the one the frontend already used for the API URL, and `imagetools create` copies a manifest without pulling layers.
- Reading the version in one place on each side keeps the compiled-in version as the fallback for local and dev runs.

## Consequences

- **`/health` in production reports the candidate's commit**, not the `main` merge commit, and `X.Y.Z` as the version. The commit shown is the tested one. RELEASING.md says so to whoever verifies a release.
- **`APP_VERSION` is part of a production release** and of a rollback (set to the version being rolled back to). Forgetting it shows `X.Y.Z-rc.N` in production and fails the deploy job's last gate.
- **`main` accepts only releases.** A push to `main` whose version files carry a candidate fails the guard in the `promote` job.
- **Tag after the dev run.** A candidate tagged before CI has pushed `sha-<commit>` builds its own image, which the development environment did not run. RELEASING.md tells the person cutting a candidate to tag after CI is green and the dev deploy has run.
- **Release notes of a candidate repeat the release section.** Each candidate cut edits the same section; the final candidate's text is the release's.
- **Scan coverage is unchanged but not repeated.** The candidate image was scanned when dev built it; promotion does not scan it again. A vulnerability published between the build and the release is caught by the next candidate, not by the release, since a release builds nothing.
- The first release to use the flow needs a candidate cut after this change is on `dev`: earlier candidates' images do not read `APP_VERSION`.
- The CI/CD and deployment diagrams in `docs/03-architecture/diagrams/views` predate this decision and still draw a build on `main`; they are regenerated from their source, not edited by hand.

## Validation

- `backend/tests/unit/test_version.py`: the environment variable overrides the literal, the literal is the fallback (empty and blank values too), and the literal line still has exactly one match for the guard's pattern.
- Frontend vitest: `appVersion()` prefers `config.js` and falls back to the compiled-in version; `compareVersions` orders `0.5.0-rc.1 < rc.2 < rc.10 < 0.5.0 < 0.5.1`; a dev build running `0.5.0-rc.4` does not show the `0.5.0` section and production running `0.5.0` does.
- `scripts/test_release_guard.py`: `RELEASE_NOTES.md` is a shipped file, the release-section check, and the real `version.py` declares one version. The `--rev` mode was exercised against a scratch clone (a label commit passes; a notes change after the candidate fails; a candidate version is refused).
- `entrypoint.sh` was run with and without `APP_VERSION` against stub binaries: `appVersion` appears only when set.
- The workflow changes are linted with actionlint. The promotion path has not run in CI before the first release that uses it; its checks (digest equality of every new name, the guard before any tag is written, the deploy job's version gate) fail closed.

## Revisit when

- Images need attestations or an SBOM bound to a digest (then promotion should copy or re-attest them).
- A scan of the release at release time is wanted in addition to the build-time scan (then scan the digest in the `promote` job).
- Release notes outgrow being bundled (then serve them from the API and drop the repeated release section).
- A second production environment appears: the `APP_VERSION` variable becomes a per-environment matter in the deploy job.

## Links

Stories: US-111 (this), US-103 (scan and guard), US-094 and US-110 (What's new, candidates). Documents: `docs/09-operations/RELEASING.md` (the flow), `docs/09-operations/OPERATIONS.md` (Deployment, Rollback, the `APP_VERSION` variable), `docs/03-architecture/ARCHITECTURE.md` (`/health`, deployment), `scripts/release_guard.py`, `.github/workflows/ci.yml` (`images`, `promote`), `.github/workflows/deploy.yml`.
