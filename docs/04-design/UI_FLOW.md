# PermitFlow: UI flows

Screen IDs refer to `SCREEN_INVENTORY.md`. State codes refer to `docs/03-architecture/STATE_MACHINE.md`.

## Information architecture

```
/login (S-00)
Operator (/app)
  /dashboard (S-10) ── stat strip · my applications · recent activity
  /applications/new → /applications/:id/form (S-11)      draft only
  /applications/:id/documents (S-12)                     draft only
  /applications/:id/review (S-13)                        draft only
  /applications/:id/submitted (S-14)                     once, after submit
  /applications/:id (S-15)   status bar · feedback panel · sections · documents  (all post-submission states)
  /applications/:id/history (S-16)   revisions · released feedback · timeline · site visit (S-19, v0.4.0)
  /applications/:id/clarification (S-18, v0.4.0)   only the flagged items · responses · attachments · send
  notifications panel (S-17) from the bell
Officer (/officer)
  /queue (S-20)
  /applications/:id (S-21)   review workspace: submission · documents · feedback rail · actions
  /applications/:id (S-23)   same route, resubmission variant when revisions ≥ 2 (Changed markers)
  /applications/:id/compare?from&to (S-24)
  /applications/:id/history (S-25)   audit trail · revisions · status history
  /applications/:id/checklist (S-30, v0.4.0)   the inspection checklist, one per visit; read-only after submit
  /applications/:id (S-31, v0.4.0)   same route, the clarification rail replaces the feedback rail in the post-site states
  dialogs: request resubmission (S-22), reject (note), schedule site visit, approve; v0.4.0: submit checklist, still needs clarification, mark clarified, request another round
Admin (/admin, v0.4.0)
  /overview (S-40)   stat strip · applications by status · idle cases · check health · today
  /activity (S-42)   audit events across every application and every user change
  /users (S-41)      directory · change role · deactivate · reactivate
  /applications/:id (S-43)   the officer's case page, read-only
```

Navigation: top bar (brand, bell, user, sign out) + left side nav per role. Application screens use breadcrumbs (`My applications › PF-2026-000214 › Documents`) and tabs (`Application | History` for operators; `Submission | Documents | Feedback | History & audit` for officers).

## Operator flow: apply and submit (UC1-A)

| Step | Screen | State | What the user sees / does | Engineering hook |
|------|--------|-------|---------------------------|------------------|
| 1 | S-00 |: | Sign in; persona picker in the prototype only | `POST /auth/login`, role → home |
| 2 | S-10 |: | Stat strip answers "what do I need to do today"; table of own applications with operator labels | `GET /applications` |
| 3 | S-11 | draft | "New application" creates a draft and opens the form; section rail with completion marks; each section saves on its own; inline + summary errors; autosave note | `POST /applications`, `PATCH /applications/{id}/sections/{key}`, `GET /form-schema` |
| 4 | S-12 | draft | One slot per required document type; drop zone per empty slot; upload badge; verification block updates by polling; issues explained with "what to do"; invalid file errors inline | `POST /applications/{id}/documents`, `GET /applications/{id}` (poll 2 s while pending/running) |
| 5 | S-13 | draft | Read-only summary of every section and document; completion 100 %; warning if any document has unresolved check results; declarations; Submit | `completeness` from the server |
| 6 | S-14 | application_received | Confirmation with reference, "Submitted" badge, what happens next | `POST /applications/{id}/submit` (Revision 1) |

Steps 3–5 share a six-step stepper (Business, Premises, Operations, Declarations, Documents, Review & submit) under the status bar so the operator always knows where they are.

## Operator flow: respond to feedback and resubmit (UC1-B, UC1-C)

