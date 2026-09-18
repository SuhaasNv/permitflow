# PermitFlow: Design documentation

Status: written (UI/UX design phase, 17 to 18 Sep 2026, after solutioning and before implementation) and updated at the Sprint 1 close with an as-built record. These documents explain how the engineering design in `docs/architecture/` and `docs/requirements/` becomes a usable interface. They do not restate requirements; they reference requirement and use-case IDs.

**Prototype (clickable, browser):** https://claude.ai/artifact/LzFbAsy985c3EvA14yXbyj: 23 artboards on one canvas (design system, operator journey, operator resubmission, officer journey, admin concept, two phone screens). Links between artboards follow the real workflow: sign in as a persona → create → form → documents → review → submit → officer queue → review → request resubmission → operator responds → officer reviews Revision 2 → compare → audit. Every screen uses fictional Singapore data (Kopi & Kaya Toast House Pte. Ltd., PF-2026-000214, Jalan Besar).

**As built (Sprint 1 close, 18 Sep 2026):** https://claude.ai/artifact/MzKLsdXJ5USLi6Xidob941: every shipped screen captured from the running product at 1440 and 390, reverse-engineered into colour, type, components, motion and the deliberate departures from prototype v3 (typography, single surfaces, dashboard split, application header, stepper, motion, red usage, landing width). The PNG captures are in `screens/as-built/`. Officer screens (queue, case review, feedback, compare) are captured at the Sprint 2 close.

| Document | Purpose |
|----------|---------|
| `UI_DESIGN.md` | Design direction, visual personality, what we deliberately avoid, motion principles |
| `DESIGN_SYSTEM.md` | Tokens (colour, type, spacing, radius, elevation), status and verification vocabularies as rendered |
| `UI_FLOW.md` | Operator and officer flows screen by screen, with state-machine and feedback-lifecycle mapping |
| `SCREEN_INVENTORY.md` | Every screen: ID, persona, purpose, use case, requirements, actions, states, responsive notes, priority |
| `COMPONENT_INVENTORY.md` | Reusable components, their variants and where they are used |
| `UI_STATES.md` | Loading / empty / error / permission / not-found / success / partial states per screen, plus the upload → verification lifecycle |
| `FRONTEND_ARCHITECTURE.md` | How the React/Vite/Tailwind/TanStack Query/RHF/Zod frontend is organised to implement this design |
| `UI_REQUIREMENTS_TRACEABILITY.md` | Requirement and use-case IDs → screens and components |

Assumptions made during design are listed at the end of `UI_DESIGN.md`. None changes product behaviour defined in `SCOPE.md`, `STATE_MACHINE.md` or `DOMAIN_MODEL.md`.
