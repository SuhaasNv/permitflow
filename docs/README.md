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
| `architecture/STATE_MACHINE.md` | written | 12 states + draft + withdrawn, labels, transitions (incl. Return to review), guards, feedback rules |
| `architecture/decisions/ADR-001 … ADR-011` | written (ADR-003, 006, 007, 009 amended as built; ADR-010 licence certificate, ADR-011 delivery pipeline added 19 Sep) | Architecture decision records |
| `architecture/permitflow-architecture.drawio` / `.png` | written | Overall architecture diagram |
| `architecture/diagrams/uc1-use-case`, `uc2-use-case`, `e4-admin-use-case` (`.drawio` / `.png`) | written | UML use case diagrams per epic |
| `architecture/diagrams/sequences/*.mmd` / `.png` | written | Sequence diagrams UC1-A, UC1-B, UC2-A, UC2-B (Mermaid) |

## Design (UI/UX phase, 17–18 Sep 2026)
| Document | Status | Purpose |
|----------|--------|---------|
| `design/README.md` | written | Index + link to the clickable prototype (23 artboards) |
| `design/UI_DESIGN.md` | written | Direction, personality, what is avoided, motion, accessibility, assumptions |
| `design/DESIGN_SYSTEM.md` | written | Tokens, type scale, status / verification / feedback vocabularies as rendered |
| `design/UI_FLOW.md` | written | Information architecture; operator and officer flows mapped to states and endpoints |
| `design/USER_JOURNEY.md` | written (Sprint 2) | The journey as built, step by step for the operator and the officer, with what the system does at each step |
| `design/SCREEN_INVENTORY.md` | written | Every screen with ID, persona, requirements, actions, states, responsive notes, priority |
| `design/COMPONENT_INVENTORY.md` | written | Reusable components and where they are used |
| `design/UI_STATES.md` | written | Loading / empty / error / permission states; upload → verification and feedback lifecycles |
| `design/FRONTEND_ARCHITECTURE.md` | written | Folder layout, routing, query keys, forms, uploads, responsive breakpoints, motion, a11y |
| `design/UI_REQUIREMENTS_TRACEABILITY.md` | written | Use case / requirement / story → screen |
| `design/brand/` | written | Logo mark (SVG), monochrome mark, horizontal lockup, usage notes |
| `design/screens/` | written | Rendered PNG of every prototype artboard; `screens/as-built/` holds captures of the shipped screens at the Sprint 1 close |

## Security
| Document | Status | Purpose |
|----------|--------|---------|
| `security/THREAT_MODEL.md` | written | Threats T1–T20, planned controls, validation, production gaps |

## AI
| Document | Status | Purpose |
|----------|--------|---------|
| `ai/AI_VERIFICATION_DESIGN.md` | written | Pipeline, prompt contract, output schema, rules, failure handling |
| `ai/AI_EVALUATION.md` | written (19 Sep) | Evaluation set and results against mock and OpenAI |
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
| `testing/TEST_STRATEGY.md` | written (19 Sep) | Layers, what each layer protects, how to run |
| `uat/UAT_PLAN.md` | to be written (Day 3) | Acceptance scenarios and results on the deployed URL |
| `operations/OPERATIONS.md` | written (grows per story) | Setup, env vars, health, logs, migrations, deployment environments |
| `operations/BRANCHING.md` | written | Git branching strategy: main / dev / feat / fix / hotfix / release; two Railway environments |
| `reviews/EDGE_CASE_REVIEW.md` | written (Sprint 2) | Three devil's-advocate reviews: every finding, its fix or its plan |
| `reviews/BUG_HUNT_REVIEW.md` | written (19 Sep) | Three parallel bug hunts (backend, frontend, seams): 45 findings, what was fixed and what was kept; run-through findings R1 to R5 |
| `reviews/LAYOUT_AUDIT.md` | written (19 Sep) | Layout audit at 390, 820, 1024, 1280 and 1440; findings tracked as US-043 and US-044 |
| `reviews/PRODUCTION_READINESS_REVIEW.md` | to be written (Day 3) | Honest gap list with severity |
| `reviews/ASSESSMENT_TRACEABILITY.md` | to be written (Day 3) | Brief requirement → implementation → test → evidence |
| `reviews/FINAL_REVIEW.md` | to be written (Day 3) | What we built, tradeoffs, what AI got wrong |
| `../CHANGELOG.md` | written (Sprints 1 and 2 closed; Sprint 3 in progress) | Milestones, sprint closes with Shipped / Slipped / Retro |
| `../README.md` | written (grows per story) | Setup, demo accounts, security, AI verification, tests, layout, branching |

## Review history
- 18 Sep 2026 — UI/UX design phase: two independent design-critique passes on the prototype (pass 1 scored 6.6/10 with 11 rendering bugs and 15 fixes; all applied; pass 2 results recorded in `design/UI_DESIGN.md`). Scope changes from the phase: public landing page (M1, FR-031), admin user management (S7, FR-030, US-073, T19), upload validation and hash-based duplicate detection made explicit (M3, SEC-005).
- 17 Sep 2026 — Solutioning documents reviewed by a stringent solution-architect pass (six blocking findings: feedback withdraw deadlock, document target semantics, undefined verification vocabulary, background-task session lifetime, assessment brief in git history, incomplete concurrency design). All six were fixed in the documents before implementation; the significant findings (priority conflicts, SQLite fallback, admin cuttability, notification kinds, stuck-application exits, structured-output constraints, error shape, sub-resource IDOR, third-party data transfer, rate limiter definition, diff by hash, cut order) were also applied.
