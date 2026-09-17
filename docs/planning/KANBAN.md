# PermitFlow — Kanban (Scrumban)

One engineer, three days, AI-assisted. Lightweight flow inside three one-day sprints (`SPRINTS.md`): planning at the start of the day, a mid-day check, review and close at the end, recorded in `CHANGELOG.md`.

## Board

The authoritative board is in Notion: "PermitFlow — Xtremax Assessment" (Epics and Stories databases). This file mirrors the workflow rules and the story-to-day mapping so the repository is self-contained. Story details live in `USER_STORIES.md`.

Columns:

```
Backlog → Ready → In Progress → Code Review → QA → UAT → Done
```

| Column | Entry criteria | Exit criteria |
|--------|----------------|---------------|
| Backlog | Story written | Prioritised and sized |
| Ready | Acceptance criteria clear; dependencies done | Picked up |
| In Progress | Work started | Code complete, tests written, self-reviewed |
| Code Review | Diff reviewed against requirements and coding standards (AI-generated code reviewed line by line) | No open review comments; lint/typecheck green |
| QA | Automated tests pass locally and in CI | Manual check of loading/empty/error states; three viewports for UI stories |
| UAT | Scenario from `docs/uat/UAT_PLAN.md` executed | Expected result observed |
| Done | Definition of Done met (`DEFINITION_OF_DONE.md`) | — |

## WIP limits

| Column | Limit |
|--------|-------|
| In Progress | 2 |
| Code Review | 1 |
| QA | 2 |

If a limit is hit, finish before starting. The point is fewer half-done stories, not more parallelism.

## Policies

- Small batches: a story should be finishable in under half a day; split otherwise.
- The core journey (submit → review → feedback → resubmit → compare) must stay green; a story that breaks it is reverted, not patched forward.
- Tests are part of the story, not a later column.
- AI-generated code enters Code Review like any other code: read fully, compared to the requirement, and tested.
- Anything deferred is written down in `SCOPE.md` the moment the decision is made.

## Story-to-day mapping

| Day | Stories |
|-----|---------|
| Day 1 | US-000, US-001, US-002 (mock provider), US-006 (skeleton), US-010, US-011, US-012, US-014, US-015, US-030 |
| Day 2 | US-002 (OpenAI provider), US-003, US-013, US-016, US-017, US-018, US-019, US-020, US-021, US-022, US-023, US-024, US-025, US-026, US-027, US-028, US-029, US-031, US-032 |
| Day 3 | US-004, US-005 (E2E + gaps), US-006 (complete), US-007, US-008, US-070–073 (admin, only if core is stable), production readiness review, traceability, final review |

## Daily cadence

- Start: pick the day's stories in dependency order; move to Ready.
- During: update Notion status as stories move; record decisions in ADRs or `SCOPE.md`.
- End: run the full test suite, run the UAT scenarios that apply, update `CHANGELOG.md`, note what slipped and why.
