# Release notes

What each version of PermitFlow brings, written for the people who use it. Newest first. The engineering record behind each entry is `CHANGELOG.md`; every release adds an entry here before it is tagged (`docs/09-operations/BRANCHING.md`, rule 5).

Version numbers: `v0.<sprint>.0` for the three assessment sprints, `v0.x.y` for fixes on a release, `v0.4.0` for the two epics below, `v0.4.0-rc.N` for a release candidate tagged on `dev` for the development environment before the release.

Format: the product reads this file at build time for its What's new page (the version number in the corner opens it; `frontend/src/features/releases/notes.ts`), so the lines keep four shapes. A release heading is `## vX.Y.Z, D Month YYYY (optional note): title`; a release candidate has the same heading with `-rc.N` after the version (`## vX.Y.Z-rc.N, D Month YYYY: title`) and the same blocks and bullets below it, written for what that candidate changed. Candidates sit among the releases in date order, newest first; the development environment lists them with a Release candidate label, and production hides them completely (while the build information is still loading they stay hidden). A released version's own notes never mention candidates. A bold line such as `**New for operators**` opens an audience block and the bullets under it belong to it; text before the first block is the release's introduction; `## Coming next` holds the plan. Inline, only backticks, bold and bare links are rendered. A heading of another shape fails the frontend tests.

---

## Coming next

**v0.5.0, planned: safe intake.** Every uploaded file is checked for viruses before an officer can open it, and a file that fails is blocked with a clear message. The automatic document check runs on its own worker, so a slow file never slows the rest of the service. The licensing office sees what each check cost and can tune the limits (requests, daily checks, upload size) from the overview, with every change recorded. Sign-in moves to a more secure cookie.

**After that:** a refreshed look across every screen (v0.6.0), then passkeys and two-step sign-in, self-registration and password reset by email (v0.7.0).

## v0.4.1, 9 October 2026: Singapore formats on the form, hours you pick, and steadier checks

**New for operators**
- Every field on the application form is checked as you type, with the same rules the service applies: a Singapore phone number (+65 and eight digits starting with 3, 6, 8 or 9), any of the three UEN formats, a postal code from a real sector, an address with a unit number written like #01-12, and a tenancy that ends at least three months from today.
- Operating hours are picked instead of typed: choose the days you open, then the opening and closing time from a list, or tick Open 24 hours; closing after midnight is fine and the form says so.
- What you type is tidied before it is saved: the phone number in one format, the UEN in capitals, the email in lower case, and invisible characters removed.
- An answer the form cannot use, such as a very large number, now gets a clear message instead of an error page, and the date you confirmed your declaration is always set by the service.

**New for licensing officers**
- The hours read the same way everywhere, for example "Mon to Sat, 07:00 to 21:00"; older applications keep the hours exactly as they were written.
- Re-checking a document is done from the case page, and opening an earlier visit that does not exist says so instead of showing an error page.

**Also**
- The administrator's sign-in is no longer published with the demonstration accounts.
- The PermitFlow name sits in the same place on the sign-in page as on the home page.

## v0.4.1-rc.3, 9 October 2026: steadier form checks and a tidier sign-in page

**New for operators**
- A form answer sent in the wrong shape now gets a clear message instead of an error page.
- The declaration boxes accept only a tick or no tick.

**New for licensing officers**
- Opening an earlier visit with an impossible visit number now says so instead of showing an error page.

**Also**
- The PermitFlow name sits in the same place on the sign-in page as on the home page.

## v0.4.1-rc.2, 8 October 2026: safer sign-ins and sturdier checks

**New for operators**
- A very large number typed into a number field now gets a clear message instead of an error page.
- The date your declaration was confirmed is always set by the service when you confirm it.

**New for licensing officers**
- Re-checking a document is done from the case page; the applicant's own re-check stays on the application.

**Also**
- The administrator's sign-in is no longer published with the demonstration accounts.

## v0.4.1-rc.1, 8 October 2026: Singapore formats on the form, hours you pick, and a clear test environment

**New for operators**
- Every field on the application form is checked as you type, with the same rules the service applies: a Singapore phone number (+65 and eight digits starting with 3, 6, 8 or 9), any of the three UEN formats, a postal code from a real sector, an address with a unit number written like #01-12, and a tenancy that ends at least three months from today.
- Operating hours are picked instead of typed: choose the days you open, then the opening and closing time from a list, or tick Open 24 hours; closing after midnight is fine and the form says so.
- What you type is tidied before it is saved: the phone number in one format, the UEN in capitals, the email in lower case, and invisible characters removed.

**New for licensing officers**
- The hours read the same way everywhere, for example "Mon to Sat, 07:00 to 21:00"; older applications keep the hours exactly as they were written.

**Also**
- On the development environment a strip across the top of every page says it is not the live service.
- This page lists each release candidate on the development environment; the live service shows released versions only.

## v0.4.0, 8 October 2026: the site visit, the clarification and the office's own view

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
- Checked against every WCAG 2.2 AA rule: the control you reach with the keyboard is never hidden behind a sticky bar, input and checkbox borders are easier to see, screen readers name the dashboard groups and a locked step, your contact details can be filled in by the browser, and five minutes before you would be signed out for inactivity the top strip warns you with a Stay signed in button. A second pass with nine kinds of user (voice control, Windows High Contrast and large text among them) fixed three more things: controls are named by the words they show, keyboard focus stays visible in High Contrast, and nothing is cut off at 200% text size.
- The version number in the corner opens What's new: this page, with your own changes first and every earlier release below; the word New sits beside the version until you have read it once.
- Reviewed twice before release (a code review on 21 Sep and a stability review of the whole build with a smoke test of every route the same morning): a case can no longer end with Reject as the only move after every question of a round is withdrawn, a visit date that has passed cannot be confirmed, the last taps on the checklist are saved when you leave the page by a link, and typing while an answer saves no longer loses what you typed.

---

## v0.4.0-rc.2, 21 September 2026: the What's new page, on the same build

The build of v0.4.0-rc.1 plus the page you are reading.

**New**
- The version number in the corner opens What's new, with the word New beside it until you have read the page once.
- The page lists every version newest first and marks the one you are using as This build.
- Your own changes come first; the changes for the other audiences are folded below them.

---

## v0.4.0-rc.1, 21 September 2026: use case 3, sessions, storage and the office's own view

The first build with everything planned for v0.4.0, on the development environment for testing.

**New for licensing officers**
- The site visit, the inspection checklist on a tablet and the clarification rounds on the case, with one device signed in at a time.

**New for operators**
- Answer the flagged items after the visit, with text and up to three files; the pages say how much of the application's 150 MB of storage is left.

**New for the licensing office (administrators)**
- The operations overview, the activity feed, any case read as the officer sees it, and user management.

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