| Step | Screen | State | What the user sees / does | Engineering hook |
|------|--------|-------|---------------------------|------------------|
| 1 | S-17 / S-10 | pending_pre_site_resubmission | Notification "changes requested"; stat strip cell "1 needs your action" | `GET /notifications` |
| 2 | S-15 | pending_pre_site_resubmission | Status bar explains in one sentence; **feedback panel first**, numbered, each with target tag and "Go to" anchor; section rail shows flagged (amber flag) vs read-only (lock); only flagged sections/document slots are editable; flagged section repeats the officer comment inline; "Items addressed 1 of 3" progress | released feedback only; `editable_targets`; `PATCH` on non-flagged → 403 shown as "This section is not open for changes" |
| 3 | S-15 | pending_pre_site_resubmission | Replace a flagged document (previous file stays in Revision 1); the new file is re-checked | `POST /documents` (replace by type), sha256: identical file → "This is the same file as before: no change recorded" |
| 4 | S-15 | pre_site_resubmitted | Resubmit (enabled once ≥ 1 flagged target changed); toast; status bar updates | `POST /applications/{id}/resubmit`; 422 "no changes to flagged items" shown inline |
| 5 | S-16 | any | History: revisions (immutable), feedback with what changed, timeline; Compare Rev 2 with Rev 1 (read-only diff) | `GET /revisions`, `GET /compare` |

Repeats for unlimited rounds; each round adds a "Round n" group in the feedback panel.

## Officer flow: review, feedback, request resubmission (UC2-A)

| Step | Screen | State | What the officer sees / does | Engineering hook |
|------|--------|-------|-----------------------------|------------------|
| 1 | S-20 |: | Stat strip (awaiting review, under review, waiting on operator, route to approval, site visit); table with internal labels, revision count, feedback counts, last activity, one contextual action per row | `GET /officer/applications` |
| 2 | S-21 | application_received | "Start review" is the primary action; sections and documents are read-only; feedback rail is empty with guidance | `POST /transition {target: under_review}` |
| 3 | S-21 | under_review | Each section and document card has "Comment on section / Comment"; the composer pre-selects that target; template chips fill the message; items appear in the rail marked "not yet released"; Edit / Withdraw available | `POST /feedback`, `GET /feedback-templates`, withdraw |
| 4 | S-22 | under_review | "Request resubmission (n)" opens a dialog listing exactly what will reopen for the operator, optional note, reminder that feedback freezes | `POST /transition {target: pending_pre_site_resubmission, expected_version}` |
| 5 | S-20 | pending_pre_site_resubmission | Row shows "Waiting on operator" |: |

Header actions always show all allowed transitions for the current state; disallowed ones are visible but disabled with a tooltip reason ("Resolve or withdraw open feedback first"), so the state machine is legible. Reject is always available (danger style, note required).

## Officer flow: review the resubmission, compare, resolve (UC2-B, UC2-C, UC2-D)

| Step | Screen | State | What the officer sees / does | Engineering hook |
|------|--------|-------|-----------------------------|------------------|
| 1 | S-17 / S-20 | pre_site_resubmitted | Notification "resubmitted · 3 of 3 addressed"; queue row highlighted with "Review resubmission" | `GET /notifications` |
| 2 | S-23 | pre_site_resubmitted → under_review | "Review resubmission" performs Start review; screen shows only changes: "Changed" sections with old value struck through, "Replaced" documents with the previous file link, unchanged sections collapsed | `GET /officer/applications/{id}` (changed flags), `POST /transition {under_review}` |
| 3 | S-24 | under_review | Compare: field-by-field old/new table per section, documents row per type with Replaced mark, unchanged rows recede, toggle to hide unchanged | `GET /compare?from=1&to=2` |
| 4 | S-23 | under_review | Feedback rail: Addressed items with "Changed: 48 → 62" context and "Mark resolved"; resolved items green; toast confirms; warning if addressed items are unresolved before scheduling a site visit | `POST /feedback/{fid}/resolve` |
| 5 | S-21/S-23 | under_review → site_visit_scheduled → site_visit_done → pending_approval → approved/rejected | Header actions walk the remaining lifecycle; approve/reject dialogs capture the note the operator will see | `POST /transition` |
| 6 | S-25 | any | History & audit: every event with actor, time, type; revisions; status history | `GET /officer/applications/{id}/audit` |

## Feedback lifecycle as the user experiences it

```
Officer drafts item (under_review)  →  rail: "Open · not yet released"    (operator cannot see it)
Officer requests resubmission      →  operator: numbered item, "Open", Go to target
Operator changes the target        →  operator: progress "n of m addressed"; on resubmit item becomes "Addressed in Rev N"
Officer reviews Revision N         →  rail: "Addressed" + what changed + Mark resolved
Officer marks resolved             →  both roles: "Resolved" (green, message greyed)
```

