# PermitFlow: UI states

UX-002 requires explicit loading, empty, error and success states for every data view. This document lists them per screen and specifies the two lifecycles the brief singles out: upload → verification, and feedback open → addressed → resolved.

## Global states

| State | Rendering | Notes |
|-------|-----------|-------|
| Loading (page) | `PageSkeleton` (eyebrow, title, subtitle) plus shimmering blocks in the shape of the final layout | never a blank page or a spinner-only page |
| Saving (section) | footer `SaveIndicator`: "Unsaved changes" (amber dot) → "Saving…" (spinner) → "Saved just now" (drawn check), then relative time | live region |
| Checking (document) | badge "Checking" with pulsing dot; verification block lists the four check steps advancing while the server run is pending | result copy always from the server |
| Success (toast) | bottom-right toast, 4.5 s | section saved, document uploaded |
| Loading (mutation) | button shows spinner + "Saving…", inputs stay editable-but-disabled | input never cleared |
| Empty | `EmptyPanel` with icon, one-line title, one-line explanation, one action | copy is specific ("No applications yet: start a new application") |
| Error (query) | `ErrorPanel` with request id and Retry; mutation errors as an inline `Alert` with the server message | REL-005 |
| Error (mutation) | inline `Alert error` above the form/action + field errors; input preserved | REL-005 |
| Permission denied (403) | full-panel "Not available for your role" | UC0-A 3a |
| Not found (404) | "Application not found" with back link | SEC-002 (other operators' applications look like 404) |
| Stale version (409 `version_conflict`) | banner "This application changed since you opened it: Reload" | REL-007 |
| Stale checklist (409 `version_conflict`, v0.4.0) | the server returns the current content; the page merges the officer's unsaved input over it and says "Updated from another session; your unsaved changes are kept"; never a silent overwrite (US-061) | REL-007, designed |
| Moved under us (409 on an appointment decision, a checklist save after a submit elsewhere, a clarification send after a withdrawal; v0.4.0) | toast "This application changed since you opened it. Showing the latest." (or, for the checklist, the server's sentence "This checklist was submitted; its findings can no longer change."), then the page reloads the case and the panel from the server and drops the stale input; never the raw server reason, never a stale rail (UAT run 4, 21 Sep) | REL-007 |
| Lapsed appointment proposal (v0.4.0, 21 Sep) | the officer's date arrived unanswered: the operator card says "This date has passed and can no longer be accepted; propose another one below" with the counter form; the officer rail's Confirm without a reply is disabled with "This date has passed; propose another one." and a Propose another date button opens the date form; a confirmed date that has arrived cannot be moved | REL-007 |
| Invalid transition (409 `invalid_transition`) | dialog error line listing allowed actions | SEC-004 |
| Session expired (401) | any 401 (or the token's own expiry timer) ends the session in one place; sign-in page shows "Your session ended" and honours the return path only inside the role's own area | SEC-006 (built) |
| Session ended elsewhere (401 `session_revoked`, US-093) | the sign-in page names the reason from the server's details: "Your session ended: this account signed in on another device at 21 Sep, 10:05", the idle sentence with the configured minutes, or "You signed out"; signing in again clears it | NFR-019 (built) |
| Account in use (409 `session_active` on sign-in, US-093) | a warning block under the form: "This account is signed in on Safari on iPad, last active 21 Sep, 10:05", the loss warning ("anything typed in the last second or so may be lost"), "Sign out the other device and continue" (primary) and Cancel; the email and password stay in the form | NFR-019 (built) |
| Unsaved changes | browser "leave site?" prompt on refresh or close while a section is dirty; in-app navigation and Sign out show the "Leave without saving?" / "Sign out without saving?" dialog with Stay focused; "Save and exit" saves the partial draft first | built |
| Updated elsewhere | a dirty section is never overwritten by data from another tab: warning with "Discard my edits" | built |
| Check taking too long | after 3 minutes pending or running, polling stops, the block says so and Re-run is offered | built |
| Offline / network | the request fails as `network_error` ("Could not reach the server") in the `ErrorPanel` or the inline `Alert`; reads retry through the query client when the page is refreshed. **v0.4.0 (US-061, US-087):** the checklist page and the respond page listen to `navigator.onLine` and show a warning banner within a second ("You are offline: changes will not save until you reconnect" / "You are offline: answers and files wait here until you reconnect"); a failed save or upload is retried after 1, 2, 4, 8, 16 then 30 s, never while the tab is hidden, and at once when the connection or the tab returns; the checklist's `SaveIndicator` has a "Could not save, retrying" tone and the respond page says so under the field; an evidence upload shows a progress bar; a save whose response was lost is replayed with the same `save_id` and answered 200, never as a conflict | built |
| Rate limited (429, US-058) | the server message ("Too many requests. Try again in a moment.") in the `ErrorPanel` or inline `Alert`; on sign-in, the message names which limit was hit; queries do not retry a 4xx, so a limit never causes a retry storm | built |
| Storage room (US-085) | one sentence beside every file picker on the operator's pages: "147 MB of the application's 150 MB storage room is left", or, at zero, "This application has used its 150 MB of storage room. Remove a file you no longer need before adding one."; a refused upload shows the server's sentence naming the room (422 `storage_budget`); an image the server cannot read is refused with "The image could not be read. Send it again, or save it as a PDF." | NFR-009 (built) |
| Draft limit (409 `draft_limit`, US-058) | "You already have 20 draft applications. Submit or delete one before starting another." in the dashboard and list alerts, without the generic retry advice | built |
| Unknown route (404) | `NotFoundPanel` "Page not found" with a link to the front page; an application that does not exist keeps "Application not found" | built |

## Upload → verification lifecycle (S-12, S-15)

These are two separate stages and are shown separately: the **upload badge** in the card header and the **verification block** below it.

| # | Stage | Upload badge | Verification block | User can |
|---|-------|--------------|--------------------|----------|
| 1 | Idle slot | "Missing" (neutral) | none | drop / browse |
| 2 | Dragging over | drop zone `over` style (primary border, soft fill) "Drop to upload <file>" | none | drop |
| 3 | Client validation fails | inline error in the slot: "Word documents are not accepted. Save the file as PDF and try again." / "File is larger than 10 MB." / "Only PDF, PNG, JPG or TXT." | none | choose another file |
| 4 | Uploading | progress bar with % | none | cancel |
| 5 | Server validation fails (400: extension/MIME/magic bytes/size) | error with the server message | none | choose another file |
| 6 | Duplicate (same sha256 as the current file of that type) | info: "This is the same file as the one already attached: nothing changed." | unchanged | pick a different file |
| 7 | Upload complete | "Upload complete" (success) | **pending** "Queued for checking" | download, remove (draft) |
| 8 | Check running | "Upload complete" | **running** spinner + indeterminate bar + what is being compared; card polls every 2 s | download |
| 9 | Result | "Upload complete" | one of **verified / issues_found / needs_review / unreadable / failed / unavailable** (copy in DESIGN_SYSTEM) | re-run (terminal only), replace |
| 10 | Replace (flagged slot during resubmission) | new file "Upload complete" + "replaces <old name>" | new run from pending | previous file remains in the earlier revision |

Input validation rules the UI reflects (SEC-005, DOMAIN_MODEL Document): allowlist PDF/PNG/JPG/JPEG/TXT by extension and MIME, magic-byte check on the server, 10 MB cap, server-generated storage key, one current file per document type, `sha256` stored per file. PDF is the recommended format and the only one the checker can read; images are accepted and stored but marked "Could not read" (no OCR in the MVP). The duplicate check uses the stored hash: re-uploading an identical file is reported as no change (and, during resubmission, does not count as addressing feedback: USE_CASES UC1-B 6b).

Verification results never block anything: submit stays enabled with a warning summary on S-13.

## Feedback lifecycle (S-15, S-16, S-21, S-23)

| State | Operator sees | Officer sees |
|-------|---------------|--------------|
| Draft (open, not released) | nothing | "Open · not yet released", Edit / Withdraw (only while under_review) |
| Open (released) | numbered item, amber, target tag, "Go to", inline note inside the target, target editable | "Open", frozen (no edit/withdraw while pending resubmission) |
| Addressed (target changed in Revision N) | "Addressed in Rev N" + "You changed: …" | "Addressed in Rev N" + "Changed: 48 → 62" / "Replaced: file", Mark resolved, View change |
| Resolved | green, message greyed | green, "Resolved by you · date" |
| Withdrawn (before release) | never shown | greyed, "Withdrawn", in audit only |

Progress on S-15: "Items addressed n of m"; Resubmit enabled once n ≥ 1.

## Per-screen states

| Screen | Loading | Empty | Error | Success / other |
|--------|---------|-------|-------|-----------------|
| S-00 | button spinner | none | generic "Email or password is incorrect"; 429 shows the server message (failed-attempt window, or too many sign-ins from this network) | redirect by role |
| S-44 What's new | none (the notes are in the build); the build line fills in when `/health` answers | none (the notes always hold at least one release) | `/health` unreachable: the build line shows the version alone; unknown version in the URL: the newest release | the reader's own block open under "For you", the other audiences folded with a count, "For everyone" open; "This build" on the running release; the "New" mark beside the version chip until the page is opened once per browser (`localStorage`, works without it) |
| S-10 | strip + table skeleton | no applications | retry | none |
| S-11 | form skeleton | new draft (all sections "Not started") | save failed (input kept); 403 if not draft ("This application can no longer be edited") | "Draft saved" note; section "Complete" badge |
| S-11 (application) | sections + completion skeleton | none | withdraw 409 ("A decided application cannot be withdrawn.") as an error toast, dialog closes | withdraw: danger dialog (Cancel focused, reason optional) → toast "Application withdrawn" → neutral outcome panel with the reason; Withdraw panel disappears (US-038) |
| S-12 | slot skeletons | all four slots empty | upload errors above; poll error → block shows "Could not refresh: retry" | see lifecycle |
| S-13 | summary skeleton | none | 422 gaps listed and linked; submit disabled until complete | → S-14 |
| S-15 | status bar + feedback skeleton | no released feedback (read-only view) | 403 non-flagged, 422 no change, 409 conflict | toast "Resubmitted"; status bar updates |
| S-16 | list skeleton | single revision ("Compare available after your first resubmission") | retry | none |
| S-20 | strip + rows skeleton | "No applications in the queue" / filtered empty | retry | none |
| S-21 | facts + sections skeleton | feedback rail empty ("No feedback yet: use Comment on a section or document") | 409 stale (reload banner), composer disabled with reason and closed automatically when the case locks | toast per feedback action; Withdraw and Mark resolved toasts carry Undo for 10 s; Mark resolved only on items sent to the operator (US-039) |
| S-23 | as S-21 | nothing changed (cannot happen: resubmit requires change) | as S-21 | toast on resolve |
| S-24 | table skeleton | single revision → disabled control with explanation | retry | none |
| S-25 | rows skeleton | new application (only created event) | retry | none |
| S-26 | viewer skeleton | not applicable (only linked while pending approval) | 409 when the application is no longer pending approval (link back to the case); fetch error with retry | PDF inline with the preview watermark; download fallback link |
| S-11b (approved) | as S-11 | not applicable | download failed toast | outcome panel with the officer's note when present and Download licence (PDF) with number and validity |
| S-32 (v0.4.0) | none (dialog) | none | date in the past or not a working day: inline error; 409 when the case moved | the case moves to Site Visit Scheduled; toast "Visit proposed" |
| S-33 (v0.4.0) | card skeleton | no visit yet (card absent) | counter-proposal too soon ("Choose a date at least 2 working days ahead."), weekend, over 60 days, reason missing, 409 when the officer decided first (toast and reload); at the six-proposal cap the counter form gives way to "No more dates can be proposed for this visit. You can still accept this one." | Waiting for your reply (Accept this date opens a confirmation; or counter), Waiting for the officer (your proposal shown), Confirmed (date and slot, Request a different date), Done; the header sentence follows the state |
| S-34 (v0.4.0) | panel skeleton | no proposal yet on a case scheduled through the API: "Propose a visit date" | 409 when the operator replied first; Confirm without a reply disabled with "Available from … if the operator has not replied."; at the cap "Propose another date" disabled with the round-limit reason | Waiting for you (Accept, Keep, Propose another date), Waiting for the operator (the reply deadline), Confirmed (Request a different date), Done; Mark site visit done enabled only once confirmed |
| S-30 (v0.4.0) | page skeleton in the shape of the section list | new checklist: every item Not assessed, progress "0 of 17 assessed" | 409 outside the site-visit states ("The checklist opens once a site visit is scheduled"), 409 `checklist_submitted` on a save after submit, 409 `version_conflict` merged (above), 422 on submit listing the item keys (page scrolls to the first), save failed → retrying tone, offline banner | Saved just now / Saved hh:mm after each autosave (1.5 s after the last touch, on leaving the list, when the tab goes to the background or the page unloads, or Save draft); the browser's leave-page alert appears only while a save is still pending or failing, never after one landed; Could not save, retrying (backoff) after a failed save; the offline banner; "Another tab or device saved this checklist" once a stale version was merged (their copy, the officer's touched items kept on top, saved again); submit dialog lists the flagged items (US-063); after submit the page is read-only with "Submitted by … on …" and the case card links to it |
| S-31 (v0.4.0) | rail skeleton | nothing flagged: "Nothing to clarify. Route to approval when you are ready." with the primary action | 409 stale (reload banner as S-21); item action refused (409) shown inline; Route to approval disabled with the reason | toast per item action ("Marked clarified", "Reopened, not sent yet", "Withdrawn"); Request another round confirms with the open items listed |
| S-18 (v0.4.0) | page skeleton | no released item: "Nothing needs your response yet" with a link back to the application | 422 on send listing the unanswered keys (scroll to the first); attachment errors inline in the item (type, size, fourth file "You can attach up to 3 files per item", duplicate "This is the same file as one already attached"); 409 when the round was already sent or the case moved (reload banner); failed send keeps every typed response | readiness line "Ready to send: n of m items answered"; toast "Responses sent"; status bar "The licensing officer is reviewing your responses"; the page becomes read-only |
| S-19 (v0.4.0) | list skeleton | no site visit yet ("The site visit stage has not started") | retry | "Draft, never sent" on an unsent response after Reject or Withdraw |
| S-40 (v0.4.0) | strip and table skeleton | no applications at all ("No applications yet"); provider none → "Provider: none (mock)" | retry with request id | none (read-only) |
| S-42 (v0.4.0) | rows skeleton | no events ("Nothing has happened yet"); filtered empty ("No events of this kind") | retry; older page failed → inline retry under the list | "Show older activity" appends; user rows without a case link |
| S-41 (v0.4.0) | rows skeleton | filter or search with no match ("No accounts match") | 409 `last_admin` ("This is the last active administrator"), `self_change` ("You cannot change your own account"), `protected_account` ("Demonstration account, protected") shown in the dialog as an inline `Alert`; own and protected rows disabled beforehand with the reason in `title`; the Add an account dialog validates name, email and the 12-character password inline and shows 409 `email_taken` as "An account with this email already exists."; retry | toast "Role changed" / "Account deactivated" / "Account reactivated" / "Account created" (built) |
| S-43 (v0.4.0) | as S-21 | as S-21 | 404 for an unknown id; every mutation route 403 (never reachable from the page: no control is rendered) | banner "Read-only: administrators cannot act on a case"; Back to the overview |

## Checklist and clarification lifecycle (v0.4.0, S-30, S-31, S-18, S-19)

The inspection record and the clarification threads are two things: the checklist's findings freeze at submit; the threads keep moving until the case leaves the post-site states.

| # | Stage | Officer sees (S-30, S-31) | Operator sees (S-18, S-19) | Case status (officer label / operator label) |
|---|-------|---------------------------|----------------------------|------------------------------------------------|
| 1 | Visit scheduled, checklist not opened | Case page: primary action "Open checklist" | Pending Site Visit | Site Visit Scheduled / Pending Site Visit |
| 2 | Draft on site | every item Not assessed until touched; result, comment, flag per item; Saved hh:mm, retrying, offline banner; progress "n of 17 assessed, f flagged, c comments missing"; submit disabled with the reason | nothing changes | same |
| 3 | Submitted | findings read-only; "Submitted on … by …"; the rail shows the flagged items as Open with the finding at the top of each thread; Request another round is not needed for round 1 (submit released the items) | notice "n items need your answer"; only the flagged items with the officer's comment; response and attachments per item; Send responses disabled until every item is answered | Awaiting Post-Site Clarification / Pending Post-Site Clarification |
| 4 | Round sent by the operator | rail header "Round 1, your turn"; items Answered with the response and attachments in the thread; per item Mark clarified or Still needs clarification; Withdraw on open items | page read-only; status bar "The licensing officer is reviewing your responses" | Post-Site Clarification Resubmitted / Post-Site Resubmitted |
| 5 | Officer asks again | reopened items say "Not sent yet" until Request another round; Route to approval disabled while anything is open or answered | nothing changes until the round is requested | same |
| 6 | Another round requested | rail header "Round 2, waiting on operator"; the new requests released | notice "n items need your answer" (only the reopened items); history shows round 1 | Awaiting Post-Site Resubmission / Pending Post-Site Resubmission |
| 7 | Everything clarified or withdrawn | Route to approval enabled; Reject always available with a note | history shows every round as Clarified | Route to Approval / Pending Approval |
| 8 | Reject or Withdraw mid-round | threads frozen as they are; an unsent operator draft shows "Draft, never sent" | outcome panel; history shows "Draft, never sent" on the unsent round | Rejected / Withdrawn |
| 9 | Return to review, second visit | a new checklist, Visit 2, from step 1; Visit 1 stays readable | history lists Visit 1 and Visit 2 | Site Visit Scheduled again |

Item states in the rail and the history: Open (amber), Answered (blue), Clarified (green), Withdrawn (grey), each a badge with a dot; the finding's result is a grey tag ("Result: Unsatisfactory"), never a badge, because it is a fact, not a state.

## Partial failure

- Upload succeeded but verification `failed` / `unavailable`: card shows the state and re-run; nothing else changes. An `unavailable` run with reason `daily_limit_reached` (US-058 quota) says so in operator words, offers no re-run for the day, and the officer's check panel names the limit.
- Resubmit succeeded but notification delivery (mock email) failed: no user-visible effect (in-app notification is in the same transaction).
- One of several polled cards errors: only that block shows the error; others keep updating.
