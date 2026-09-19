# PermitFlow walkthrough: narration

Voice: Kokoro af_heart, speed 0.95. One cue per line; the cue key is the file name. Plain speech, no jargon, no em dashes. Sentences about a check result are written from the take and never quote the model.

[w01-title]
PermitFlow. One application, from draft to licence, with every step on record.

[w02-catch]
Before anything else, the catch. The operator uploaded a food hygiene certificate, and the check found it had expired, before submission, before any officer looked.

[w03-catch-wide]
The other three documents came back verified. This is the operator's view. The officer sees more, and we will get there.

[w04-loop]
Here is the whole loop, from a new application to the licence.

[w05-new]
The operator starts on the dashboard. New application opens the form.

[w05b-sections]
Four sections: business, premises, operations and declarations, then the documents, then review.

[w06-form]
Each field validates as it is typed, and every section saves as a draft, so nothing has to be finished in one sitting. Premises and operations follow the same pattern.

[w07-documents]
Four required documents, one slot each. PDF is recommended, because it is the only format the check can read.

[w08-checks]
Every upload is read and compared with the form while the operator carries on. The clean documents come back verified within seconds.

[w09-flag]
The certificate does not. Two issues to check, in plain language, with what to do about them. The check never blocks anything: the operator can still submit.

[w10-submit]
Submit once. The application becomes Revision 1, a snapshot that can never be changed, and the operator sees exactly what happens next.

[w11-queue]
The licensing officer's side. The application is already in the queue, with the checks run and one document flagged.

[w12-case]
The case page holds the whole submission: the form by section, every document with its result, and the review rail. Start review records the officer's name in the audit trail.

[w13-evidence]
Here the officer sees what the operator does not: the confidence, the model, and the evidence quoted from the document itself. Valid until 3 January 2025.

[w14-feedback]
Feedback is tied to the exact document. A template saves the typing; the officer can still edit it. It stays a draft until the round is sent.

[w15-request]
Request resubmission releases the feedback and freezes it. The status changes, the operator is notified, and only the flagged item will reopen.

[w16-respond]
Back with the operator. The feedback sits on top, linked to its document. Three sections are locked. One slot is open.

[w17-replace]
A new certificate replaces the old one. The check runs again and comes back verified.

[w18-resubmit]
Ready to resubmit: one of one flagged item changed. Resubmit records Revision 2. Nothing else was re-entered, and nothing from Revision 1 is lost.

[w19-compare]
The officer opens the resubmission. Only the changed document is highlighted, and Compare shows Revision 1 against Revision 2, field by field.

[w20-resolve]
The item was marked addressed automatically when the document changed. Resolving it is the officer's call, and it is recorded.

[w21-visit]
After the review, a site visit. Scheduling and completing it are status changes with the officer's name on them; the checklist itself is deferred in this release.

[w22-approve]
Route to approval, then a decision with a note. Approval issues the licence in the same transaction as the status change.

[w23-licence]
The operator sees the outcome and downloads the licence.

[w23b-pdf]
The licence carries the number, the validity dates and a verification code. It was rendered in the same transaction that approved the application.

[w24-audit]
Every step is on record: submissions, status changes, feedback, documents, decisions. Each with who and when. Nothing here can be edited or removed.

[w25-boundary]
Roles are enforced on the server. An operator who opens an officer address sees this, and the API answers four zero three.

[w26-state]
Behind the status badges is one table: fourteen states, who may move between them, and under which guard. A test walks every combination.

[w27-tests]
Seven hundred and forty-eight backend tests run against a real database, one hundred and fifty-two in the browser, and eight end-to-end journeys.

[w28-gate]
Every push runs a six-stage AI gate: model approval, contracts, the golden set, adversarial cases, fairness, verdict.

[w29-fairness]
The fairness check swaps the applicant's name across Singapore's communities and expects the same answer. The first run failed two of twenty-one. The cause was the harness, not the model: a leftover email in the form. Fixed, and twenty-one of twenty-one twice since.

[w30-scope]
What is built: use cases one and two, the full lifecycle. Deferred: the site-visit checklist. Simplified: email delivery, in-process checks, local file storage, and a session token in browser storage.

[w31-close]
Checks help you. Officers decide.
