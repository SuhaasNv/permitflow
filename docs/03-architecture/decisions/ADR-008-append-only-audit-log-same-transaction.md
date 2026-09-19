# ADR-008: Append-only audit log written in the same transaction

## Context
"Complete audit trail of all feedback and resubmission rounds" and "no applications are lost due to status transitions" require that every meaningful change is recorded with actor and time, and that the record cannot drift from the data.

## Constraints
- Must be consistent with the change it describes (no audit row without the change, no change without its audit row).
- Must be readable by officers in order.
- Must not be editable through the API.

## Options Considered

### Option A: `audit_events` table, appended by the service layer inside the same SQLAlchemy session/transaction as the mutation
- Pros: business-meaningful event types (`revision.submitted`, `status.changed`, `feedback.created`, `feedback.resolved`, `document.uploaded`, `verification.completed`); actor known; atomic with the change.
- Cons: relies on services calling `audit.record`; a forgotten call is a gap.

### Option B: Database triggers on the mutated tables
- Pros: cannot be forgotten.
- Cons: triggers do not know the actor or the business event; produce row-level noise; harder to test and to port.

### Option C: Application logs only
- Pros: zero schema.
- Cons: not queryable per application; not durable with the data; not an audit trail.

## Decision
Option A, with a `payload` JSON column for event-specific data (from/to status, feedback id, revision number) and no update/delete methods on the repository.

## Rationale
The audit trail is a product feature (visible to officers), so it must carry product semantics. Same-transaction writes give consistency without triggers.

## Consequences

### Positive
- Officer "History" tab is a single ordered query.
- Tests can assert the exact event sequence of a journey, which doubles as a regression test for the whole flow.

### Negative / Tradeoffs
- Discipline required; mitigated by placing `audit.record` calls in services (the only layer that mutates) and by the sequence test.
- No cryptographic tamper evidence; documented as a production gap (hash chaining or WORM storage).

## Validation
- Integration test asserting the event sequence for submit → review → feedback → request resubmission → resubmit → resolve → approve.
- Static check: no `AuditEvent` update/delete usage in the codebase.
