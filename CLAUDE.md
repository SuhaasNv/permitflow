# PermitFlow — Project Instructions for Claude Code

PermitFlow is a 3-day software engineering assessment (Regulatory & Licensing platform). These instructions are standing obligations for every session on this repository. They complement the user-level standards in `~/.claude/CLAUDE.md` (build before commit, no `any`, no unrequested refactors, ask before `git push`).

## 1. Sources of truth (read before acting)

| Topic | File |
|-------|------|
| What we build and what we defer | `SCOPE.md` |
| Requirements (IDs FR/NFR/SEC/AI/AUD/UX/REL) | `docs/requirements/REQUIREMENTS.md` |
| Use cases (UC0-A … UC4-A, grouped like Notion epics) | `docs/requirements/USE_CASES.md` |
| Stories (US-xxx, 1:1 with Notion) | `docs/planning/USER_STORIES.md` |
| Sprints, sprint DoD, close ritual | `docs/planning/SPRINTS.md` |
| Story DoD | `docs/planning/DEFINITION_OF_DONE.md` |
| Domain model, state machine, architecture, ADRs | `docs/architecture/` |
| Threat model | `docs/security/THREAT_MODEL.md` |

If code and docs disagree, fix one of them in the same change. Never leave a doc describing something the code does not do.

## 2. Personas and roles (never reduce to two)

Three roles: `operator` (business user), `officer` (licensing officer / reviewer), `admin` (read-only oversight and monitoring; beyond the brief by product decision). Every new endpoint declares which roles may call it; authorization is server-side; operators never receive internal status codes.

## 3. Notion board — update in the same turn as the work

Board: "PermitFlow — Xtremax Assessment". Stories data source `collection://0a2a5588-d1ee-4855-867d-0a2f1f5b0149`; Epics `collection://fb140dee-a3b2-42e4-88c7-aacdd6fbd221` (E0 `3de339c78c3381b38d49f0e866d61e14`, UC1 `3de339c78c3381eb9d9adb6d2242c7a8`, UC2 `3de339c78c33819dbcb6ed174f91b125`, UC3 `3de339c78c3381a1ae48c394afdc661b`, E4 `3de339c78c3381008f09f9c475489e62`).

- When starting a story: set its Notion `Status` to `In progress` (`notion-update-page`, `update_properties`).
- When a story meets its DoD: set `Status` to `Done`.
- When a story slips: move `Sprint Day` to the next sprint and add a `Notes` line "slipped from Sprint N: reason".
- When a story is added, renamed or renumbered in `USER_STORIES.md`: mirror it in Notion in the same turn (title format `US-xxx — As a …, I want …, so that …`).
- If the Notion MCP is unavailable, say so and record the pending updates in `CHANGELOG.md` under "Notion sync pending".

## 4. After every story (checklist — run it, do not skip)

1. Tests for the story written and green (`pytest`, `vitest`, Playwright when it exists).
2. `docs/planning/USER_STORIES.md` unchanged or updated; Notion status moved.
3. Any new env var → `.env.example`, `README.md`, `docs/operations/OPERATIONS.md`.
4. Any schema change → Alembic migration + `docs/architecture/DOMAIN_MODEL.md`.
5. Any new endpoint → `docs/architecture/ARCHITECTURE.md` API table + authorization test.
6. Any architectural change → new or amended ADR in `docs/architecture/decisions/`.
7. Any scope change → `SCOPE.md` (MUST/SHOULD/COULD/DEFERRED) the moment it is decided.
8. AI prompt or provider change → `docs/ai/` and later `AI_USAGE.md`.
9. `CHANGELOG.md` entry for meaningful milestones (not every commit).
10. Commit with a conventional message (`feat:`, `fix:`, `test:`, `docs:`, `chore:`): short subject (≤ 50 chars), conclusive, body only when the "why" is not obvious. Never mention Claude, AI tools or add attribution trailers. Never `git push` without telling the user first and getting a yes in that turn.

Then prompt the user with a one-line status: what is Done, what is next, and anything they must decide.

## 5. Sprint close (end of each day, or when the user says the sprint is over)

Run the ritual in `docs/planning/SPRINTS.md`: tests green → Notion statuses final → `CHANGELOG.md` "## Sprint N — <date>" with Shipped / Slipped / Retro → re-check `SCOPE.md` → commit `docs: close sprint N`. Never mark a story Done that fails its DoD. Remind the user if the day is ending and the close has not run.

## 6. Engineering rules specific to this project

- Modular monolith: `api → services → domain / repositories → models`; `domain/` is pure Python (no SQLAlchemy, no FastAPI, no I/O).
- All status changes go through `domain/workflow.py`; AI never mutates application state, feedback or status.
- Revisions are immutable snapshots; audit events are append-only and written in the same transaction as the change.
- AI provider: OpenAI (direct API key, `OPENAI_API_KEY`, model via `OPENAI_MODEL`) behind `VerificationProvider`; `MockProvider` when no key or in tests. Load the `claude-api` skill only if the user changes provider to Anthropic.
- Uploads: allowlist (pdf, png, jpg, jpeg, txt), 10 MB, magic-byte check, server-generated keys, served only through an authorized endpoint.
- Error body everywhere: `{ "error": { "code", "message", "details"? } }`.
- No secrets in the repo; `.env.example` documents every variable.

## 7. Communication

Keep the user informed without being asked: after each story, at midday (mid-sprint check: what is at risk), and before the sprint close. If something must be cut, propose the cut from the "Cut order" in `SPRINTS.md` and ask.

## 8. End-of-project deliverables (Day 3)

`README.md` (setup, env vars, tests, AI verification, security, CI/CD, deployment, scope, AI Usage, What I would do next), `SCOPE.md`, `AI_USAGE.md`, `CHANGELOG.md`, `docs/testing/TEST_STRATEGY.md`, `docs/ai/AI_EVALUATION.md`, `docs/operations/OPERATIONS.md`, `docs/uat/UAT_PLAN.md`, `docs/reviews/PRODUCTION_READINESS_REVIEW.md`, `docs/reviews/ASSESSMENT_TRACEABILITY.md`, `docs/reviews/FINAL_REVIEW.md`. Every one must describe what actually exists.
