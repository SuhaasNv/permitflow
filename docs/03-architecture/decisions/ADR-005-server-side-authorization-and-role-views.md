# ADR-005: Server-side authorization and role-specific response shaping

## Context
Two roles see the same application differently: operators see only their own applications, role-mapped status labels and never the internal approval stage; officers see everything including audit trails. Feedback and status changes are officer-only; submissions and resubmissions are operator-only.

## Constraints
- "Never expose the internal approval stage to Operators" is a data rule, so it must hold at the API, not only in the UI.
- Horizontal privilege escalation (operator A reading operator B's application) must be impossible by construction, not by remembering a check.

## Options Considered

### Option A: Server-side checks via FastAPI dependencies plus role-aware serializers
`require_role(...)` dependencies on routers; a single repository method `get_application_for(user, id)` that applies ownership for operators; separate response models `ApplicationOperatorView` and `ApplicationOfficerView` so internal fields cannot leak by accident.
- Pros: authorization is declarative and centralised; response shape is typed per role; tests can assert absence of fields.
- Cons: two response models to maintain.

### Option B: One response model, UI hides fields by role
- Pros: less code.
- Cons: any client can read the raw API; fails the assessment's explicit constraint.

### Option C: Row-level security in Postgres
- Pros: strong guarantee.
- Cons: session-per-user connection setup, harder to test, unusual for an MVP; still needs response shaping.

## Decision
Option A. Ownership failures return 404 (not 403) for operators to avoid confirming that an application id exists. Role failures on officer-only routes return 403.

## Rationale
The cheapest place to make a rule un-forgettable is the function everyone must call to load an application. Typed per-role response models turn "did we leak a field?" into a compile-time and test-time question.

## Consequences

### Positive
- Every endpoint's access rule is visible in its signature.
- The operator view model physically lacks `internal_status`, audit trail and officer-only notes.

### Negative / Tradeoffs
- Two view models mean two serializers to update when adding fields; a small cost.
- JWT in `sessionStorage` is readable by XSS; documented production gap (httpOnly cookie).

## Validation
- Tests: operator B → 404 on A's application (read, update, submit, documents); operator → 403 on feedback/status/audit/queue; operator response JSON never contains `internal_status`, `route_to_approval` or audit events.
- Label test per role against the assessment table.
