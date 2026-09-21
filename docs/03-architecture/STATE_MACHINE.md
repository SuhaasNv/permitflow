# PermitFlow: Application State Machine

Implemented in `backend/app/domain/workflow.py` (ADR-003). The transition table below is the specification; `backend/tests/unit/test_workflow.py` iterates over every combination (588 cases, checked on 20 Sep 2026 against this table).

## States and role-specific labels

The twelve states from the assessment plus one pre-submission state (`draft`, an engineering assumption needed for "save and return"; never visible to officers) and one operator-initiated terminal state (`withdrawn`, US-038).

| Internal code | Assessment internal status | Officer label | Operator label |
|---------------|----------------------------|---------------|----------------|
| `draft` | none (assumption) | none (not listed for officers) | Draft |
| `application_received` | Application Received | Application Received | Submitted |
| `under_review` | Under Review | Under Review | Under Review |
| `pending_pre_site_resubmission` | Pending Pre-Site Resubmission | Pending Pre-Site Resubmission | Pending Pre-Site Resubmission |
| `pre_site_resubmitted` | Pre-Site Resubmitted | Pre-Site Resubmitted | Pre-Site Resubmitted |
| `site_visit_scheduled` | Site Visit Scheduled | Site Visit Scheduled | Pending Site Visit |
| `site_visit_done` | Site Visit Done | Site Visit Done | Pending Post-Site Clarification |
| `awaiting_post_site_clarification` | Awaiting Post-Site Clarification | Awaiting Post-Site Clarification | Pending Post-Site Clarification |
| `pending_post_site_resubmission` | Pending Post-Site Resubmission | Awaiting Post-Site Resubmission | Pending Post-Site Resubmission |
| `post_site_clarification_resubmitted` | Post-Site Clarification Resubmitted | Post-Site Clarification Resubmitted | Post-Site Resubmitted |
| `pending_approval` | Pending Approval | Route to Approval | Pending Approval |
| `approved` | Approved | Approved | Approved |
| `rejected` | Rejected | Rejected | Rejected |
| `withdrawn` | none (assumption, US-038) | Withdrawn | Withdrawn |

Labels are copied verbatim from the assessment table, including "Awaiting Post-Site Resubmission" as the officer label for `pending_post_site_resubmission`.

Visibility rule: the operator API never returns the internal code; it returns `status_label` computed for the operator role. The officer API returns both the internal code and the officer label. "Route to Approval" therefore never reaches an operator client (ADR-005).

## Transitions

Guards are evaluated by the service with a `TransitionContext` (`open_feedback_count`, `has_changes_to_flagged_targets`, `is_complete`, `has_note`, and since US-079 the use case 3 fields `checklist_started`, `checklist_complete`, `open_clarification_count`, `answered_clarification_count`, `all_open_items_answered`) so the machine itself stays pure. `WorkflowService.build_context` builds it once for a transition and for the case view's `actions[]`; the viewer's own actor decides which edges are listed (`actor_for_role`: none for an admin, so the list is empty). `open_feedback_count` counts items with resolution `open` only; `addressed` items do not block a site visit (the officer is expected to resolve them, and the UI warns, but the workflow does not force it).

