# PermitFlow: Use Cases

Use cases are grouped exactly as the Notion board epics: **E0 Foundation**, **UC1 Operator Submission & Resubmission**, **UC2 Officer Review & Feedback**, **UC3 On-Site Assessment (deferred)** and **E4 Admin Oversight & Monitoring**. Each use case has an ID `UCn-X` used in `USER_STORIES.md`, the use case diagrams and the sequence diagrams (`docs/03-architecture/diagrams/`). Requirement IDs refer to `REQUIREMENTS.md`.

## Personas

| Persona | Role code | What they do | Home screen after login |
|---------|-----------|--------------|-------------------------|
| Operator | `operator` | Business seeking a licence; creates, submits and resubmits applications; sees only own applications and operator-facing status labels | Operator dashboard (my applications) |
| Licensing Officer | `officer` | Reviews applications, gives contextual feedback, moves status, compares revisions, reads audit trails | Review queue |
| Admin | `admin` | Oversees the platform: throughput by status, stuck applications, AI verification health, cross-application audit feed; manages users (create, change role, deactivate); read-only on applications; not in the assessment brief, added by product decision (see `SCOPE.md`) | Operations dashboard |

---

## E0: Foundation

### UC0-A Log in (all personas)
**Actor:** Operator, Officer or Admin
**Requirements:** FR-028, SEC-006, SEC-010

**Main flow**
1. User submits email and password.
2. System verifies the argon2 hash, issues a JWT with the role claim, and the client keeps it in memory (and `sessionStorage` for reloads).
3. Client routes the user to the home screen for their role (see Personas). Protected routes redirect to login without a valid token.

**Alternative / error flows**
- 1a. Wrong credentials → 401 with a generic message.
- 1b. More than 10 attempts per minute from one IP → 429.
- 3a. A user opens a route for another role → the API answers 403 and the UI shows "Not available for your role".

**Expected outcome:** Each persona lands in its own workspace; the role is re-checked on the server for every request.

---

## UC1: Operator Submission & Resubmission

### UC1-A Create and submit an application
**Actor:** Operator
**Preconditions:** Logged in as operator.
**Requirements:** FR-001 … FR-007, AI-001 … AI-006

**Main flow**
1. Operator opens the dashboard and clicks "New application".
2. System creates an application in status `draft` (pre-submission state, not in the assessment table, never shown to officers) and opens the form.
3. Operator completes sections (Business details, Premises, Operations, Declarations). Each section validates on blur and on save.
4. Operator drags required documents into the upload area and selects a document type for each.
5. System stores each file, records a document row, and starts AI verification in the background. The document card shows "Verifying…".
6. Verification completes; the card shows "Verified", "Issues found (n)", "Needs review", "Unreadable" or "Verification unavailable" with a summary.
7. Progress indicator shows 100 % when all required sections are valid and all required document types are present.
8. Operator clicks "Submit application".
9. System validates completeness server-side, creates Revision 1 (snapshot of form data + document ids), transitions status to `application_received`, writes audit events, and notifies officers.
10. Operator sees the application with status "Submitted".

**Alternative / error flows**
- 3a. Section invalid → inline errors; save blocked for that section only.
- 5a. File type or size not allowed → 400 with message; no document row.
- 6a. AI provider unavailable → "Verification unavailable"; submission still allowed (AI-006).
- 8a. Missing required section/document → 422 listing what is missing; form scrolls to the first gap.
- 9a. Database error → 500 with generic message; nothing partially saved (REL-002).

**Expected outcome:** One application with one immutable revision in `application_received`; operator can no longer edit.

### UC1-B Resubmit with targeted changes
**Actor:** Operator
**Preconditions:** Application in `pending_pre_site_resubmission` with open feedback.
**Requirements:** FR-009 … FR-014, FR-021, FR-024

