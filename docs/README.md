# PermitFlow: Documentation Index

Each numbered folder has its own `README.md` (what the folder is for, when it was written, one line per document, where to start); this file is the index across them.

Status legend: **written** (solutioning phase, before code) · **to be written** (produced during or after implementation). Documents written before code describe the intended design; where the built system differs, the document was updated in the same change or the difference is recorded in the readiness review.

## Product and requirements
| Document | Status | Purpose |
|----------|--------|---------|
| `../SCOPE.md` | written | What is built, deferred, mocked; assumptions; stack summary |
| `01-discovery/PROBLEM.md` | written | Problem, personas, pain points, success criteria |
| `02-requirements/REQUIREMENTS.md` | written | FR / NFR / SEC / AI / AUD / UX / REL requirements with IDs |
| `02-requirements/USE_CASES.md` | written | Use cases UC0-A … UC4-A grouped by Notion epic |

## Architecture
| Document | Status | Purpose |
|----------|--------|---------|
| `03-architecture/SOLUTIONING.md` | written | Options and choices for every significant engineering problem |
| `03-architecture/ARCHITECTURE.md` | written | Layers, modules, API surface, request flows, boundaries |
| `03-architecture/DOMAIN_MODEL.md` | written | Entities, verification vocabulary, issue codes, invariants |
| `03-architecture/STATE_MACHINE.md` | written | 12 states + draft + withdrawn, labels, transitions (incl. Return to review), guards, feedback rules |
| `03-architecture/decisions/README.md` + `ADR-001` to `ADR-012` | written (index with "chose X over Y because Z" per ADR; 003, 006, 007, 009, 011 amended as built; 010, 011 and 012 added 19 Sep) | Architecture decision records |
| `03-architecture/diagrams/views/*.png` | written (19 Sep) | Solution architecture, branching, deployment and CI/CD views used in the technical deck; generated from prompts written against the code and rated before use (`AI_USAGE.md`, Debrief material) |

## Design (UI/UX phase, 17–18 Sep 2026)
| Document | Status | Purpose |
|----------|--------|---------|
| `04-design/README.md` | written | Index + link to the clickable prototype (23 artboards) |
| `04-design/UI_DESIGN.md` | written | Direction, personality, what is avoided, motion, accessibility, assumptions |
| `04-design/DESIGN_SYSTEM.md` | written | Tokens, type scale, status / verification / feedback vocabularies as rendered |
| `04-design/UI_FLOW.md` | written | Information architecture; operator and officer flows mapped to states and endpoints |
| `04-design/USER_JOURNEY.md` | written (Sprint 2) | The journey as built, step by step for the operator and the officer, with what the system does at each step |
| `04-design/SCREEN_INVENTORY.md` | written | Every screen with ID, persona, requirements, actions, states, responsive notes, priority |
| `04-design/COMPONENT_INVENTORY.md` | written | Reusable components and where they are used |
| `04-design/UI_STATES.md` | written | Loading / empty / error / permission states; upload → verification and feedback lifecycles |
| `04-design/FRONTEND_ARCHITECTURE.md` | rewritten as built (20 Sep) | Tree, data flow, query keys and polling, forms, errors, client security, accessibility, known gaps |
| `04-design/UI_REQUIREMENTS_TRACEABILITY.md` | written | Use case / requirement / story → screen |
| `04-design/brand/` | written | Logo mark (SVG), monochrome mark, horizontal lockup, usage notes |
| `04-design/prototype/permitflow-prototype-v3-23-artboards.pdf` | written (18 Sep) | Static export of the clickable prototype, one artboard per page (design system, operator journey, resubmission, officer journey, admin concept, phone screens); Git LFS |
| `04-design/screens/` | written | Rendered PNG of every prototype artboard; `screens/as-built/` holds captures of the shipped screens at the Sprint 1 close |

## Security
| Document | Status | Purpose |
|----------|--------|---------|
| `06-security/THREAT_MODEL.md` | written | Threats T1 to T22, planned controls, validation, production gaps |

## AI
| Document | Status | Purpose |
|----------|--------|---------|
| `07-ai/AI_VERIFICATION_DESIGN.md` | written | Pipeline, prompt contract, output schema, rules, failure handling |
| `07-ai/AI_EVALUATION.md` | written (19 Sep) | Evaluation set and results against mock and OpenAI |
| `07-ai/AI_ASSURANCE.md` | written (19 Sep) | One page: the four layers, the AI gate and the live evaluation, fairness, tools chosen and not |
| `../AI_USAGE.md` | written (19 Sep) | How AI tools were used: tools and models, the workflow they worked inside, the standing instructions, the prompts grouped by the decision they carry, verification, what was discarded |