| From | To | Allowed actor | Guard | Trigger in MVP |
|------|----|---------------|-------|----------------|
| `draft` | `application_received` | operator (owner) | `is_complete` (all required sections valid, all required documents present) | Operator clicks Submit |
| `application_received` | `under_review` | officer | none | Officer clicks Start review |
| `application_received` | `rejected` | officer | `has_note` (a note is required) | Officer clicks Reject (e.g. duplicate or ineligible submission) |
| `pre_site_resubmitted` | `under_review` | officer | none | Officer clicks Start review |
| `pre_site_resubmitted` | `rejected` | officer | `has_note` (a note is required) | Officer clicks Reject |
| `under_review` | `pending_pre_site_resubmission` | officer | `open_feedback_count ≥ 1` | Officer clicks Request resubmission |
| `under_review` | `site_visit_scheduled` | officer | `open_feedback_count = 0` | Officer clicks Mark site visit scheduled: the proposal dialog asks for the date and slot and `POST /officer/applications/{id}/site-visit` runs this transition and records the proposal in one transaction (US-084) |
| `under_review` | `rejected` | officer | `has_note` (a note is required) | Officer clicks Reject |
| `pending_pre_site_resubmission` | `rejected` | officer | `has_note` (a note is required) | Officer clicks Reject (abandoned or unsalvageable application; prevents stuck cases) |
| `pending_pre_site_resubmission` | `pre_site_resubmitted` | operator (owner) | `has_changes_to_flagged_targets` | Operator clicks Resubmit |
| `site_visit_scheduled` | `site_visit_done` | officer | `visit_confirmed` (the current SiteVisit is `confirmed`: the operator accepted, the officer decided a counter, or confirmed after three working days of silence; US-084) | Officer clicks Mark site visit done; the visit row becomes `done` in the same transaction |
| `site_visit_scheduled` | `rejected` | officer | `has_note` (a note is required) | Officer clicks Reject |
| `site_visit_done` | `rejected` | officer | `has_note` (a note is required) | Officer clicks Reject |
| `site_visit_done` | `awaiting_post_site_clarification` | system | `checklist_complete` (the current visit's checklist is submitted: every item assessed, every flagged or unsatisfactory item commented, checked by the submit) | The checklist submit service (US-063, built): from `site_visit_scheduled` the officer hop is recorded first; the flagged items' round-1 requests are released in the same transaction; the transitional route straight to approval was removed with this story |
| `awaiting_post_site_clarification` | `post_site_clarification_resubmitted` | operator (owner) | `all_open_items_answered` | Operator clicks Send responses (round 1, US-065) |
| `awaiting_post_site_clarification` | `pending_approval` | officer | no item `open` or `answered` | Officer clicks Route to approval (a checklist with nothing flagged, or everything withdrawn) |
| `awaiting_post_site_clarification` | `rejected` | officer | `has_note` | Officer clicks Reject (US-079) |
| `pending_post_site_resubmission` | `post_site_clarification_resubmitted` | operator (owner) | `all_open_items_answered` | Operator clicks Send responses (round 2 onwards) |
| `pending_post_site_resubmission` | `pending_approval` | officer | no item `open` or `answered` | Officer clicks Route to approval after withdrawing every question of a later round (found in the two-device UAT run, 21 Sep 2026: without this edge the case sat with Reject as its only move) |
| `pending_post_site_resubmission` | `rejected` | officer | `has_note` | Officer clicks Reject (US-079) |
| `post_site_clarification_resubmitted` | `pending_post_site_resubmission` | officer | `open_clarification_count ≥ 1` | Officer clicks Request another round (US-066) |
| `post_site_clarification_resubmitted` | `pending_approval` | officer | no item `open` or `answered` | Officer clicks Route to approval |
| `post_site_clarification_resubmitted` | `rejected` | officer | `has_note` | Officer clicks Reject (US-079) |
| `pending_approval` | `approved` | officer | none (note optional) | Officer clicks Approve; side effect: the licence certificate is issued in the same transaction (`licence.issued`, US-051) |
| `pending_approval` | `rejected` | officer | `has_note` (a note is required) | Officer clicks Reject |
| `pending_approval` | `under_review` | officer | none | Officer clicks Return to review (US-031 follow-up, 19 Sep 2026): something noticed at the decision step is handled with feedback or a resubmission instead of a rejection |
| any post-submission, non-terminal state | `withdrawn` | operator (owner) | none (reason optional) | Operator clicks Withdraw application (US-038); `POST /applications/{id}/withdraw` |

Everything not listed is invalid and returns HTTP 409 `invalid_transition` with `details.allowed` for the caller's role. Role mismatches on a listed transition also return 409 (`details.kind = "forbidden"`): the transition table encodes the actor, and the role-gated routers already answered 403 before a wrong role could reach it. The `admin` role has no transitions: it is read-only on applications.

**Reading of the three post-site states (US-079, 20 Sep 2026; SCOPE.md assumption 18).** The brief's officer label for `pending_post_site_resubmission` is "Awaiting Post-Site Resubmission": the officer waits for the operator. By the same grammar "Awaiting Post-Site Clarification" is the officer waiting for the operator's clarification, and the brief goes from "On checklist submission, case automatically moves to Pending Post-Site Clarification" straight to "Operator sees ONLY the items flagged". So the operator answers in `awaiting_post_site_clarification` (round 1) and in `pending_post_site_resubmission` (later rounds); the officer reviews the answers in `post_site_clarification_resubmitted`. Before US-079 the table carried both readings at once (an officer edge from `awaiting` to `pending_post_site_resubmission` and "Request another round" back to `awaiting`); those two edges are gone, the operator edge from `awaiting` is new, and Reject is allowed from all three states.

Terminal states: `approved`, `rejected`, `withdrawn`.

## Diagram

```
 draft ──submit──▶ application_received ──start review──▶ under_review
                                                              │  ▲
                        ┌──── request resubmission (≥1 open) ─┘  │ start review
                        ▼                                        │
       pending_pre_site_resubmission ──resubmit──▶ pre_site_resubmitted
                        ▲                                        
                        └──────────── (unlimited rounds) ─────────┘

 under_review ──schedule (0 open)──▶ site_visit_scheduled ──done──▶ site_visit_done
                                                                        │
                       ┌── (UC3, deferred) checklist submit ────────────┤
                       ▼                                                │ route to approval
   awaiting_post_site_clarification ◀─────┐                             ▼
          │ request         │ route to    │ another round         pending_approval
          │ resubmission    │ approval    │                              │
          ▼                 └─────────────┼──────────────────┐   ┌───────┴───────┐
   pending_post_site_resubmission         │                  │   ▼               ▼
          │ resubmit                      │                  └▶ approved      rejected
          ▼                               │                                     ▲
   post_site_clarification_resubmitted ───┘── route to approval ────────────────┘

   pending_approval ──return to review (officer)──▶ under_review

   reject (officer, note) is allowed from every non-terminal post-submission state:
   application_received, under_review, pending_pre_site_resubmission, pre_site_resubmitted,
   site_visit_scheduled, site_visit_done, pending_approval ──────────────────▶ rejected

   withdraw (operator, reason optional) is allowed from every non-terminal post-submission
   state, including the UC3 states ─────────────────────────────────────────▶ withdrawn
```

## Feedback lifecycle rules (prevent stuck applications)

- Officers may create or withdraw feedback only while the status is `under_review`. In `pending_pre_site_resubmission` the feedback set is frozen, so the operator's editable targets cannot change underneath them (this closes the deadlock where a withdrawn item would leave an edited section without an open item).
- Requesting resubmission releases the current round's feedback to the operator: every `open` item gets `released_to_operator_at` set. Operators see only released feedback, so items being drafted during `under_review` are not visible until the officer asks for the resubmission.
- An addressed item the officer judges not fixed can be reopened while Under Review (`feedback.reopened`): it becomes a draft again with the same text, leaves the operator's view until the next round is requested, and counts as open for Request resubmission (US-049).
- An officer may resolve only items that were released to the operator (an unsent draft can only be withdrawn), and may undo their own withdraw or resolve within 15 seconds on the server (the toast offers it for 10 seconds; the extra 5 seconds absorb a slow click) while the state still allows the original action; the undo is audited as `feedback.restored` (US-039).
- Feedback targets are section keys or document types (both stable across revisions); resolution moves `open → addressed` automatically on resubmission when the target's content changed (sections compared by value, documents by `sha256`), and `addressed → resolved` by officer action.
- An officer can reject an application from `pending_pre_site_resubmission`, `site_visit_scheduled` or `site_visit_done` so that an abandoned application always has an exit.

## Editability by state

| State | Operator may edit | Scope |
|-------|-------------------|-------|
| `draft` | yes | all sections and documents |
| `pending_pre_site_resubmission` | yes | only sections/document types with `open` feedback |
| `awaiting_post_site_clarification`, `pending_post_site_resubmission` | no sections or documents (`editability.py` returns empty sets); the operator answers the released clarification items through the clarification service (US-065) | the flagged checklist items only |
| all others | no | none |

## Side effects per transition (service layer)

| Transition | Side effects (same transaction) |
|------------|--------------------------------|
| `→ application_received` | create Revision 1; copy `draft_data`; snapshot current document ids; audit `revision.submitted`, `status.changed`; notify all officers (kind `submitted`) |
| `→ pre_site_resubmitted` | create Revision N+1; mark feedback whose target changed as `addressed` (audit `feedback.addressed`); audit `revision.submitted`, `status.changed`; notify all officers (kind `resubmitted`) |
| `→ pending_pre_site_resubmission` | set `released_to_operator_at` on every `open` feedback item (audit `feedback.released`); audit `status.changed`; notify operator |
| any officer or system transition | audit `status.changed` (`trigger` = `officer` or `system`, the acting user as actor); the operator is notified `status_changed` with the operator label for every target in `WorkflowService.NOTIFY_OPERATOR` (every officer or system target); the caller may pass the body when it carries facts the service does not know (the count of flagged items at checklist submit) |
| `→ site_visit_done` | mark the current SiteVisit `done` (`done_at`); the appointment stays readable on both sides (US-084) |
| `→ awaiting_post_site_clarification` (system, from the checklist submit) | checklist `submitted` with `submitted_by`, `submitted_at`; a released round-1 `ClarificationRequest` per flagged item and the item `open`; audit `checklist.submitted` then `status.changed` (`trigger = system`); one operator notification with the count (US-063) |
| `→ post_site_clarification_resubmitted` (operator, from Send responses) | every open item's answer gets `sent_at` and the item becomes `answered`; audit `clarification.answered` per item then `status.changed` (`trigger = operator`); every active officer notified "The operator answered the clarification request" (US-065) |
| `→ pending_post_site_resubmission` (officer, Request another round) | every unreleased question of the current checklist gets `released_at`; audit `clarification.released` per item then `status.changed`; the operator is notified with the count (US-066) |
| `→ approved` / `→ rejected` | store `decision_note` (the `status.changed` audit payload carries `has_note`); on approval, issue the licence and audit `licence.issued` (ADR-010) |

## Built (Sprint 2; the post-site edges amended in Sprint 4, US-079)

Every transition in the table is exercised by `backend/tests/unit/test_workflow.py`; the officer edges run through `services/workflow.py`, the operator edges through `services/submission.py` and `services/resubmission.py`. Side effects marked in the table above for `→ pending_pre_site_resubmission` (release) and `→ pre_site_resubmitted` (Revision N+1, addressed, notify officers) are implemented and covered by `tests/integration/test_feedback.py` and `test_resubmission.py`.

## Concurrency

Every mutating service locks the application row (`SELECT … FOR UPDATE`) for the duration of its transaction, then re-reads status and feedback before evaluating guards, so concurrent officer actions cannot both pass a guard. Officer status-changing requests additionally send `expected_version` (from the last read) and receive 409 `version_conflict` if the row moved, which protects against acting on a stale screen. Operator `submit`/`resubmit` do not send a version: the row lock plus the state machine (409 `invalid_transition` if the state moved) is sufficient (REL-007).