**Main flow**
1. Operator opens the application; status shows "Pending Pre-Site Resubmission"; the feedback panel at the top lists each open item with its target and officer comment.
2. Only sections/documents with open feedback are editable; others are read-only.
3. Operator clicks a feedback item → page scrolls to and highlights the target.
4. Operator edits the flagged section(s) and/or replaces flagged document(s). Replaced documents are re-verified by AI.
5. Operator clicks "Resubmit".
6. System creates Revision N+1 with the full snapshot (unchanged sections copied forward), marks feedback whose targets changed as `addressed`, transitions to `pre_site_resubmitted`, writes audit events, and notifies officers.

**Alternative / error flows**
- 4a. Operator attempts to edit a non-flagged section via the API → 403 "Section not open for editing".
- 5a. Operator resubmits without changing any flagged target → 422 "No changes made to flagged items".
- 6a. Concurrent officer action (for example Reject) → the row lock serialises the two; whichever runs second sees the new state and gets 409 `invalid_transition`; the operator reloads.
- 6b. Operator re-uploads the identical file for a flagged type → not a change (same `sha256`); the item stays `open` and the operator is told so.

**Expected outcome:** New revision; prior revision untouched; feedback resolution states updated; officers notified. Repeats for unlimited rounds.

### UC1-D Withdraw an application (US-038, product decision)
**Actor:** Operator (own applications)
**Requirements:** FR-032, SEC-002, AUD-001

**Main flow**
1. Operator opens a submitted application that has not been decided and chooses Withdraw application.
2. Confirms in a dialog, optionally giving a reason.
3. The application becomes Withdrawn (terminal); every active officer is notified with the reason; the audit trail records the operator as actor.

**Alternative / error flows**
| Case | Result |
|------|--------|
| Draft | No withdrawal: the draft is simply left (409 from the API) |
| Approved or Rejected | 409 "A decided application cannot be withdrawn." |
| Officer or admin calls the endpoint | 403 |
| Another operator | 404 (ownership) |

### UC1-C View history and prior feedback
**Actor:** Operator (own applications)
**Requirements:** FR-014, SEC-001, SEC-002

**Main flow**
1. Operator opens the application's History tab.
2. Sees revisions (number, submitted at) and all released feedback with states and rounds (items withdrawn by the officer before release are never shown to the operator).

**Alternative / error flows**
- 1a. Operator requests another operator's application → 404.

---

## UC2: Officer Review & Feedback

### UC2-A Review an application and request changes
**Actor:** Licensing Officer
**Preconditions:** Application in `application_received` or `pre_site_resubmitted`.
**Requirements:** FR-015 … FR-020, FR-025

**Main flow**
1. Officer opens the review queue; sees the application with its internal status label.
2. Officer opens the application and clicks "Start review". System transitions to `under_review` (assumption: explicit action so the actor is recorded) and writes an audit event.
3. Officer reads each section and each document; AI verification results and issues are shown beside each document.
4. Officer adds feedback items: chooses a target (section or document type), picks a template or types a message, saves. Each item is `open` and not yet visible to the operator.
5. Officer sets status to `pending_pre_site_resubmission` with an optional note.
6. System validates the transition, releases the round's feedback to the operator (`released_to_operator_at`), records audit events, and notifies the operator. From here the feedback set is frozen until the operator resubmits.

**Alternative / error flows**
- 2a. Another officer already started the review → button hidden; API returns 409 if called.
- 4a. Officer tries to add or withdraw feedback while the status is not `under_review` → 409 "Feedback can only be changed while the application is under review".
- 5a. Transition not allowed from the current state → 409 with allowed transitions listed.
- 5b. Zero open feedback items → 422 "At least one open feedback item is required".
- 5c. Officer decides the application cannot proceed → Reject with a note (allowed from every non-terminal post-submission state).

**Expected outcome:** Application in `pending_pre_site_resubmission` with ≥1 open feedback item; operator notified.

### UC2-B Review a resubmission and compare revisions
**Actor:** Licensing Officer
**Preconditions:** Application in `pre_site_resubmitted` with ≥2 revisions.
**Requirements:** FR-021 … FR-025

