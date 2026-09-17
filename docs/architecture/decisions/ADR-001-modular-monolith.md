# ADR-001: Modular monolith with an isolated AI module

## Context
PermitFlow needs an API, a web UI, a database, file storage and an AI verification step. We must decide how many deployable units to build and how to keep the code maintainable as features grow.

## Constraints
- 3 calendar days, one engineer.
- Must run locally from the README and deploy to a simple platform (Railway).
- Evaluated on production readiness and clarity, not on distributed-systems sophistication.
- AI verification is the one component with external latency and failure modes.

## Options Considered

### Option A: Modular monolith
One FastAPI process, one Postgres, modules by domain with enforced dependency direction; AI verifier behind an interface, run as an in-process background task.
- Pros: one deploy, one transaction boundary (atomic submissions), no inter-service contracts, fastest to build and to explain.
- Cons: AI work shares the process; scaling is vertical; discipline needed to keep boundaries.

### Option B: Microservices (applications, documents, verification, notifications)
- Pros: independent scaling; verification isolation.
- Cons: network failure modes, distributed transactions for "submission + audit + notification", service discovery, multiple deploys, far more infrastructure than three days allow. No user-visible benefit at MVP scale.

### Option C: Monolith plus a separate verification worker
- Pros: isolates the slow component; keeps one database.
- Cons: needs a queue/broker locally and in deployment; adds operational surface for a demo.

## Decision
Option A. The verification module is designed so that Option C is a later extraction: it has a single entry point (`run_verification(document_id)`), its own `verification_runs` table with status, and no dependency on request context.

## Rationale
The hard problems in this assessment are domain problems (revisions, diffs, feedback resolution, visibility rules, audit). A monolith lets every mutation happen in one transaction and lets a reviewer read the whole flow in one place. The only component that benefits from isolation is already isolated at the code level.

## Consequences

### Positive
- Atomic submissions and audit writes are trivial.
- One `docker compose up` for local, one Railway service plus Postgres for deployment.
- Debrief-friendly: a single request path can be traced end to end.

### Negative / Tradeoffs
- A burst of uploads runs verification in the API process. Mitigated with a 30 s timeout and small concurrency; documented as a production gap.
- Module boundaries are conventions plus a lightweight test, not process boundaries.

## Validation
- Dependency direction documented in `ARCHITECTURE.md`; a unit test asserts routers import services, not repositories, and that `verification` never imports `applications` services.
- Integration test covers submission atomicity (a forced failure after revision creation leaves no partial rows).
