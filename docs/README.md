# PermitFlow — Documentation Index

Status legend: **written** (solutioning phase, before code) · **to be written** (produced during or after implementation). Documents written before code describe the intended design; the production readiness review on Day 3 re-checks each against the actual code.

## Product and requirements
| Document | Status | Purpose |
|----------|--------|---------|
| `../SCOPE.md` | written | What is built, deferred, mocked; assumptions; stack summary |
| `discovery/PROBLEM.md` | written | Problem, personas, pain points, success criteria |
| `requirements/REQUIREMENTS.md` | written | FR / NFR / SEC / AI / AUD / UX / REL requirements with IDs |
| `requirements/USE_CASES.md` | written | Use cases UC0-A … UC4-A grouped by Notion epic |

## Architecture
| Document | Status | Purpose |
|----------|--------|---------|
| `architecture/SOLUTIONING.md` | written | Options and choices for every significant engineering problem |
| `architecture/ARCHITECTURE.md` | written | Layers, modules, API surface, request flows, boundaries |
| `architecture/DOMAIN_MODEL.md` | written | Entities, verification vocabulary, issue codes, invariants |
| `architecture/STATE_MACHINE.md` | written | 12 states + draft, labels, transitions, guards, feedback rules |
| `architecture/decisions/ADR-001 … ADR-009` | written | Architecture decision records |
| `architecture/permitflow-architecture.drawio` / `.png` | written | Overall architecture diagram |
| `architecture/diagrams/uc1-use-case`, `uc2-use-case`, `e4-admin-use-case` (`.drawio` / `.png`) | written | UML use case diagrams per epic |
| `architecture/diagrams/sequences/*.mmd` / `.png` | written | Sequence diagrams UC1-A, UC1-B, UC2-A, UC2-B (Mermaid) |

## Security
| Document | Status | Purpose |
|----------|--------|---------|
| `security/THREAT_MODEL.md` | written | Threats T1–T19, planned controls, validation, production gaps |

## AI
| Document | Status | Purpose |
|----------|--------|---------|
| `ai/AI_VERIFICATION_DESIGN.md` | written | Pipeline, prompt contract, output schema, rules, failure handling |
| `ai/AI_EVALUATION.md` | to be written (Day 3) | Evaluation set and results against mock and OpenAI |
| `../AI_USAGE.md` | to be written (Day 3) | How AI tools were used to build PermitFlow |

## Planning
| Document | Status | Purpose |
|----------|--------|---------|
| `planning/USER_STORIES.md` | written | Stories US-000 … US-073, 1:1 with Notion |
| `planning/SPRINTS.md` | written | Three one-day sprints, sprint DoD, close ritual, cut order |
| `planning/KANBAN.md` | written | Flow, WIP limits, story-to-day mapping |
| `planning/DELIVERY_PLAN.md` | written | Day-by-day plan, cut order, risks |
| `planning/DEFINITION_OF_DONE.md` | written | Story-level DoD |

## Quality, operations, reviews (produced during implementation)
| Document | Status | Purpose |
|----------|--------|---------|
| `testing/TEST_STRATEGY.md` | to be written (Day 3) | Layers, what each layer protects, how to run |
| `uat/UAT_PLAN.md` | to be written (Day 3) | Acceptance scenarios and results on the deployed URL |
| `operations/OPERATIONS.md` | to be written (Day 3) | Setup, env vars, health, deploy, failure modes, rollback |
| `reviews/PRODUCTION_READINESS_REVIEW.md` | to be written (Day 3) | Honest gap list with severity |
| `reviews/ASSESSMENT_TRACEABILITY.md` | to be written (Day 3) | Brief requirement → implementation → test → evidence |
| `reviews/FINAL_REVIEW.md` | to be written (Day 3) | What we built, tradeoffs, what AI got wrong |
| `../CHANGELOG.md` | to be written (from Sprint 1 close) | Milestones and sprint closes |
| `../README.md` | to be written (Day 3, skeleton from Day 1) | Setup and overview |

## Review history
- 17 Sep 2026 — Solutioning documents reviewed by a stringent solution-architect pass (six blocking findings: feedback withdraw deadlock, document target semantics, undefined verification vocabulary, background-task session lifetime, assessment brief in git history, incomplete concurrency design). All six were fixed in the documents before implementation; the significant findings (priority conflicts, SQLite fallback, admin cuttability, notification kinds, stuck-application exits, structured-output constraints, error shape, sub-resource IDOR, third-party data transfer, rate limiter definition, diff by hash, cut order) were also applied.
