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

## Amendments (as built)
- 19 Sep 2026 (US-038): a fourteenth state `withdrawn`, terminal, reachable by the operator (owner) from every post-submission non-terminal state with an optional reason. First transition with `Actor.OPERATOR` outside submit and resubmit; officers are notified; the operator is the audit actor.
- 19 Sep 2026 (US-031 follow-up): `pending_approval → under_review` ("Return to review", officer) so an officer who notices something at the decision step can add feedback or request a resubmission instead of rejecting. No new state.
- The unit test now iterates 14 states × 14 targets × 3 actors (588 cases) plus guards; the label test covers the withdrawn row for both roles.

## Amendment, 20 Sep 2026 (US-079, v0.4.0)

The post-site part of the table is read the brief's way (SCOPE.md assumption 18): the operator answers in `awaiting_post_site_clarification` and `pending_post_site_resubmission`, the officer reviews in `post_site_clarification_resubmitted`. Two edges that encoded the other reading are removed (`awaiting → pending_post_site_resubmission` by the officer, `post_site_clarification_resubmitted → awaiting`), one operator edge is added (`awaiting → post_site_clarification_resubmitted`, guard: every open item answered), the routes to approval from the post-site states are guarded by "nothing open or answered", the system edge from `site_visit_done` is guarded by a complete checklist, and Reject is allowed from the three post-site states. The direct route `site_visit_done → pending_approval` survives Sprint 4 behind a `checklist_started = false` guard and goes with US-063, when the checklist is the visit record. `TransitionContext` grows five use case 3 fields; `WorkflowService` takes the actor from the caller (`actor_for_role`, `Actor.SYSTEM` for the checklist submit) instead of assuming an officer, and the case view lists edges for the viewer's own actor, so an admin gets none. The sweep still covers every (state, target, actor) combination (588 cases); the expected table is the edge list itself.

