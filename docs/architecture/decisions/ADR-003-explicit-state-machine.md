# ADR-003: Explicit application state machine owns all status transitions

## Context
The assessment specifies twelve internal statuses with role-specific labels and states that "no applications are lost due to status transitions or filtering errors" and "operators cannot see the internal approval stage at any point". Status changes are triggered by operators (submit, resubmit) and officers (start review, request resubmission, schedule site visit, mark site visit done, route to approval, approve, reject). The only system-triggered transition (checklist submitted → awaiting post-site clarification) belongs to the deferred UC3.

## Constraints
- Every transition must be authorised by role and, in some cases, guarded by data conditions (for example, open feedback).
- Labels must be derived from internal status per role, never stored per role.
- Must be exhaustively unit-testable.

## Options Considered

### Option A: Single transition table in a `workflow` module
`TRANSITIONS: dict[(from, to)] -> Transition(allowed_roles, guard)`; `label_for(status, role)`; services call `workflow.transition(app, to, actor, ctx)`.
- Pros: one place to read and test; guards are pure functions over a context object; label mapping lives beside the states.
- Cons: guards needing data require the caller to build the context.

### Option B: Inline checks in each endpoint/service
- Pros: no abstraction.
- Cons: rules scattered; easy to allow an invalid transition; impossible to test exhaustively; the debrief question "how do you know no invalid transition is possible?" has no good answer.

### Option C: Workflow library (e.g. `transitions`)
- Pros: features like callbacks and diagrams.
- Cons: another dependency and mental model for a flow that is mostly linear; role and guard semantics would still be custom.

## Decision
Option A.

## Rationale
The state table is the most scrutinised business rule in the brief. Making it a literal data structure means the tests can iterate over every (state, target, role) triple and the reviewer can compare the code to the assessment table line by line.

## Consequences

### Positive
- Invalid transitions return 409 with the list of allowed targets for the caller's role.
- Adding UC3 later means adding rows, not editing services.
- Label mapping is tested against the assessment table verbatim.

### Negative / Tradeoffs
- Guards that need database state (open feedback count) require the service to load that state before calling the machine. This is deliberate: the machine stays pure.

## Validation
- Parametrised tests: every allowed transition succeeds for its role; every other combination raises `InvalidTransition`.
- Label test asserts the twelve-row mapping for both roles.
- Integration test asserts an operator cannot trigger an officer-only transition via the API (403) and an officer cannot skip states (409).