**Main flow**
1. Officer receives a notification and sees the application in the queue flagged as resubmitted.
2. Officer opens it; changed sections and documents carry a "Changed" marker.
3. Officer opens "Compare", selects the previous revision; each changed field shows old and new values; documents show added/removed/replaced.
4. Feedback panel shows each earlier item with its state (`addressed` or still `open`) and the round it was raised in.
5. Officer clicks "Start review" (`pre_site_resubmitted` → `under_review`), then marks addressed items `resolved`, or leaves them open and adds new items (feedback changes are only possible in `under_review`).
6. Officer either requests another round (UC2-A step 5) or advances the application (UC2-C).

**Alternative / error flows**
- 3a. Only one revision exists → compare control disabled with explanation.
- 5a. Operator attempts to resolve feedback via the API → 403.

**Expected outcome:** Officer sees exactly what changed; resolution tracked; audit trail extended.

### UC2-C Advance the application to an outcome
**Actor:** Licensing Officer
**Preconditions:** Application in `under_review` with no open feedback.
**Requirements:** FR-019, FR-026, FR-027

**Main flow**
1. Officer sets `site_visit_scheduled` (operator sees "Pending Site Visit").
2. Officer later sets `site_visit_done` (operator sees "Pending Post-Site Clarification").
3. Because UC3 is deferred, officer sets `pending_approval` directly (officer sees "Route to Approval", operator sees "Pending Approval").
4. Officer previews the licence certificate (watermarked, nothing stored) and sets `approved` (note optional; the certificate is issued in the same transaction, US-051) or `rejected` (note required). Operator sees "Approved" / "Rejected", the note, and after approval a Download licence (PDF) action.

**Alternative / error flows**
- 1a. `open` feedback items exist → 422 "Resolve or withdraw open feedback before scheduling a site visit" (`addressed` items do not block; the UI warns).
- 4a. Operator attempts any status change → 403.
- 4b. Documents still carry unresolved check results at approval → the Approve dialog warns; approval is not blocked (AI-005).
- 4c. Officer notices something at `pending_approval` → Return to review (`under_review`), then feedback or a resubmission round as in UC2-A; no rejection needed.

**Expected outcome:** Terminal state reached; full audit trail; operator never exposed to unmapped internal labels.

### UC2-D View the audit trail
**Actor:** Licensing Officer
**Requirements:** FR-025, AUD-001 … AUD-006

**Main flow**
1. Officer opens the application's History tab.
2. Sees revisions, feedback and every audit event (type, actor, timestamp) in chronological order.

---

## UC3: On-Site Assessment & Post-Site Clarification (DEFERRED)

Deferred per `SCOPE.md`. Intended use cases, for completeness of the traceability matrix:

- **UC3-A** Officer captures the site-visit checklist (draft save, per-item comments, mark "Need Further Clarification"); on submit the case moves to `awaiting_post_site_clarification`.
- **UC3-B** Operator sees only flagged items with the officer's comment, responds per item and uploads supporting documents; case moves to `post_site_clarification_resubmitted`.
- **UC3-C** Multiple clarification rounds per item with a full per-item audit trail.

The post-site states and transitions exist in the state machine and are unit-tested; screens and the checklist data model are not built.

---

## E4: Admin Oversight & Monitoring

Not in the assessment brief; added as a product decision (SHOULD HAVE in `SCOPE.md`) because a regulator operating the platform needs an oversight view.

### UC4-A Monitor operations
**Actor:** Admin
**Requirements:** FR-029, FR-030, NFR-007

**Main flow**
1. Admin logs in and lands on the operations dashboard.
2. Sees counts of applications by internal status, applications with no activity for more than 7 days, and today's submissions/resubmissions.
3. Sees AI verification health: runs in the last 24 h, failure/unavailable rate, average latency, provider in use.
4. Sees the cross-application audit feed (latest 50 events) and can open any application read-only (officer view, no actions).
5. Manages users: sees the directory (name, email, role, active, created, last active), creates a user with a role, changes a role, deactivates or reactivates a user. Each change is audited; the last active admin cannot be demoted or deactivated.

**Alternative / error flows**
- 1a. Operator or officer opens `/admin/*` → 403.
- 3a. AI provider not configured → panel shows "Provider: none (mock)" rather than an error.

**Expected outcome:** Admin can answer "is the platform healthy and is anything stuck?" without database access.
