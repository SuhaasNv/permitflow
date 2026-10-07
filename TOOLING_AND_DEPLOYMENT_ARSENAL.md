# Tooling and deployment arsenal

What is installed on this machine for Claude Code (skills, agents, connected services), which of it protects a PermitFlow deployment, and where the engineering documents live. Written 5 October 2026 against the `main` checkout (v0.3.0 plus later documentation and observability merges).

This file is a working note for the owner. It describes tools and documents; it does not change how the product is released. The release rules stay in `CLAUDE.md`, `docs/09-operations/OPERATIONS.md` and `docs/09-operations/BRANCHING.md`.

## 0. How I work: the daily toolkit

The tools I reach for on every project, and what each one is for. The longer reference lists are in sections 2 to 5.

### The rulebook

A checked-in `CLAUDE.md` in the repository, plus a global `~/.claude/CLAUDE.md`, tells the AI how this project works: three roles, the layering, every status change through the workflow table, the AI never changes application state, and a checklist to run after every story. It also says never to push, merge, tag or deploy without my yes in that turn. Every session starts from these files, so the rules do not depend on what I remember to say.

### The six I use most

| Tool | What I use it for | Where it shows up |
|------|-------------------|-------------------|
| **Review agents in parallel** (read-only: design critique, edge-case reviews, bug hunts, a five-agent recheck of the v0.4.0 diff with three Opus and two Sonnet) | A second pair of eyes with a separate brief. A reviewer reports and never edits; every finding is reproduced before a fix, and the fix goes through the normal story flow with a test | `AI_USAGE.md`; `docs/11-reviews/` |
| **`wcag-audit`** | Accessibility against WCAG 2.2 AA: source scan, axe-core in a browser at three widths, keyboard, reflow and target-size checks. Written from this project's accessibility work | US-095 and US-096 in `CHANGELOG.md` |
| **Cloudflare `security-audit` skill** (open source, installed at user level at `~/.claude/skills/security-audit`) | A source-first security audit: reconnaissance agents, hunter waves over a coverage ledger, independent verifiers and schema-validated findings. Run on 24 Sep with the standard profile and 15 agents, source only. It found no critical, high or medium issue; the two low findings and one hardening note were fixed with a test each | "Security audit fixes" in `CHANGELOG.md`; threat model T28, T29; `AI_USAGE.md` |
| **`anti-slop-design-auditor`** | Finds the tells of a generated site and proposes fixes; nothing changes until I approve, because design changes are my decision | "Anti-slop design audit fixes" in `CHANGELOG.md` |
| **Claude in Chrome** | User acceptance testing in a real browser: separate tabs emulating an iPad, flaky Wi-Fi, session take-over, every case in the UAT plan | `docs/10-uat/UAT_PLAN.md` |
| **Railway MCP, `gh` and Notion MCP** | Deployment checks, CI runs and pull requests, and the story board kept in step with the work | `docs/09-operations/OPERATIONS.md`; the Notion board |

For UI design direction I use the taste skill (`design-taste-frontend`, an anti-slop frontend skill for landing pages and redesigns): it reads the brief, infers a direction and runs a pre-flight check before any UI is built, and `anti-slop-design-auditor` checks the result afterwards.

For video I use the `hyperframes` skills with `brag` and `demo-video` (the debrief videos, `AI_USAGE.md` appendix). For releases, `staged-release` holds the same rule the pipeline follows: a fresh approval for every outward step.

### Memory and continuity

Rules are not the only thing that carries over between sessions. Each project has a small memory folder (`~/.claude/projects/<repo>/memory/`) with one note per lasting fact: how the Notion board stays in step, the three personas, the sprint cadence, UI taste (no em dashes, no generated look), the release state, "main is frozen during the assessment", and "never send an outward message without a yes on the exact text". If a session stops mid-story, a handover line in `CHANGELOG.md` says what is half done and what to run next. For long runs I give the frame once ("loop, use Sonnet reviewers, ping me") and approve outward steps from my phone through Remote Control.

### How the agents are organised

```
I decide: scope, stories, and every outward step
   -> Opus main session plans, writes the brief, merges, reports
      -> Sonnet builders (my standing rule for parallel work), one worktree each, own files, no push, no AI attribution
         -> Read-only reviewers in parallel (Opus and Sonnet), separate briefs
            -> Each finding reproduced, then fixed through the story flow with tests
               -> CI gates: seven jobs, the AI gate, the accessibility gate
                  -> My yes for each outward step: merge, tag, deploy
```

The main session plans and writes the briefs. Builders, when I split work, run in separate worktrees on separate files; on PermitFlow most of the code was written in the main session and the read-only reviewers were used throughout. Reviewers are read-only, run in parallel, and must reproduce a bug before reporting it. Nothing goes outward without my yes in that turn.

