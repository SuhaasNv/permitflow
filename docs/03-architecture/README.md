# 03 Architecture

The engineering design: written 17 Sep 2026 before the code (solutioning phase) and kept in step with it afterwards. When an endpoint, entity, transition or flow changes, the document changes in the same commit; the diagrams are regenerated when the view they show changes.

| Document | What it holds |
|----------|---------------|
| `SOLUTIONING.md` | The engineering problems considered before implementation: options, choice, rationale, trade-offs and how each was validated |
| `ARCHITECTURE.md` | The modular monolith: layers, modules, the API table with the roles allowed on each endpoint, request flows, boundaries; the solution-architecture diagram |
| `DOMAIN_MODEL.md` | Entities and their fields as named in code, the verification vocabulary and issue codes, invariants and ownership rules |
| `STATE_MACHINE.md` | The twelve statuses of the brief plus `draft` and `withdrawn`, the label per role, the transition table (source, target, actor, guard) and the feedback rules; the specification that `backend/app/domain/workflow.py` implements and `test_workflow.py` sweeps |
| `decisions/` | Architecture decision records ADR-001 to ADR-012, with an index that gives "chose X over Y because Z" per record |
| `diagrams/views/` | The four rendered views used in the technical deck: solution architecture (with the observability group since 20 Sep), branching, deployment (with the two monitoring services), CI/CD pipeline |

Reading order for a newcomer: `ARCHITECTURE.md` (ten minutes), then `STATE_MACHINE.md`, then the ADR index. `SOLUTIONING.md` is the long form of why; `DOMAIN_MODEL.md` is the reference while reading the models and repositories.

Related: security controls in `../06-security/`, the AI module in `../07-ai/`, the frontend structure in `../04-design/FRONTEND_ARCHITECTURE.md`, deployment in `../09-operations/`.
