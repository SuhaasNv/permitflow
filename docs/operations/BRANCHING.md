# PermitFlow: Git branching strategy

Two long-lived branches, short-lived work branches, merges only through the chain below. No direct commits to `main`.

```
main  ── production. Only receives merges from dev (release) or hotfix/*. Tagged on every release.
  └── dev  ── integration. Always buildable; CI must be green. Receives merges from feat/*, fix/*, chore/*, docs/*.
        ├── feat/us-010-create-application
        ├── fix/us-012-upload-magic-bytes
        ├── chore/ci-postgres-service
        └── docs/sprint-1-close
hotfix/<issue>  ── branched from main, merged into main AND dev.
```

## Branches

| Branch | From | Merges into | Lifetime | Naming |
|--------|------|-------------|----------|--------|
| `main` | — | — | permanent | |
| `dev` | `main` | `main` (release) | permanent | |
| `feat/*` | `dev` | `dev` | one story | `feat/us-<id>-<slug>` |
| `fix/*` | `dev` | `dev` | one bug found before release | `fix/<slug>` or `fix/us-<id>-<slug>` |
| `chore/*` | `dev` | `dev` | tooling, CI, deps | `chore/<slug>` |
| `docs/*` | `dev` | `dev` | documentation only | `docs/<slug>` |
| `hotfix/*` | `main` | `main` then `dev` | production bug | `hotfix/<slug>` |
| `release/*` | `dev` | `main` and back into `dev` | optional stabilisation before a release | `release/sprint-<n>` |

## Rules

1. One story per `feat/*` branch. The branch name carries the story ID so the commit history maps to Notion and `USER_STORIES.md`.
2. Merge into `dev` with `--no-ff` so each story is one visible merge commit; the branch is deleted after merge.
3. Commits are conventional: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`; subject 50 characters or fewer; body explains why when not obvious. No tool attribution.
4. `dev` must pass CI (lint, type check, tests, build, secret scan) before it is merged to `main`.
5. A release is a `--no-ff` merge of `dev` into `main`, tagged `v0.<sprint>.0` (Sprint 1 → `v0.1.0`). Deployment (Railway) builds from `main` only.
6. A hotfix branches from `main`, merges into `main` (tag `v0.x.y`), then into `dev` so the fix is not lost.
7. Nothing is pushed without the user's explicit confirmation in that turn (project rule). Pull requests are used when a remote is in play; until then the same flow runs locally.
8. History is never rewritten on `main` or `dev`. Work branches may be rebased on `dev` before merge.

## Day-to-day

```
git switch dev
git switch -c feat/us-010-create-application
# work, test, commit
git switch dev
git merge --no-ff feat/us-010-create-application -m "feat: create application (US-010)"
git branch -d feat/us-010-create-application
```

Sprint close: `docs/sprint-<n>-close` branch for `CHANGELOG.md` and doc updates, merged into `dev`; then `dev` → `main` with tag.

## Branch history on GitHub

Merged feature branches are kept on the remote (not deleted) so the development history is visible branch by branch: `feat/us-000-project-skeleton` through `feat/us-015-submit-application`, then `feat/frontend-redesign`, `feat/landing-polish` and `feat/dashboard-split` for the Sprint 1 design pass. Every one enters `dev` through a `--no-ff` merge, so the graph shows one side line per story. Locally, branches may be deleted after merge; the remote copy stays.