### Keeping the toolkit current

New skills go in when a task calls for one: the HyperFrames set came in with `npx hyperframes skills` for the videos, and the security-audit skill was added on 24 Sep to run over this repository. A skill gets written when a run teaches something reusable: `wcag-audit` came out of the PermitFlow accessibility work. My own agents live in `~/.claude/agents/`, one file each, written for audits I repeat: security, resilience, launch, legal, polish and design.

## 1. Standing rules for any deployment

These come from the owner's instructions and always apply, whatever tool is used.

| Rule | Source |
|------|--------|
| No `git push`, merge into `main`, tag, GitHub release or deploy without a clear yes from the owner in that turn. One yes covers one step only. | `~/.claude/CLAUDE.md`, Rule 0 |
| If any check fails partway through a release, stop and report. Do not move to the next outward step. | Rule 0 |
| `main` is frozen while the submission is being assessed: no pull request into `main`, no tag, no production deploy, no hotfix, until the owner lifts the freeze in so many words. Everything for v0.4.0 lands on `dev` and shows on the development environment only. | `CLAUDE.md` section 4a |
| A story branch merges into `dev` only when its whole Definition of Done is met. | `CLAUDE.md` section 4, item 10 |
| Production is pinned to a release image `sha-<commit>`; the production deploy job waits for the owner's approval in GitHub. | `docs/09-operations/OPERATIONS.md` |
| The main session plans and reviews; builders run as Sonnet subagents in worktrees. | Rule 0a |

## 2. Skills worth knowing (curated)

About 150 skills are installed. Only these matter for PermitFlow; the rest are grouped in one line at the end.

