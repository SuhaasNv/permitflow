# Release notes

What each version of PermitFlow brings, written for the people who use it. Newest first. The engineering record behind each entry is `CHANGELOG.md`; every release adds an entry here before it is tagged (`docs/09-operations/BRANCHING.md`, rule 5).

Version numbers: `v0.<sprint>.0` for the three assessment sprints, `v0.x.y` for fixes on a release, `v0.4.0` for the two epics below.

---

## Coming next

**v0.4.0: the admin panel and use case 3.** Two epics in one release.

*The admin panel.* A read-only oversight view for the licensing office: applications by status, the ones that have gone quiet, today's submissions, the health of the automatic document checks (how many ran, how many failed, how long they took), a feed of recent activity across every application, and a user directory where an administrator can change a role or deactivate an account (every change audited; the last active administrator cannot be removed). The admin role and its routes are already reserved; the screens are the work. Stories US-070 to US-073.

*Use case 3, the site visit.* After a visit is scheduled, the officer opens the inspection checklist on site from a tablet, fills it item by item with comments, saves it as a draft between rooms and finishes it later, and marks the items that need clarification. Submitting the checklist moves the case to Pending Post-Site Clarification on its own. The operator then sees only the flagged items with the officer's comment on each, answers them one by one and attaches supporting documents; several rounds per item are supported and every exchange is kept with its timestamps. The three post-site statuses and their transitions already exist and are tested; the checklist model, the officer's tablet screen and the operator's targeted-response screen are the work. Stories US-060 to US-066.

**Unreleased, on `dev` since 20 September 2026 (will ship as v0.3.1, or with v0.4.0):** a refused action tells the operator where the application is in their own words; a check stuck past three minutes offers Re-run on its own; a failed background refresh no longer replaces the page or drops unsaved work; oversized uploads are refused before the file is read; a refused check no longer counts against the daily allowance; provider problems are reported to operators as "unavailable" rather than as technical codes; the release process is pinned and protected (release images only from a tag, production on a fixed image, main behind a pull request with required checks).

---

## v0.3.0, 19 September 2026: production

The first version on the public address, https://permitflow.space, with a development copy at https://dev.permitflow.space.

**New**
- Live on a custom domain with TLS, two isolated environments (development and production), and production behind an approval step.
- Licence certificate: on approval a PDF certificate is issued and can be downloaded by the applicant and by officers; officers can preview it before deciding.
- Withdraw an application: an operator can withdraw a submitted application with an optional reason; officers are told.
- Delete a draft: a never-submitted draft can be removed outright.
- Undo for officers: a withdrawn or resolved feedback item can be restored within a few seconds; an addressed item that is not actually fixed can be reopened with the same text.
- Search and grouping on the operator list and the officer queue.
- Flagged sections are marked in the form rail and the stepper, and the form walks the operator through only the flagged items to Resubmit.
- Return to review: an officer at the decision step can send a case back to review instead of rejecting it.
- Privacy, terms and cookie pages; demonstration notices on sign-in and uploads; fonts served by the site itself.

**Improvements**
- Every screen fits a phone width without sideways scrolling; navigation opens at the top of the page.
- Session warning appears only in the last 30 minutes.
- Sign-in page shows or hides the password.
- Clearer wording on the application header, feedback headings and the template picker.

**Behind the scenes**
- Automatic checks are limited per applicant and per day, and every request is rate limited, so a public demonstration cannot be knocked over or run up a bill.
- The AI check is evaluated on every code change (pipeline, on a deterministic stand-in) and nightly against the real model (14 golden cases, 18 name-swapped fairness runs), with a trace per check.
- Accessibility gate over 23 screen states in the build; contrast corrected; keyboard and skip-link tests.
- 748 backend and 152 frontend tests, eight browser scenarios, coverage thresholds, secret scan and dependency audits, all blocking.

**Known limitations** (full list in `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md`)
- Use case 3 (site visit) is not built; a site visit is a status change only.
- Notifications are in-app only; no email.
- Images are stored but not read by the automatic check; PDF and text files are.
- The demonstration accounts share one published password by design.

---

## v0.2.0, 18 September 2026: the loop closes

**New**
- Officer queue: every submitted application with its status, whose turn it is, and what needs attention.
- Case review: all sections and documents in one place, with the automatic check's findings, confidence and evidence beside each document.
- Feedback tied to a section or a document, with seven ready-made comment templates; drafts until the officer requests a resubmission.
- Request resubmission: the operator sees the feedback at the top, only the flagged parts reopen, and resubmits a new revision; the rest of the application is kept as submitted.
- Compare revisions: what changed, field by field and document by document, between any two versions.
- Resolution tracking: an item becomes "addressed" when its target changes and "resolved" when the officer confirms.
- Audit trail of every status change, submission, feedback and document event, readable by officers.
- In-app notifications for operators (status changes) and officers (resubmissions), with an unread count.
- Site visit, route to approval, approve and reject with a note, so a case reaches a final outcome.
- The real document check with OpenAI, behind the same interface as the stand-in used in tests.

**Improvements**
- Unsaved changes are protected on refresh, navigation and sign-out; a second tab cannot overwrite an edit in progress.
- Interrupted checks recover on restart with a Re-run.

---

## v0.1.0, 18 September 2026: an operator can submit

**New**
- Sign in as an operator or an officer with seeded accounts.
- Create a Food Establishment Licence application and complete four sections with inline validation and autosave.
- Upload the four supporting documents by drag and drop (PDF, PNG, JPG, TXT, up to 10 MB), with an identical re-upload detected as "no change".
- A live check status on every document while the automatic check runs.
- A progress indicator across sections and documents, and Submit when complete.
- Role-specific status labels exactly as the licensing table defines them.
- Public landing page.