## Notifications (S-17)

Kinds from the domain model only: `submitted` and `resubmitted` (to officers), `status_changed` (to the operator). Rendered as title (reference + event), one body line, timestamp; unread rows tinted; click opens the application. Verification outcomes are not notifications in the MVP (they are visible on the document card); the panel design leaves room for them if added later.

## Officer flow: site visit and clarification (UC3-A, UC3-C, v0.4.0)

| Step | Screen | State | What the user sees / does | Engineering hook |
|------|--------|-------|---------------------------|------------------|
| 1 | S-21 | site_visit_scheduled | Primary action "Open checklist"; the feedback rail is locked with the reason | `POST /officer/applications/{id}/checklist` (201 or 200) |
| 2 | S-30 | site_visit_scheduled / site_visit_done | Fills each item: result, comment, flag; section picker; progress with counts; autosave with Saved hh:mm, retrying and the offline banner | `PUT …/checklist` with `version` and `save_id` (idempotent; 409 merged) |
| 3 | S-30 | site_visit_done (hop recorded when needed) | Submit dialog lists the flagged items; findings freeze; the case moves on its own | `POST …/checklist/submit`; system transition; one operator notification |
| 4 | S-31 | awaiting_post_site_clarification | Rail header "Round 1, waiting on operator"; every flagged item Open with the finding on top; Withdraw available; Route to approval disabled with the reason | `actions[]` from the server |
| 5 | Bell, S-20 | post_site_clarification_resubmitted | "PF-…: The operator answered the clarification request"; row says Review responses | officer notification (active officers) |
| 6 | S-31 | post_site_clarification_resubmitted | Per item: Mark clarified or Still needs clarification (message required; item shows "Not sent yet"); Request another round (n) once an item is open; Route to approval once nothing is open or answered | item endpoints; the two transitions with their guards |
| 7 | S-21 | pending_approval | Preview licence, Approve or Reject, Return to review (a second visit gets its own checklist) | as today |

## Operator flow: answer the flagged items (UC3-B, v0.4.0)

| Step | Screen | State | What the user sees / does | Engineering hook |
|------|--------|-------|---------------------------|------------------|
| 1 | Bell, S-10 | awaiting_post_site_clarification | "PF-…: The licensing officer completed the site visit and needs more information on 3 items"; the card sits under Needs your response with "Respond to clarification (3 items)" | `clarification: { can_respond, open_count, round }` on the operator view |
| 2 | S-15 | same | Status bar "Pending Post-Site Clarification"; the notice on top; the form and documents locked with the reason | operator view |
| 3 | S-18 | same | Only the flagged items; the officer's comment first on each; response text; Take a photo or Choose a file (3 per item); readiness "Ready to send: n of m items answered"; Send responses disabled until every item is answered; the dialog lists the items | `GET /applications/{id}/clarifications`; responses and attachments endpoints; `POST …/clarifications/send` |
| 4 | S-15 | post_site_clarification_resubmitted | Toast "Responses sent"; status bar "Post-Site Resubmitted: the licensing officer is reviewing your responses"; page read-only | transition with the guard |
| 5 | S-18 | pending_post_site_resubmission | Only the reopened items, with the officer's new comment; round 2 | as step 3 |
| 6 | S-19 | any | Site visit tab: every round of every item, per visit; "Draft, never sent" after Reject or Withdraw | `GET /applications/{id}/clarifications` (history) |

## Admin flow (UC4-A, v0.4.0)

| Step | Screen | What the user sees / does | Engineering hook |
|------|--------|---------------------------|------------------|
| 1 | S-40 | Stat strip, applications by status, idle cases, check health, today's counts against the platform quota | `GET /admin/overview` |
| 2 | S-42 | Every audit event across applications, family filter, older pages by cursor, user rows without a case link | `GET /admin/audit-feed` |
| 3 | S-43 | Any case as the officer sees it, with the read-only banner and no actions | officer GETs with `OfficerOrAdmin`; `actions[]` empty |
| 4 | S-41 | Directory; Change role or Deactivate with a consequence dialog; own and protected rows disabled with the reason | `GET /admin/users`, `PATCH /admin/users/{id}` |

