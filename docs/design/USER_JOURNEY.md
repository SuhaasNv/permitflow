# PermitFlow: user journey as built (19 Sep 2026)

One record of what a person actually does and sees, step by step, in the product as it runs today. Written after Sprint 2, from the browser. Screen IDs refer to `SCREEN_INVENTORY.md`; statuses use the role-specific labels from `../architecture/STATE_MACHINE.md`. Two personas only: the operator (the person who fills in and submits the application, SCOPE assumption 10) and the licensing officer. The admin persona is Sprint 3.

## The loop in one line

Operator applies and submits → officer reviews with AI-assisted document checks → officer sends contextual feedback and requests a resubmission → operator changes only the flagged parts and resubmits → officer sees what changed, resolves feedback, schedules a site visit, routes to approval and decides → operator sees the outcome and the officer's note. Every step is a numbered revision, an audit event, and a notification to the other side.

## Operator journey

| Step | Where | What the operator does | What the system does | Status the operator sees |
|------|-------|------------------------|----------------------|--------------------------|
| 1 | Landing S-01 | Reads what the licence needs (four documents), signs in | Signed-in users never see the landing page | |
| 2 | Sign in S-02 | Email and password (seeded account) | JWT for 8 hours; 10 failed attempts per address pause sign-in for a minute; the top bar warns only in the last 30 minutes ("Session ends in 12 min"); a dead session ends in one place and the sign-in page says why | |
| 3 | Dashboard S-10 | Sees a greeting, one summary line and work cards grouped by who is waiting on whom; clicks New application | Draft created with a sequential reference, `application.created` audited | Draft |
| 4 | Application S-11 | Sees the four numbered sections, the documents row and the completion card; Continue application | Editability computed by the state machine: everything open while draft | Draft |
| 5 | Form S-12 | Fills a section; Save section, Save and continue, or Save and exit (saves the partial draft first) | Zod validation as they type, server validation on save (422 per field), row lock, `section.updated` audit with field names only; refresh or tab close with unsaved input prompts first; another tab's save never wipes local typing | Draft |
| 6 | Documents S-13 | Drops or picks a file per required document | Allowlist, magic bytes, 10 MB (header check first, then streamed), sha256 so an identical re-upload is "no change"; a check runs in the background and the slot polls every 2 s until it lands; replace, remove (draft only), download, re-run | Draft |
| 7 | Documents S-13 | Reads the check result in plain language: Verified, n issues to check, Needs officer review, Could not read, Check unavailable | Operator never sees confidence or evidence; the result is advisory and never blocks submission | Draft |
| 8 | Review S-14 | Reads the answers sheet, sees any checks still running, submits | Completeness guard (422 with every gap), Revision 1 snapshot, `revision.submitted` + `status.changed` audit, every active officer notified | Submitted |
| 9 | Submitted S-15 | Confirmation with reference, status and what happens next | The application is read-only; review and submitted pages redirect if opened in the wrong state | Submitted |
| 10 | Bell S-17 | Sees "Under Review" arrive | Officer started the review; notification written in the same transaction as the status change | Under Review |
| 11 | Bell, Dashboard | Sees "Pending Pre-Site Resubmission"; the card moves to Needs your response with a red Respond action | Officer requested a resubmission; that round's feedback was released and frozen | Pending Pre-Site Resubmission |
| 12 | Application S-11 (respond) | Reads the feedback notice on top: each item with its target, the officer's words and a link; Respond to feedback jumps to the first flagged target | Only sections and document types with open released feedback are editable; the rest say "the officer did not ask for changes here" and the API returns 403 | Pending Pre-Site Resubmission |
| 13 | Form S-12 or Documents S-13 | Changes the flagged section or replaces the flagged document; the officer's comment sits inline on the target; Save and continue walks only the flagged items and ends at the application page; locked sections show a lock in the rail and stepper (US-040, US-041) | Readiness reports what changed and what is still untouched; the form and the application page show "Ready to resubmit: n of m changed"; Resubmit stays disabled until one flagged target changed | Pending Pre-Site Resubmission |
| 14 | Application S-11 | Resubmit, confirms in a dialog that names untouched items | Revision 2 snapshot; items whose target changed become Addressed; `feedback.addressed`, `revision.submitted`, `status.changed` audited; officers notified with "n of m items addressed" | Pre-Site Resubmitted |
| 15 | History S-16 | Sees every revision, "what changed from Revision 1" (field by field, documents by content), every feedback item by round with its state | Compare endpoint is owner-scoped; Revision 1 is immutable | any |
| 16 | Bell, Application | Sees Pending Site Visit, then Pending Approval, then Approved or Rejected with the officer's note in an outcome panel | Decision note is served to the operator only with the final outcome; nothing can follow a decision | Pending Site Visit → Pending Approval → Approved / Rejected |
| any time before step 8 | Application S-11 | Discard or Delete draft when the application was started by mistake | Draft removed outright with its files; only submission creates the record (US-045) | |
| any time after step 8 | Application S-11 | Withdraw application (optional reason) when the licence is no longer needed | Terminal Withdrawn status, officers notified, audited with the operator as actor (US-038) | Withdrawn |

