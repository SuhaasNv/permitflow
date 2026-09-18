# PermitFlow — Sprint Plan

Three calendar days, one engineer with AI assistance. We run **three one-day sprints**. A one-day sprint is the shortest cycle that still has a real goal, a review and a close; anything shorter turns into task-switching. The Notion `Sprint Day` field is the sprint (Day 1 = Sprint 1, and so on). Stories move `Not started → In progress → Done` on the Notion board as they are picked up and finished; a sprint is closed only when the close ritual below has run.

## Cadence

| Event | When | Duration | Output |
|-------|------|----------|--------|
| Sprint planning | Start of each day | 15 min | Sprint goal confirmed; stories pulled into Ready in dependency order; WIP limits respected (In Progress ≤ 2) |
| Mid-sprint check | Midday | 5 min | Anything at risk is cut or simplified now, not at 23:00; `SCOPE.md` updated if scope changes |
| Sprint review | End of day | 20 min | Demo the sprint goal end to end locally (Sprint 1–2) or on the deployed URL (Sprint 3); run the UAT scenarios that apply |
| Sprint close | Immediately after review | 10 min | Close ritual (below) executed; `CHANGELOG.md` entry written; Notion statuses final |
| Retro | Part of close | 5 min | One line each: what slowed us, what to change tomorrow — recorded in `CHANGELOG.md` |

## Definition of Done

Story level: `DEFINITION_OF_DONE.md` (acceptance criteria met, validation, authorization, tests, UI states, docs, Notion updated).

Sprint level — a sprint is Done when:
1. The sprint goal is demonstrable end to end.
2. Every story marked Done meets the story DoD; stories not meeting it are moved back to In progress or to the next sprint, never marked Done "mostly".
3. The full test suite is green locally and CI is green on the last commit.
4. The core journey (submit → review → feedback → resubmit → compare) still works — regression here blocks the close.
5. `CHANGELOG.md` has a dated entry listing what shipped, what slipped and why.
6. Notion board reflects reality: Done stories Done, slipped stories re-assigned to the next sprint with a note.

## Sprint close ritual (run every time)

```
1. pytest + vitest (+ playwright when it exists) — all green
2. git log since sprint start — every commit has a conventional message
3. Notion: set Status = Done for finished stories; move unfinished to next Sprint Day with a Notes line "slipped from Sprint N: <reason>"
4. CHANGELOG.md: "## Sprint N — <date>" with Shipped / Slipped / Retro
5. Re-read SCOPE.md: still true? Update MUST/SHOULD/DEFERRED if anything changed
6. Commit: "docs: close sprint N"
```

## Design phase — 17 September 2026 (before Sprint 1)

US-009: design direction, design system, clickable prototype (23 artboards), design docs in `docs/design/`, two critique passes. No code. Sprint dates below shifted by one day as a result.

## Sprint 1 — 18 September 2026 — "An operator can submit" — CLOSED

Closed 18 Sep 2026: goal met; US-002 OpenAI half moved to Sprint 2; retro in `CHANGELOG.md`.

**Goal:** an operator logs in, creates an application, fills the form, uploads documents that are verified by the mock provider, and submits; the state machine, role labels and authorization exist and are unit-tested; CI skeleton runs.

| Story | Title (short) | Priority |
|-------|---------------|----------|
| US-000 | Project skeleton, DB, migrations, health, CI skeleton | MVP |
| US-001 | Login per persona (operator, officer, admin) | MVP |
| US-030 | Role-specific status labels | MVP |
| US-010 | Create application | MVP |
| US-011 | Sectioned form with validation | MVP |
| US-012 | Drag-and-drop document upload | MVP |
| US-002 | AI verification pipeline (mock provider) | MVP |
| US-014 | Progress indicator | MVP |
| US-015 | Submit application | MVP |
| US-006 | CI pipeline (skeleton) | MVP |

**Exit criteria:** Sprint DoD + state machine tests cover every (state, target, role); operator-B-cannot-see-A test passes; `docker compose up` + README steps work on a clean clone.

**Cut order if behind:** progress indicator UI polish → CI skeleton (keep local checks) → nothing else; the rest is the foundation.

## Sprint 2 — 19 September 2026 — "The loop closes, twice" — CLOSED

Closed 19 Sep 2026: goal met; nothing slipped; US-033 and US-034 added and Done; retro in `CHANGELOG.md`.

**Goal:** the officer reviews, gives contextual feedback and requests resubmission; the operator sees feedback on top, edits only flagged targets and resubmits; the officer sees highlights, compares revisions, tracks resolution and advances to an outcome; the audit trail and notifications work; OpenAI provider is wired. Two full rounds work end to end.

