# ADR-013: Use case 3, part 1: the site visit appointment beside the state machine

Date: 20 September 2026. Story: US-084 (FR-043). Status: accepted, built. Parts 2 and 3 (the checklist and the clarification rounds, US-060 to US-066) are decided in `docs/05-planning/RELEASE_PLAN_V0_4_0.md` section 4 and will be recorded here as they are built.

## Context

The brief gives the site visit two statuses, Site Visit Scheduled and Site Visit Done, and nothing in between: the date was arranged outside the product. The owner asked on 20 September 2026 for the appointment to be arranged inside the case, both sides agreeing a date, every round on record. The checklist that follows (US-060) needs a confirmed date to be the visit's record.

## Constraints

- The twelve assessment statuses and their labels are the brief's; no status may be added or renamed.
- All status changes go through `domain/workflow.py`; the appointment must not become a second workflow.
- Operators never receive officer-only wording, internal codes or the officer's name.
- Every change is audited and notified in the same transaction (ADR-008); a case must never get stuck (no unbounded loop, no dead end without an officer move).
- Singapore time everywhere (NFR-016); no public-holiday calendar exists in the product.

## Options Considered

### Option A: new statuses (Site Visit Proposed, Counter-Proposed)
Honest about the negotiation, but it changes the brief's status list and every label table, queue filter and dashboard bucket built on it.

### Option B: a free-text "visit date" field on the application
One field, no rounds: the operator cannot answer, nothing is recorded, and the officer still arranges the date by phone.

### Option C: an appointment record inside `site_visit_scheduled`, with its own small state
`SiteVisit` (`proposed`, `counter_proposed`, `confirmed`, `done`) and `SiteVisitProposal` rounds live beside the application the way feedback items live inside `under_review`. The application status does not move while the date is negotiated; the workflow gains one guard (`visit_confirmed` on `site_visit_scheduled` to `site_visit_done`) and one side effect (the visit becomes `done`).

## Decision

Option C. The officer's "Mark site visit scheduled" becomes the first proposal (date, slot, note): `POST /officer/applications/{id}/site-visit` runs the `under_review` to `site_visit_scheduled` transition and records the proposal in one transaction, under the application row lock and the version check. The operator accepts, or counters with a date and a required reason; the officer accepts the operator's date, keeps the date on the table, or proposes a third; either side may ask to move a confirmed visit before its date, reason required; the officer may confirm a proposal the operator has not answered after three working days (never later than the visit itself). The negotiation is capped at six proposals per visit, both sides together; at the cap only the closing moves remain (`MAX_ROUNDS` in `domain/site_visit.py`). The date on the table is always the visit row's own date; deciding a counter settles only an officer proposal still pending, so earlier rounds keep their recorded outcome after a reschedule. The operator view is built separately (`SiteVisitOperatorView`): role labels for the appointment state, "Licensing officer" instead of the officer's name in the rounds, the reply deadline and the earliest date they may pick.

## Rationale

- The brief's status list stays intact and every existing consumer of it (labels, queue, dashboards, tests) is untouched; the queue and the operator dashboard read the appointment state for "whose move it is" without a new status.
- A bounded loop with an officer-only closing move and a silence rule means a case can never wait on the operator forever and never ping-pong forever.
- Rounds as immutable rows with a single written outcome give the audit trail and both histories one source; the checklist takes the confirmed date and slot from the same row.

## Consequences

- Two tables (`site_visits`, `site_visit_proposals`, migration 0006), seven routes, four audit event types, two notification titles per side; `notifications.kind` values are reused (`status_changed` to the operator, `resubmitted` to officers) because the column is `VARCHAR(16)` and the title carries the meaning.
- A second visit (`visit_no` 2) is modelled but unreachable in v0.4.0: no transition returns a case to `site_visit_scheduled`. If a "return to visit" edge is ever added, `propose` already handles a `done` visit by opening the next number.
- Public holidays are not modelled (SCOPE assumption 22); an officer will not propose one, and the operator can counter.
- The transition endpoint still accepts `site_visit_scheduled` for API callers; the case then shows "Propose a visit date" in the rail until a proposal exists.