## Licensing officer journey

| Step | Where | What the officer does | What the system does | Internal status |
|------|-------|-----------------------|----------------------|-----------------|
| 1 | Sign in S-02 | Same form, officer account | Lands on the queue | |
| 2 | Queue S-20 | Sees Needs review by default (plus Waiting on operator, Decided, All), each row with applicant, status, document-check state and the next action | Queue refreshes every 30 s; next action is server-derived from the state machine | Application Received |
| 3 | Case S-21 | Opens the case: key facts strip, the submitted revision (never the working copy), each document with its check result, confidence, model and evidence quotes, revision history, review rail | Officer-only endpoint; operators and admins get 403; drafts are 404 | Application Received |
| 4 | Case S-21 | Start review | Row lock, version check (409 if stale), `status.changed` with the officer as actor, operator notified | Under Review |
| 5 | Case S-21 | Re-runs a check if needed; reads the AI summary (analysed, verified, issues, need review) | Re-run audited as `verification.requested`; result polls in every 2 s | Under Review |
| 6 | Feedback rail S-21 | Add feedback: picks a template (fills target and message), edits the text, adds; items mark their section or document inline; withdraws a mistake | Create and withdraw only while Under Review (409 otherwise); `feedback.created` / `feedback.withdrawn` audited; drafts are not visible to the operator | Under Review |
| 7 | Review rail S-21 | Request resubmission (enabled once one item is open; Mark site visit scheduled is blocked while an item is open, with the reason shown) | Every open item gets `released_to_operator_at`, `feedback.released` audited, operator notified with the operator label | Pending Pre-Site Resubmission |
| 8 | Bell, Queue | Sees "Resubmission PF-…, 1 of 2 items addressed"; the row says Review resubmission | Resubmit notification to every active officer | Pre-Site Resubmitted |
| 9 | Case S-23 | Resubmitted banner with change counts; Changed / Replaced markers on the sections and documents that differ; Compare revisions panel (any two revisions, old struck, new highlighted); Addressed in Revision 2 badges; Start review | Diff is field-level for the form and by content hash for documents | Pre-Site Resubmitted → Under Review |
| 10 | Feedback rail | Mark resolved on addressed (or open) items; a warning stays while addressed items are unresolved | `feedback.resolved` audited; open items block the site visit, addressed ones only warn | Under Review |
| 11 | Review rail | Mark site visit scheduled → Mark site visit done → Route to approval → Approve (note optional) or Reject (note required, from any non-terminal state) | Each is a state-machine edge with a guard; the operator sees Pending Site Visit, Pending Post-Site Clarification is unreachable in the MVP UI (UC3 deferred), then Pending Approval, then the outcome | Site Visit Scheduled → Site Visit Done → Route to Approval → Approved / Rejected |
| 12 | Audit trail S-25 | Opens the append-only trail: every event with actor, role, time and a plain sentence; filters by family | Nothing can be edited or removed; system events (checks) have no actor | any |

## What is deliberately not in the journey

- No account creation, password reset or SSO: accounts are seeded (SCOPE, Deferred).
- No site-visit checklist or per-item clarification rounds (UC3, deferred): the visit is a status change, not a form.
- No email or SMS: notifications are in-app; delivery is a logged mock.
- No officer assignment: every officer sees the whole queue.
- The admin persona (oversight, user management) is Sprint 3.
