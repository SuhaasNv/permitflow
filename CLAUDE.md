# PermitFlow: Project Instructions for Claude Code

PermitFlow is a 3-day software engineering assessment (Regulatory & Licensing platform). These instructions are standing obligations for every session on this repository. They complement the user-level standards in `~/.claude/CLAUDE.md` (build before commit, no `any`, no unrequested refactors, ask before `git push`).

## 0. You are the whole team: carry every hat, every story

There is one developer on this project, so Claude is responsible for all of the following on every story, not only the code. Nothing below is optional and nothing waits for the user to remember it:

| Hat | Standing responsibility |
|-----|-------------------------|
| Product owner / PM | Notion board is the live truth: story `In progress` when started, `Done` when its DoD is met, slipped stories moved with a note; sprint close ritual run at the end of each day (`docs/05-planning/SPRINTS.md`); `SCOPE.md` updated the moment scope changes |
| Solution architect | `docs/03-architecture/*` (ARCHITECTURE, DOMAIN_MODEL, STATE_MACHINE, ADRs) and the diagrams (`diagrams/views/*.png`: solution architecture, branching, deployment, CI/CD) match the code; when an endpoint, entity, transition or flow changes, update the doc and regenerate the affected view in the same change |
| Developer | Modular monolith rules (§6), typed code, conventional commits, no secrets |
| QA engineer | Tests per layer for every story; the critical journey stays green; `docs/08-testing/TEST_STRATEGY.md` and `docs/10-uat/UAT_PLAN.md` kept current; UAT executed before calling anything shipped |
| Security engineer | Threat model controls implemented as designed; authorization test for every endpoint; `THREAT_MODEL.md` amended when a control changes |
| DevOps | `.env.example`, Docker Compose, CI workflow, Railway deployment, `docs/09-operations/OPERATIONS.md`; the observability layer (`docker/observability/`, `docs/13-observability/OBSERVABILITY.md`): a new metric, rule, dashboard row or Telegram command is documented there in the same change, and the dashboard and alerting files are regenerated from their generators, never edited by hand |
| Technical writer | `README.md`, `CHANGELOG.md`, `RELEASE_NOTES.md` (an entry per release, in the users' words, before the tag), `AI_USAGE.md`, `docs/README.md` index status ("written" / "to be written") kept truthful |
| Reviewer | Before declaring a sprint or the project done, re-read the brief's acceptance criteria and check `docs/11-reviews/ASSESSMENT_TRACEABILITY.md` |

If a session ends mid-story, leave a "Handover" line in `CHANGELOG.md` (what is half-done, what to run next) so the next session can continue without the user re-explaining.

## 1. Sources of truth (read before acting)

| Topic | File |
|-------|------|
| What we build and what we defer | `SCOPE.md` |
| Requirements (IDs FR/NFR/SEC/AI/AUD/UX/REL) | `docs/02-requirements/REQUIREMENTS.md` |
| Use cases (UC0-A … UC4-A, grouped like Notion epics) | `docs/02-requirements/USE_CASES.md` |
| Stories (US-xxx, 1:1 with Notion) | `docs/05-planning/USER_STORIES.md` |
| Sprints, sprint DoD, close ritual | `docs/05-planning/SPRINTS.md` |
| Story DoD | `docs/05-planning/DEFINITION_OF_DONE.md` |
| Domain model, state machine, architecture, ADRs | `docs/03-architecture/` |
| Threat model | `docs/06-security/THREAT_MODEL.md` |
| Observability: metrics, dashboard, alerts, Telegram, the monitoring services on Railway | `docs/13-observability/OBSERVABILITY.md` |
| UI design: screens, design system, states, components, frontend architecture | `docs/04-design/` (prototype: link in `docs/04-design/README.md`) |

If code and docs disagree, fix one of them in the same change. Never leave a doc describing something the code does not do.

## 2. Personas and roles (never reduce to two)

Three roles: `operator` (business user), `officer` (licensing officer / reviewer), `admin` (read-only oversight and monitoring; beyond the brief by product decision). Every new endpoint declares which roles may call it; authorization is server-side; operators never receive internal status codes.

## 3. Notion board: update in the same turn as the work

Board: "PermitFlow, Xtremax Assessment". Stories data source `collection://0a2a5588-d1ee-4855-867d-0a2f1f5b0149`; Epics `collection://fb140dee-a3b2-42e4-88c7-aacdd6fbd221` (E0 `3de339c78c3381b38d49f0e866d61e14`, UC1 `3de339c78c3381eb9d9adb6d2242c7a8`, UC2 `3de339c78c33819dbcb6ed174f91b125`, UC3 `3de339c78c3381a1ae48c394afdc661b`, E4 `3de339c78c3381008f09f9c475489e62`).

- When starting a story: set its Notion `Status` to `In progress` (`notion-update-page`, `update_properties`).
- When a story meets its DoD: set `Status` to `Done`.
- When a story slips: move `Sprint Day` to the next sprint and add a `Notes` line "slipped from Sprint N: reason".
- When a story is added, renamed or renumbered in `USER_STORIES.md`: mirror it in Notion in the same turn (title format `US-xxx — As a …, I want …, so that …`).
- If the Notion MCP is unavailable, say so and record the pending updates in `CHANGELOG.md` under "Notion sync pending".

## 4. After every story (checklist: run it, do not skip)

1. Tests for the story written and green (`pytest`, `vitest`, Playwright when it exists).
2. `docs/05-planning/USER_STORIES.md` unchanged or updated; Notion status moved.
3. Any new env var → `.env.example`, `README.md`, `docs/09-operations/OPERATIONS.md`.
4. Any schema change → Alembic migration + `docs/03-architecture/DOMAIN_MODEL.md`.
5. Any new endpoint → `docs/03-architecture/ARCHITECTURE.md` API table + authorization test.
6. Any architectural change → new or amended ADR in `docs/03-architecture/decisions/`.
7. Any scope change → `SCOPE.md` (MUST/SHOULD/COULD/DEFERRED) the moment it is decided.
8. AI prompt or provider change → `docs/07-ai/` and later `AI_USAGE.md`.
9. `CHANGELOG.md` entry for meaningful milestones (not every commit).
10. Work on a `feat/us-<id>-<slug>` branch from `dev` and merge it into `dev` with `--no-ff` (`docs/09-operations/BRANCHING.md`); `main` only receives releases. Commit with a conventional message (`feat:`, `fix:`, `test:`, `docs:`, `chore:`): short subject (≤ 50 chars), conclusive, body only when the "why" is not obvious. Never mention Claude, AI tools or add attribution trailers. Never `git push` without telling the user first and getting a yes in that turn.

Then prompt the user with a one-line status: what is Done, what is next, and anything they must decide.

## 5. Sprint close (end of each day, or when the user says the sprint is over)

Run the ritual in `docs/05-planning/SPRINTS.md`: tests green → Notion statuses final → `CHANGELOG.md` "## Sprint N: <date>" with Shipped / Slipped / Retro → re-check `SCOPE.md` → commit `docs: close sprint N`. Never mark a story Done that fails its DoD. Remind the user if the day is ending and the close has not run.

## 6. Engineering rules specific to this project

- Modular monolith: `api → services → domain / repositories → models`; `domain/` is pure Python (no SQLAlchemy, no FastAPI, no I/O).
- All status changes go through `domain/workflow.py`; AI never mutates application state, feedback or status.
- Revisions are immutable snapshots; audit events are append-only and written in the same transaction as the change.
- AI provider: OpenAI (direct API key, `OPENAI_API_KEY`, model via `OPENAI_MODEL`) behind `VerificationProvider`; `MockProvider` when no key or in tests. Load the `claude-api` skill only if the user changes provider to Anthropic.
- Uploads: allowlist (pdf, png, jpg, jpeg, txt), 10 MB, magic-byte check, server-generated keys, served only through an authorized endpoint.
- Error body everywhere: `{ "error": { "code", "message", "details"? } }`.
- No secrets in the repo; `.env.example` documents every variable.

## 6a. UI rules from the design phase (apply to every frontend story)

- Build screens from `docs/04-design/SCREEN_INVENTORY.md`; tokens and type scale from `docs/04-design/DESIGN_SYSTEM.md`; states from `docs/04-design/UI_STATES.md`. When a screen or component changes, update those files and the prototype in the same story.
- No em dashes anywhere in UI copy or docs written from now on (use a colon, comma or middle dot). No emoji, gradients, KPI card grids or decorative icons. Red is for the brand mark, one primary action per screen and "needs you" signals only.
- Every status uses a label plus a dot or icon, never colour alone; operator screens receive operator labels only.
- Navigation: collapsible side rail (hamburger), bottom tab bar on phones; layouts verified at 390, 1024 and 1280.
- Uploads: PDF recommended; allowlist + magic bytes + 10 MB; `sha256` duplicate detection surfaced as "no change".

## 7. Communication

Keep the user informed without being asked: after each story, at midday (mid-sprint check: what is at risk), and before the sprint close. If something must be cut, propose the cut from the "Cut order" in `SPRINTS.md` and ask.

## 8. End-of-project deliverables (Day 3)

`README.md` (setup, env vars, tests, AI verification, security, CI/CD, deployment, scope, AI Usage, What I would do next), `SCOPE.md`, `AI_USAGE.md`, `CHANGELOG.md`, `docs/08-testing/TEST_STRATEGY.md`, `docs/07-ai/AI_EVALUATION.md`, `docs/09-operations/OPERATIONS.md`, `docs/10-uat/UAT_PLAN.md`, `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md`, `docs/11-reviews/ASSESSMENT_TRACEABILITY.md`, `docs/11-reviews/FINAL_REVIEW.md`. Every one must describe what actually exists.
