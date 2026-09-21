# Release notes

What each version of PermitFlow brings, written for the people who use it. Newest first. The engineering record behind each entry is `CHANGELOG.md`; every release adds an entry here before it is tagged (`docs/09-operations/BRANCHING.md`, rule 5).

Version numbers: `v0.<sprint>.0` for the three assessment sprints, `v0.x.y` for fixes on a release, `v0.4.0` for the two epics below, `v0.4.0-rc.N` for a release candidate tagged on `dev` for the development environment before the release.

---

## Coming next

**v0.4.0: use case 3 and the admin panel, built, reviewed and waiting for the release.** Built on `dev` on 20 and 21 September 2026 (`docs/05-planning/RELEASE_PLAN_V0_4_0.md`), reviewed twice on 21 September, and tagged on `dev` as the release candidate `v0.4.0-rc.1` for the development environment; production keeps v0.3.0 until the owner runs the release ritual after the Xtremax process, when the same commit line becomes `v0.4.0` on `main`. The entry below is what the release will say.

## v0.4.0 (release candidate `v0.4.0-rc.1` on the development environment, 21 September 2026; production release to follow): the site visit, the clarification and the office's own view

**New for licensing officers**
- Arrange the site visit inside the case: propose a date and a morning or afternoon slot, see the operator accept or propose another date, keep or accept, ask to move a confirmed visit; six proposals at most per visit; every round on the record.
- The inspection checklist on a tablet: seventeen items in five sections, a result and a comment each, saved as a draft as you go (also when the lid closes or the connection drops), the items that need clarification flagged, findings of your own added where the template has none, and a submit that records the visit done and sends the flagged items to the operator in one step.
- The clarification rounds on the case: read each answer with its evidence, mark an item clarified, ask again, withdraw a question, request another round, route to approval when nothing is open.
- One device at a time: your account is signed in on one device; a second sign-in tells you where it is and lets you sign that device out and continue where the draft was last saved.

**New for operators**
- Answer the flagged items after the visit: the officer's comment on each item in plain words, a text answer per item, up to three files (a photo from the phone camera included, stored without its camera data), one Send when every item is answered, and the whole history of rounds on the application.
- Answers and files wait through a lost connection and go the moment it returns; every date and time is Singapore time.

**New for the licensing office (administrators)**
- An operations overview: every status with its count, the applications idle for more than seven days, today's submissions and rounds, and the health of the automatic document checks against the daily quota.
- The activity feed across every application and every account change, and any case readable exactly as the officer sees it, without a single control.
- Users: change a role, deactivate or reactivate an account, add an account; the demonstration accounts are protected; the last active administrator cannot be removed.

**Also**
- Each application has 150 MB of storage room across its documents, evidence and licence; the pages say how much is left before a file is chosen.
- The accessibility gate covers every new screen; every control on the checklist and the respond page is at least 44 px on a phone or a tablet.
- Reviewed twice before release (a code review on 21 Sep and a stability review of the whole build with a smoke test of every route the same morning): a case can no longer end with Reject as the only move after every question of a round is withdrawn, a visit date that has passed cannot be confirmed, the last taps on the checklist are saved when you leave the page by a link, and typing while an answer saves no longer loses what you typed.

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