## Planning
| Document | Status | Purpose |
|----------|--------|---------|
| `05-planning/USER_STORIES.md` | written | Stories US-000 to US-076 (US-059 the debrief material, US-074 the post-release review, US-075 the final check before submission, US-076 the fixes after the cold review), 1:1 with Notion |
| `05-planning/SPRINTS.md` | written | Three one-day sprints, sprint DoD, close ritual, cut order |
| `05-planning/KANBAN.md` | written | Flow, WIP limits, story-to-day mapping |
| `05-planning/notion/*.png` | written (19 Sep) | The Notion board after the release: the workspace page, the Epics table, the Stories table |
| `05-planning/DELIVERY_PLAN.md` | written | Day-by-day plan, cut order, risks |
| `05-planning/DEFINITION_OF_DONE.md` | written | Story-level DoD |

## Quality, operations, reviews (produced during implementation)
| Document | Status | Purpose |
|----------|--------|---------|
| `08-testing/TEST_STRATEGY.md` | written (19 Sep) | Layers, what each layer protects, how to run |
| `10-uat/UAT_PLAN.md` | written (19 Sep) | Twelve acceptance scenarios, environments and accounts, the record of every run (local, development, CI, production after v0.3.0) |
| `09-operations/OPERATIONS.md` | written (grows per story) | Setup, env vars, health, logs, migrations, deployment environments |
| `09-operations/BRANCHING.md` | written | Git branching strategy: main / dev / feat / fix / hotfix / release; two Railway environments |
| `11-reviews/EDGE_CASE_REVIEW.md` | written (Sprint 2) | Three devil's-advocate reviews: every finding, its fix or its plan |
| `11-reviews/BUG_HUNT_REVIEW.md` | written (19 Sep) | Three parallel bug hunts (backend, frontend, seams): 39 findings (36 fixed, 3 kept as decisions); browser run-through findings R1 to R12 |
| `11-reviews/LAYOUT_AUDIT.md` | written (19 Sep) | Layout audit at 390, 820, 1024, 1280 and 1440; findings tracked as US-043 and US-044 |
| `11-reviews/PRODUCTION_READINESS_REVIEW.md` | written (19 Sep) | Twenty-two gaps with severity, what is in place, what production would need; go/no-go |
| `11-reviews/ASSESSMENT_TRACEABILITY.md` | written (19 Sep) | The brief decoded; every deliverable and acceptance criterion → implementation → test → evidence |
| `11-reviews/FINAL_REVIEW.md` | written (19 Sep) | What was built, the decisions to defend, trade-offs, what the AI got wrong, what to show in the debrief |
| `11-reviews/ISSUES_AND_MITIGATIONS.md` | written (19 Sep) | Every issue found across the reviews and run-throughs, its risk, mitigation and evidence; what was kept as a decision |
| `06-security/SECURITY_REVIEW.md` | written (19 Sep) | The owner's hardening checklist and four abuse scenarios, before and after US-058, with tests and what production adds |
| `12-demo/documents/README.md` and `12-demo/documents/with_issues/NOTES.md` | written | The three document sets as PDFs (clean, with planted issues, second business), the form values they agree with, the planted values |
| `04-design/prototype-src/README.md` | written | How the clickable prototype was generated |
| `11-reviews/LEGAL_AND_ACCESSIBILITY_REVIEW.md` | written (19 Sep) | The owner's legal, privacy and accessibility checklist answered item by item with evidence; laws considered; risks flagged; contrast computation (US-057) |
| `../RELEASE_NOTES.md` | written (20 Sep) | What each version brings, in the users' words, newest first, with what comes next (v0.4.0: the admin panel and use case 3) |
| `../CHANGELOG.md` | written (Sprints 1 to 3 closed; v0.3.0 released 19 Sep) | Milestones, sprint closes with Shipped / Slipped / Retro |
| `../README.md` | written | What it is, stack and why, hosts, setup, demo accounts, security, tests, CI, deployment, AI verification, AI Usage, What I would do next |
| `01-discovery/README.md` to `12-demo/README.md` | written (20 Sep) | A README per folder: purpose, document index, reading order, related folders |
| `13-debrief/README.md` | written (19 Sep) | The pitch deck and the technical deck (pptx and handout PDF), the launch video, the narrated walkthrough and the technical video (videos in Git LFS) |

## Review history
- 18 Sep 2026: UI/UX design phase: two independent design-critique passes on the prototype (pass 1 scored 6.6/10 with 11 rendering bugs and 15 fixes; all applied; pass 2 results recorded in `04-design/UI_DESIGN.md`). Scope changes from the phase: public landing page (M1, FR-031), admin user management (S7, FR-030, US-073, T19), upload validation and hash-based duplicate detection made explicit (M3, SEC-005).
- 17 Sep 2026: Solutioning documents reviewed by a stringent solution-architect pass (six blocking findings: feedback withdraw deadlock, document target semantics, undefined verification vocabulary, background-task session lifetime, assessment brief in git history, incomplete concurrency design). All six were fixed in the documents before implementation; the significant findings (priority conflicts, SQLite fallback, admin cuttability, notification kinds, stuck-application exits, structured-output constraints, error shape, sub-resource IDOR, third-party data transfer, rate limiter definition, diff by hash, cut order) were also applied.