| Skill | What it does | Where it earned its place |
|-------|--------------|---------------------------|
| `wcag-audit` | WCAG 2.2 AA audit: source scan, axe-core in a real browser at three widths, scripted keyboard, reflow and target-size checks; fixes on request | US-095 and US-096 |
| `security-audit` (Cloudflare's open-source skill) / `security-audit-20` | The full source-first audit, or the fixed 20-point checklist with file and line proof | The 24 Sep audit; a quick go or no-go before a release |
| `staged-release` | Dev, release candidate, main, tag flow with a fresh owner approval for every outward step | Same rule as `OPERATIONS.md`; use for the v0.4.0 release |
| `railway:use-railway` | Railway projects, services, variables, deployments, logs, metrics | Pinning production to a `sha-` image, checking a rollout |
| `devops-engineer` / `sre-engineer` | CI/CD, images, SLOs, alerting, incident runbooks | Workflow changes; runbook per alert (readiness row 24) |
| `playwright-expert` | Playwright test design and debugging | The critical journey and the accessibility spec |
| `debugging-wizard` | Hypothesis-driven debugging from stack traces and logs | A red CI job or a failed health gate |
| `code-review` | Reviews a diff or pull request for correctness | Before the `dev` to `main` pull request |
| `fastapi-expert`, `react-expert`, `typescript-pro` | The backend and frontend stack | Writing and reviewing code in those layers |
| `stop-slop` | Removes machine-sounding writing | README, release notes, pitch scripts |
| taste skill (`design-taste-frontend`) | Chooses a design direction from the brief and runs a pre-flight check against templated, generated-looking UI | Before building a landing page or redesign; pairs with `anti-slop-design-auditor` |
| `hyperframes` family, `brag`, `demo-video`, `claude-video-generator` | Scripted, rendered video | The debrief videos (`AI_USAGE.md` appendix) |

Installed but not part of the story: the remaining video and motion skills, the `caveman` and `ponytail` response modes, Microsoft Learn lookups, Office file skills (`docx`, `pptx`, `pdf`, `xlsx`), plugin-authoring helpers, and the other `anthropic-skills:*` entries. `~/.claude/skills/learned` and `synced` hold no readable skill files.

## 3. Agents worth knowing (curated)

| Agent | Role | Use |
|-------|------|-----|
| `pre-deployment-checker` | Final gate before a commit or deploy (written for Next.js; other stacks marked N/A) | Before the `dev` to `main` pull request |
| `production-resilience-auditor` | Quotas, timeouts, duplicate protection, queries, a local load test, a restore check | The open readiness rows 14, 20 and 25 |
| `web-app-security-auditor` | PASS or FAIL per item with file and line proof; never attacks production | Security pass before a release |
| `anti-slop-design-auditor` | Finds the tells of a generated site; changes nothing until approved | After a visual change |
| `codebase-tidy-auditor` | Finds stray debug code and scratch files; proposes removal only | Before a commit |
| `plan-roaster` | Adversarial review of a plan | Stress-testing a release plan |
| `bug-fixer` | Finds real bugs and applies minimal fixes | Bug hunts |
| `Explore`, `Plan`, `general-purpose` (built in) | Search, planning, multi-step work | Reviews and research in parallel |

Also in `~/.claude/agents/`, for other kinds of work: `website-launch-auditor`, `website-legal-compliance-auditor`, `website-polish-fixer`, `website-ux-features-builder`, `ai-writing-pattern-editor`. Plugin agents (`caveman:cavecrew-*`) and `claude-code-guide` are installed and rarely used here.

Reviewers stay read-only and must reproduce a finding before reporting it; builders run as `sonnet` in worktrees with a brief that states scope, files owned, test limits, ports, no push and no AI attribution (Rule 0a).

## 4. Plugins, mods and hooks

### Plugins

Installed through Claude Code's plugin system (`~/.claude/plugins/`). Marketplaces added by hand: `ponytail` (DietrichGebert/ponytail), `caveman` (juliusbrussee/caveman) and `nateherk` (nateherkai/scroll-craft); the rest come from the official and `filippo-skills` marketplaces.

| Plugin | What it gives me | State |
|--------|------------------|-------|
| `railway` (official) | Railway MCP tools and the `use-railway` skill | On |
| `playwright` (official) | Browser automation tools for tests and UAT | On |
| `microsoft-docs` (official) | Microsoft Learn search, code samples and page fetch | On |
| `pyright-lsp` (official) | Python type checking in the editor loop | On |
| `swift-lsp` (official) | Swift language server | On |
| `caveman` (`caveman` and `filippo-skills`) | Terse response mode and its helper skills and agents | On |
| `ponytail` (`filippo-skills`) | Smallest-working-solution mode for coding tasks | On |
| `mode-router` (`filippo-skills`) | Hook that picks one mode per request: ponytail for coding, caveman for everything else | On |
| `nateherk-design` (scroll-craft) | Scroll-driven landing page skill | On |
| `ui-ux-pro-max` (`filippo-skills`) | UI and UX guidance across stacks | Installed for projects |
| `ecc` | The ECC skill and agent collection (includes a video `taste` skill) | Installed for projects |
| `oh-my-claudecode` | Extra agent and workflow tooling | Installed for projects |
| `frontend-design`, `coderabbit`, `claude-md-management`, `claude-mem`, `azure`, `ponytail` (original marketplace) | Frontend design, code review, `CLAUDE.md` upkeep, session memory, Azure tooling | Installed, switched off |

### Mods

Small plugins of function hooks that draw in the Claude Code interface and hot-reload (`~/.claude/mods/`, written with the `plugin-authoring` skill, each with its own tests).

| Mod | What it does |
|-----|--------------|
| `goal-meter` | A gradient progress bar above the prompt for the current goal, fed by the `progress` tool of the `goal-meter` MCP server |
| `agent-race` | A live scoreboard above the prompt when two or more subagents run at once |

### Hooks and rules

| File | What it does |
|------|--------------|
| `~/.claude/hooks/block-ai-attribution.sh` (PreToolUse, Bash) | Blocks a `git commit` or `gh pr create` whose message credits Claude or AI tooling, so no attribution reaches the history |
| `~/.claude/hooks/next-build-before-commit.sh` (PreToolUse, Bash) | Runs the Next.js build before a commit in a Next.js project |
| `~/.claude/rules/nextjs-frontend.md` | Front-end rules that load only when working on `.tsx` and `.jsx` files or `next.config.*` |
| `~/.claude/CLAUDE.md` and the repository `CLAUDE.md` | The standing rulebook (section 0) |

Settings worth knowing: the main session runs `opus` at extra-high effort; builders run as `sonnet`.

## 5. Connected services (MCP and CLI)

| Service | Tools | Use in deployment |
|---------|-------|-------------------|
| Railway MCP and `railway` CLI | `list-deployments`, `get-deployment-diagnosis`, `get-logs`, `get-status`, `list-variables`, `set-variables`, `http-error-rate`, `http-response-time`, `get-service-metrics`, `redeploy`, `restart-service`, `list-domains`, `domain-status` and others | Check a rollout, read logs, confirm variables per environment, diagnose a failed deploy. Reads are routine; `redeploy`, `set-variables` and `accept-deploy` need the owner's yes. |
| GitHub CLI (`gh`) | Pull requests, workflow runs, `gh workflow run deploy.yml`, repository secrets | Watch CI, open the `dev` to `main` pull request, dispatch the deploy job (always after a yes) |
| Notion MCP | `notion-update-page`, `notion-search`, `notion-fetch` | Move story status, keep the board 1:1 with `USER_STORIES.md` |
| Claude in Chrome and Playwright MCP | Navigate, click, screenshot, read console and network | Persona run-throughs, UAT on the deployed development environment, dashboard steps |
| Figma MCP | Design context and file access | The prototype and design handoff |
| Microsoft Learn MCP, PRA MCP, goal-meter | Documentation search, property data, progress tracking | Not used for PermitFlow deployment |
| Google Drive connector | Needs authorisation before use | Unavailable until authorised in the claude.ai connector settings |

## 6. The deployment pipeline these tools protect

From `docs/09-operations/OPERATIONS.md` and the four workflows in `.github/workflows/` (`ci.yml`, `ai-gate.yml`, `ai-eval.yml`, `deploy.yml`).

1. A push to `dev` or `main` runs `ci.yml`: backend, frontend, end-to-end with the accessibility gate, secret scan (gitleaks), dependency and code audit (pip-audit, bandit, npm audit), the six-stage AI gate, then the images job.
2. Green builds push both images to GHCR, tagged `sha-<commit>` and by branch. A `v*` tag writes the release tag and refuses a tag that does not match `frontend/package.json`.
3. `deploy.yml` redeploys the matching Railway environment and waits for a new deployment id to report SUCCESS. Health gates: `/api/v1/health` and `/healthz` must answer 200, and `config.js` must name that environment's API. The old containers keep serving until the new ones are healthy.
4. Development deploys automatically on a merge to `dev`. Production is pinned to a release `sha-` image and deployed by hand behind the owner's approval.
5. Rollback is by layer: set the two production services back to the previous `sha-` tag and run the deploy job. Migrations are forward only; the compatibility rule (add nullable, drop one release later) keeps an older image safe against a newer schema.

### Pre-release checklist, with the tool for each step

| Step | Check | Tool |
|------|-------|------|
| 1 | Every story's Definition of Done met; Notion statuses final | Notion MCP, `docs/05-planning/DEFINITION_OF_DONE.md` |
| 2 | Backend `uv run pytest`, `ruff`, `mypy`; frontend `npm test`, `lint`, `typecheck`, `build`; `npm run e2e` | Commands in `README.md`, `playwright-expert` |
| 3 | Seven CI jobs green on `dev` | `gh run list`, `schedule` or `loop` to poll |
| 4 | Security pass | `web-app-security-auditor`, `security-audit-20` |
| 5 | Accessibility gate and, for new screens, a WCAG audit | `wcag-audit` |
| 6 | Resilience items: quotas, load, backups | `production-resilience-auditor` |
| 7 | Stray files and debug code | `codebase-tidy-auditor` |
| 8 | Pre-deployment gate | `pre-deployment-checker` |
| 9 | Review of the diff between `dev` and `main` | `code-review` |
| 10 | UAT on the development environment, recorded | `docs/10-uat/UAT_PLAN.md`, Claude in Chrome |
| 11 | `RELEASE_NOTES.md` entry and `CHANGELOG.md` before the tag | `ai-writing-pattern-editor`, `stop-slop` |
| 12 | Owner lifts the `main` freeze and says yes to each outward step in turn: pull request, merge, tag, set the `sha-` pin, deploy job approval | `staged-release`, `gh`, Railway MCP |
| 13 | After the rollout: health gates, logs, error rate, the Telegram digest | Railway MCP (`get-logs`, `http-error-rate`), `docs/13-observability/OBSERVABILITY.md` |

## 7. Engineering docs

The full index is `docs/README.md`; each numbered folder under `docs/` has its own `README.md`. The ones I keep open while shipping:

| Document | Why |
|----------|-----|
| `SCOPE.md` | What is built, deferred and mocked, and the assumptions |
| `docs/03-architecture/` (`ARCHITECTURE.md`, `STATE_MACHINE.md`, the ADRs) | How it is built and why |
| `docs/09-operations/OPERATIONS.md` and `BRANCHING.md` | Environments, secrets, migrations, deploy and rollback |
| `docs/08-testing/TEST_STRATEGY.md` and `docs/10-uat/UAT_PLAN.md` | What each test layer protects, and the acceptance record |
| `docs/06-security/THREAT_MODEL.md` | Threats and controls |
| `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md` | The gap list with severities |
| `CHANGELOG.md` and `RELEASE_NOTES.md` | The engineering record and the users' words, per release |

## 8. Gaps worth closing before a real production release

From `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md`; the agent or skill that helps with each is in sections 2 and 3.

- A tested restore of the database and the uploads volume (row 14, High).
- A load and soak test against a staging copy (row 20).
- The rate limiter keyed on the real caller behind the Railway edge (row 25; built on `dev`, US-082).
- Migrations rehearsed on a staging clone of production data, not run on container start (row 13).
- A worker queue for the AI checks and object storage for files (rows 5 and 6).
- Identity through Singpass and Corppass, with MFA for officers and admins (row 2).
