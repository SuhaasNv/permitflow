# PermitFlow — Problem Discovery

Source of truth: the Software Engineering Assessment brief (Regulatory and Licensing Platform, 3-day MVP), provided by the assessor and kept outside the repository.

## Problem

Government licensing officers and business operators exchange licence applications through a slow, lossy back-and-forth loop. Applications arrive incomplete or incorrect; officers reject or request more information with comments that are not tied to anything specific; operators re-enter whole applications and often fix the wrong thing; nobody can easily see what changed between rounds or whether an earlier issue was actually resolved. Each cycle costs officer time, operator time, and trust.

PermitFlow is a small licensing operations platform that makes the submission → review → feedback → resubmission loop precise, traceable and fast, with AI used to pre-check uploaded documents so both sides know about obvious problems before a human review starts.

## Users

Three personas: Operator, Licensing Officer and Admin. The first two come from the assessment; Admin is our addition (see `SCOPE.md`).

### Operator (business seeking a licence)
- The person who fills in and submits the application. One account is one person; the business itself is described in the form, not modelled as a separate entity (SCOPE assumption 10).
- Wants to get a licence with the fewest possible rounds.
- Is not an expert in the regulator's requirements; needs guidance and specific feedback.
- Needs to know what stage the application is in, in plain language.
- Must never see internal regulator stages (for example, routing to approval).

### Licensing Officer
- Reviews many applications; needs full form data and documents in one organised view.
- Wants to give targeted, reusable feedback ("your floor plan is missing the kitchen layout") rather than free-text rejections.
- On resubmission, wants to see only what changed and whether each earlier issue was addressed.
- Is accountable: needs a complete audit trail of every status change, comment and resubmission.

### Admin (platform oversight)
- Not named in the assessment brief; added as a product decision because whoever operates the platform needs to answer "is it healthy and is anything stuck?" without database access.
- Wants throughput by status, idle applications, AI verification health and a cross-application audit feed; read-only on applications.

### System (AI document verification)
- Not a user, but an actor: reads uploaded documents, produces a structured verification result the officer can trust as advisory input. It never decides the application outcome.

## Current pain points (as described by the assessment)

1. Incomplete or incorrect submissions cause repeated rejection cycles (UC1 background).
2. Feedback is not linked to the specific form section or document, so operators do not know what to fix (UC1 acceptance criteria).
3. Operators re-enter the entire application on resubmission and data gets lost between rounds (UC1 multi-round support).
4. Officers cannot easily see what changed between versions or whether flagged issues were resolved (UC2 resubmission management).
5. Officers rewrite the same comments for common issues (UC2: predefined templates).
6. Applications get lost through status transitions or filtering errors; audit trail is incomplete (UC2 quality assurance).
7. Site inspection findings are captured inconsistently, leading to unclear follow-ups (UC3, deferred in this MVP).

## Desired outcome

- **Easier:** operators are guided through a structured form, see per-document verification status while uploading, and on resubmission edit only the flagged sections.
- **Faster:** officers open one organised review screen with AI pre-checks already run, use comment templates, and on resubmission review only the diff.
- **Safer:** every status transition is governed by an explicit state machine with role-based authorization on the server. Operators cannot see internal stages. Applications cannot be lost or silently mutated.
- **More traceable:** every submission round is stored as an immutable revision; every feedback item, status change and resubmission is recorded in an append-only audit trail; the officer can compare any two revisions.

## Core user journeys

### J1 — Operator submits a new application
Operator logs in → creates an application (single licence type: Food Establishment Licence, an assumption) → fills the sectioned form → drags and drops required documents → sees AI verification status per document update in near real time → sees a progress indicator → submits. Status becomes Application Received (operator sees "Submitted").

### J2 — Officer reviews and requests changes
Officer logs in → sees a review queue → opens the application → reads form data by section and documents with AI verification results → adds feedback items linked to a section or document (typed or from a template) → sets status to Pending Pre-Site Resubmission. Operator receives an in-app notification.

### J3 — Operator fixes only what was flagged and resubmits
Operator opens the application → officer comments shown at the top, each linked to its section/document → only flagged sections are editable → operator edits and re-uploads as needed → resubmits. A new revision is created; status becomes Pre-Site Resubmitted. Officer receives an in-app notification.

### J4 — Officer reviews the resubmission
Officer opens the application → changed sections are highlighted → officer compares the current revision with the previous one field by field → each earlier feedback item shows whether it was addressed → officer resolves items or raises new ones → officer either requests another round (J3 repeats) or moves the application forward (site visit, approval, rejection). Operator sees only the role-appropriate label and only the final outcome (Approved / Rejected).

### J5 — Anyone inspects history
Both roles see revision history and prior feedback (operator: their own applications only; officer: all applications). The officer additionally sees the full audit trail.

## Success criteria

Observable indicators that the MVP works:

1. J1 through J4 can be completed end to end in the deployed application with seeded users, with no manual database intervention.
2. A second resubmission round (J3 → J4 twice) works without data loss; all three revisions are visible.
3. An operator who requests another operator's application via the API receives 403/404, verified by an automated test.
4. Every status transition in the assessment's 12-state table is representable, and every invalid transition is rejected by the server with a clear error, verified by unit tests.
5. The status label shown to each role matches the assessment's mapping table exactly, verified by unit tests.
6. Uploading a document produces an AI verification result within seconds when the LLM provider is configured, and a clear "verification unavailable" state (with the application still submittable) when it is not.
7. The audit trail for an application lists every submission, status change and feedback event with actor and timestamp.
8. CI runs lint, type checks, backend tests, frontend tests and the Playwright critical journey on every push, and blocks merges on failure.
9. `README.md` setup steps produce a running system on a clean machine with Docker.
