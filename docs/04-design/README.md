# PermitFlow: Design documentation

Status: written (UI/UX design phase, 17 to 18 Sep 2026, after solutioning and before implementation) and updated at the Sprint 1 close with an as-built record. These documents explain how the engineering design in `docs/03-architecture/` and `docs/02-requirements/` becomes a usable interface. They do not restate requirements; they reference requirement and use-case IDs.

**Prototype (clickable, browser):** https://claude.ai/artifact/LzFbAsy985c3EvA14yXbyj (static export of the same 23 artboards, one per page: `prototype/permitflow-prototype-v3-23-artboards.pdf`, stored with Git LFS): 23 artboards on one canvas (design system, operator journey, operator resubmission, officer journey, admin concept, two phone screens). Links between artboards follow the real workflow: sign in as a persona → create → form → documents → review → submit → officer queue → review → request resubmission → operator responds → officer reviews Revision 2 → compare → audit. Every screen uses fictional Singapore data (Kopi & Kaya Toast House Pte. Ltd., PF-2026-000214, Jalan Besar).

**Prototype v0.4.0 (20 Sep 2026, US-078):** https://claude.ai/artifact/VmZ2biUWNkGMTAFoa6D8LY: ten artboards for the eight v0.4.0 screens (the officer's checklist at 820 portrait and 1024 landscape, the clarification rail, the operator's respond screen at 390 and 1280 with the send dialog, the operator's history, the four admin screens), generated from `docs/04-design/prototype-src/v0-4-0/build.py` with the as-built tokens, so a change is made in the generator and republished, never drawn by hand. The states matrix for these screens is in `UI_STATES.md`; the flows in `UI_FLOW.md`; the components in `COMPONENT_INVENTORY.md` (v0.4.0 section).

**As built (Sprint 1 close, 18 Sep 2026):** https://claude.ai/artifact/MzKLsdXJ5USLi6Xidob941: every shipped screen captured from the running product at 1440 and 390, reverse-engineered into colour, type, components, motion and the deliberate departures from prototype v3 (typography, single surfaces, dashboard split, application header, stepper, motion, red usage, landing width). The PNG captures are in `screens/as-built/`. Officer screens (queue, case review, feedback, compare) are captured at the Sprint 2 close.

| Document | Purpose |
|----------|---------|
| `UI_DESIGN.md` | Design direction, visual personality, what we deliberately avoid, motion principles |
| `DESIGN_SYSTEM.md` | Tokens (colour, type, spacing, radius, elevation), status and verification vocabularies as rendered |
| `USER_JOURNEY.md` | The journey as built after Sprint 2: every step, screen, system action and status for both personas |
| `UI_FLOW.md` | Operator and officer flows screen by screen, with state-machine and feedback-lifecycle mapping |
| `SCREEN_INVENTORY.md` | Every screen: ID, persona, purpose, use case, requirements, actions, states, responsive notes, priority |
| `COMPONENT_INVENTORY.md` | Reusable components, their variants and where they are used |
| `UI_STATES.md` | Loading / empty / error / permission / not-found / success / partial states per screen, plus the upload → verification lifecycle |
| `FRONTEND_ARCHITECTURE.md` | The frontend as built (rewritten 20 Sep from the tree): folders, data flow, polling, forms, errors, known gaps |
| `UI_REQUIREMENTS_TRACEABILITY.md` | Requirement and use-case IDs → screens and components |

Assumptions made during design are listed at the end of `UI_DESIGN.md`. None changes product behaviour defined in `SCOPE.md`, `STATE_MACHINE.md` or `DOMAIN_MODEL.md`.