| Story | Title (short) | Priority |
|-------|---------------|----------|
| US-020 | Review queue | MVP |
| US-021 | Full submission view + Start review | MVP |
| US-022 | AI results beside documents | MVP |
| US-023 | Contextual feedback | MVP |
| US-024 | Comment templates | MVP |
| US-025 | Status transitions + operator notification | MVP |
| US-016 | Resubmission view: status + feedback on top | MVP |
| US-017 | Feedback anchored to section/document | MVP |
| US-018 | Edit only flagged, resubmit | MVP |
| US-019 | Operator history | MVP |
| US-026 | Officer notified on resubmission | MVP |
| US-027 | Highlights + revision compare | MVP |
| US-028 | Feedback resolution tracking | MVP |
| US-029 | Audit trail | MVP |
| US-031 | Site visit and outcome transitions | MVP |
| US-032 | Operator sees only final outcome | MVP |
| US-013 | Live verification status polish | MVP |
| US-002 | OpenAI provider | MVP |
| US-003 | Injection heuristic + malformed output handling | MVP |
| US-033 | Operator edge cases from the review pass (session, unsaved input, submit races, locked chrome) | MVP (added 19 Sep) |
| US-034 | Backend edge cases from the review pass (limiter, upload cap, stale runs, audit, downloads) | MVP (added 19 Sep) |

**Exit criteria:** Sprint DoD + integration test for the whole loop (two rounds) + operator visibility test + audit sequence test.

**Cut order if behind:** follow `DELIVERY_PLAN.md` §Cut order — any-two-revision compare → static Zod schemas → queue filter / re-run / draft delete → notification bell → templates UI (endpoint stays). MUST stories (US-024 templates, US-031 outcome transitions) are never cut; their UI becomes plainer. The OpenAI provider may slip to Sprint 3 morning (mock stays default) without cutting anything.

## Sprint 3 — 20 September 2026 — "Ship it honestly"

**Goal:** deployed, tested, documented, reviewed. Admin epic only if the core is stable by midday.

| Story | Title (short) | Priority |
|-------|---------------|----------|
| US-005 | Tests: E2E journey + remaining unit/integration gaps | MVP |
| US-006 | CI complete (lint, typecheck, tests, E2E, gitleaks, Docker) | MVP |
| US-004 | AI evaluation set + runner | Nice-to-have |
| US-007 | Railway deployment + health | MVP |
| US-008 | Documentation: README, AI_USAGE, reviews, UAT, operations | MVP |
| US-035 | Side rail reaches the bottom while scrolling (hotfix) | MVP (added 19 Sep) |
| US-036 | Search in My applications and the review queue | Nice-to-have (added 19 Sep) |
| US-037 | Phone width fit on the officer case + scroll to top on navigation (hotfix) | MVP (added 19 Sep) |
| US-038 | Withdraw application (operator) | Nice-to-have (added 19 Sep) |
| US-039 | Feedback decisions: resolve only released items, 10 s undo, composer lock | MVP (added 19 Sep) |
| US-040 | Flagged-section markers in the form rail and stepper | MVP (added 19 Sep) |
| US-041 | Respond-to-feedback flow: walk flagged items, lead to Resubmit | MVP (added 19 Sep) |
| US-042 | Playwright scenario suite: one spec per workflow, audit asserted | MVP (added 19 Sep) |
| US-043 | Layout audit fixes (`docs/reviews/LAYOUT_AUDIT.md`) | MVP (added 19 Sep) |
| US-044 | Unhandled errors inside CORS; engine pool sizing | MVP (added 19 Sep) |
| US-045 | Delete draft | MVP (added 19 Sep) |
| US-046 | Password show/hide; leaner sign-in copy | Nice-to-have (added 19 Sep) |
| US-047 | Landing hero band and accent | Nice-to-have (added 19 Sep) |
| US-070–073 | Admin oversight dashboard | Nice-to-have (only after US-005/006/007 are Done) |

**Exit criteria:** Sprint DoD + UAT plan executed on the deployed URL + production readiness review + assessment traceability + final review written honestly.

**Protected time:** from 16:00 on Day 3 no new features; only fixes, docs and review.

**Cut order if behind:** admin epic → AI evaluation runner (keep the fixture set and document manually) → p95/AI-health metrics → Playwright reduced to one shortest journey → nothing else. Same list as `DELIVERY_PLAN.md` §Cut order.
