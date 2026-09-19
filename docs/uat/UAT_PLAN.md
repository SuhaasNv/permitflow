# User acceptance test plan and record

Acceptance scenarios for PermitFlow, run by a person in a browser against a deployed environment, with the result recorded. The automated form of every scenario is `frontend/e2e/scenarios/01..06-*.spec.ts` plus `journey.spec.ts`; the manual pass exists to see what the tests cannot (wording, layout, the feel of the loop) and to run on the deployed URL.

## Environments and accounts

| | Development | Production |
|---|---|---|
| URL | https://dev.permitflow.space (Railway host https://frontend-development-afe2.up.railway.app) | https://permitflow.space (live since v0.3.0, 19 Sep 2026) |
| AI provider | OpenAI `gpt-4.1-mini` | same |
| Accounts | operator@permitflow.example.sg (Tan Wei Ling), officer@permitflow.example.sg (Rahim bin Abdullah); password `PermitFlow!2026` (the `SEED_PASSWORD` default, public by design for the demonstration) | same, seeded once on 19 Sep 2026 |
| Documents | `docs/demo/documents/clean/*.pdf` (all match the form) and `with_issues/*.pdf` (UEN off by one, unit transposed, expired certificate) | same |

## Scenarios

| # | Scenario | Steps | Expected | Automated by |
|---|----------|-------|----------|--------------|
| U1 | Apply with checked uploads | Operator: New application, fill four sections, upload four documents, watch each check, submit | Sections autosave with inline validation; each upload shows Queued, Checking, then Verified or N issues; completion reaches 100 %; submit records Revision 1; "Application submitted" page | 01, journey |
| U2 | Reaches the officer | Officer: queue shows the new case on top with "to check" count; open, Start review | Both sides notified; case shows sections, documents with findings, summary card; status Under Review for the officer, "Under Review" for the operator | 02 |
| U3 | Officer flags | Officer: add feedback on a document (template) and a section (free text), withdraw one and undo, Request resubmission | Draft items say "Draft, not sent yet"; Undo works for 10 s; after the request the operator sees Pending Pre-Site Resubmission with the items on top and only the flagged parts editable | 03 |
| U4 | Two rounds | Operator: replace the flagged document, resubmit; officer: Not fixed, request again; operator fixes, resubmits; officer resolves, compares revisions | Revision 2 and 3 recorded; "Addressed in Revision N"; Compare shows the replacement; Mark resolved; site visit scheduled and done; Route to approval | 04 |
| U5 | Approve with licence | Officer: Preview licence, Approve (with and without a note) | Preview is watermarked; approval issues FEL-YYYY-NNNNNN; officer downloads from the case; audit shows "Licence ... issued"; operator sees the outcome panel with Download licence (PDF), with or without a note | journey |
| U6 | Withdraw | Operator withdraws with a reason from any post-submission state | Withdrawn is terminal; officer sees the reason; audit shows the operator as actor | 05 |
| U7 | Reject | Officer rejects with a required note | Operator sees Rejected and the note; nothing further possible | 06 |
| U8 | Return to review | Officer at Route to Approval clicks Return to review | Under Review again; feedback and resubmission available; operator told | `test_outcome.py` (API), manual |
| U9 | Approve warning | Officer approves while a document still has issues | Dialog warns with the count; Approve stays enabled | `CasePage.test.tsx`, manual |
| U10 | Phone and tablet | Repeat U1 and U2 at 390 and 1024 wide | No horizontal scroll; bottom tab bar on the phone; navigation opens at the top | `LAYOUT_AUDIT.md` |
| U11 | Wrong role and wrong owner | Operator opens an officer URL; operator B opens operator A's application | "Not available for your role"; Not found | authorization tests |
| U12 | Session end | Sign in, wait past expiry (or clear the token), act | Sign-in page says the session ended; return path honoured | `AuthContext` tests |

## Record

| Date | Environment | Version | Scenarios | Result | Notes |
|------|-------------|---------|-----------|--------|-------|
| 19 Sep 2026 | Local (OpenAI live) | dev at `f404ddf` | U1 to U5, U8 (first persona run-through with the clean set, then the wrong file in the floor plan slot) | Pass with two findings | R1 licence download hidden without a note; R2 feedback heading. Both fixed the same day (`BUG_HUNT_REVIEW.md`) |
| 19 Sep 2026 | Local (OpenAI live) | dev at `cf40e89` | U1 to U4, U7, U9 (second run-through with the planted-issue set; application rejected at approval because a document still carried a mismatch) | Pass with one gap | No way back from Pending Approval: became U8 (Return to review) and the approve warning (U9), both shipped |
| 19 Sep 2026 | Development (Railway) | dev at `7231fc6` | U2 (scenario 02 spec against the live URLs), health gates | Pass | Recorded in `OPERATIONS.md` "Verified" |
| 19 Sep 2026 | CI (full stack in the job) | every merge to `dev` | journey + 01 to 06 | Pass | Playwright report attached on failure only |
| 19 Sep 2026 | Development on the domain | dev at `8d75c31` | U2 (scenario 02 against https://dev.permitflow.space), health gates in deploy run #6 | Pass | US-052 |
| 19 Sep 2026 | Development on the domain, full persona run (below) | dev at `8d75c31` | U1 to U5, U8, U11, plus undo, notifications, history, compare, audit | 26 of 26 steps pass; one Low finding (R12, fixed) | Sprint 3 acceptance before the release |
| 19 Sep 2026 | CI (full stack in the job) | every merge to `dev` since US-057 | a11y gate: 22 screen states at desktop and 390 px, keyboard sign-in, skip link | Pass | `frontend/e2e/a11y.spec.ts` |
| not run by hand | | | U6 (withdraw) has only its automated scenario 05; U10 (phone and tablet) rests on `LAYOUT_AUDIT.md` and the 390 px a11y states; U12 (session end) rests on the `AuthContext` tests. Stated so a reader does not assume a manual pass | | |
| 19 Sep 2026, 17:15 SGT | Production (https://permitflow.space, API https://api.permitflow.space) | v0.3.0 (`38df991`, images `v0.3.0`) | U1 (apply through the API with the four clean demo PDFs, live OpenAI checks all `verified`, submit as PF-2026-001000), U2 (queue shows the case, Start review), U5 (site visit steps, Route to Approval, Approve with a note, licence FEL-2026-000001 issued and downloaded by the operator, preview 409 after approval), U11 (audit trail: 21 events ending in `licence.issued`), U10 (sign-in, queue and case at 1280 and 390 in headless Chromium: no horizontal overflow, fonts served from the origin, `v0.3.0` in the rail, zero console errors); headers on both tiers (CSP, HSTS, Permissions-Policy), `/api/docs` 404 | Pass | First production deployment; seeded once after the deploy. Afterwards the database was reset (schema down and up, reseeded) and one example application created for a second business, Serangoon Spice House Pte. Ltd. (`docs/demo/documents/second_business`), submitted with all four checks verified, left in Application Received for the officer's queue. The first upload of that set had three particulars the checker caught (phone, upper-case address, unit); the set was corrected and the documents replaced |

## Run 3 record, step by step (Sprint 3 acceptance)

Environment: https://dev.permitflow.space, API https://api.dev.permitflow.space, OpenAI gpt-4.1-mini, prompt 2026-09-19.3. Application PF-2026-001002.

| Step | Persona | Action | Observed | Result |
|------|---------|--------|----------|--------|
| 1 | Operator | Sign in on the domain | Dashboard with 2 earlier applications (scenario runs), bell 2 unread | Pass |
| 2 | Operator | New application | Draft PF-2026-001002 created, four sections Not started, 0 of 4 documents | Pass |
| 3 | Operator | Business, Premises, Operations, Declarations, Save and continue each | Each section marked complete in the stepper; stepper moved to the next step | Pass |
| 4 | Operator | Upload clean business profile, floor plan, tenancy; expired certificate | Three Verified within about 10 s; certificate "2 issues to check": expired 3 Jan 2025 (HIGH), personal certificate note (LOW). No false injection finding on the demo footer | Pass |
| 5 | Operator | Review and submit, confirm | "Application submitted", Revision 1, status Submitted | Pass |
| note | | Model text says "today's date 18 September 2026" (UTC date in the prompt; SGT is 19 Sep) | Low, fix: Singapore date in the prompt | Finding R12 |
| 6 | Officer | Sign in | Queue: PF-2026-001002 on top, Application Received, "1 to check", bell 3 unread | Pass |
| note | | Queue "Submitted 18 Sep 2026" on an older row was first read as a mismatch; checked against the page text and the API: rows submitted before midnight SGT read 18 Sep, later ones 19 Sep. Not a defect | Withdrawn |
| 7 | Officer | Start review (dialog) | Under Review; case shows Documents 4, Verified 3, Issues found 1 | Pass |
| 8 | Officer | Add feedback with the "certificate expired" template | Item on Food hygiene certificate, "Draft, not sent yet", 1 open | Pass |
| 9 | Officer | Withdraw the item, then Undo from the toast | "Feedback withdrawn" toast with Undo; after Undo "Undone. The item is back where it was", item Open again | Pass (US-039) |
| 10 | Officer | Request resubmission (dialog) | Pending Pre-Site Resubmission; item "Sent to the operator"; panel says feedback is frozen until the operator responds | Pass |
| 11 | Officer | Open the notifications bell | Popover lists three "New application" items with Mark all as read | Pass |
| 12 | Operator | Sign in | Dashboard: "Needs your response 1" card with Respond; two others "With the licensing office" | Pass |
| 13 | Operator | Respond, then "Respond to feedback" | Landed directly on the flagged certificate slot (#slot-food_hygiene_certificate); other slots read "The licensing officer did not ask for a new copy" | Pass (US-041) |
| 14 | Operator | Replace file with the clean certificate | Checking, then Verified in about 8 s | Pass |
| 15 | Operator | Go to resubmit; Resubmit (dialog) | "Ready to resubmit: 1 of 1 flagged item changed"; "Changes resubmitted", Revision 2, Pre-Site Resubmitted | Pass |
| 16 | Operator | History page | Revisions R1 and R2 with times, "What changed from Revision 1", feedback "Changed, awaiting review", "Raised against Revision 1" | Pass |
| 17 | Officer | Sign in, open the case | Pre-Site Resubmitted, "Revision 2 resubmitted: 0 sections and 1 document changed", Verified 4 | Pass |
| 18 | Officer | Start review; Compare revisions | Under Review; compare "0 sections and 1 document changed", certificate Replaced; document badge "Replaced in Revision 2"; feedback "Addressed in Revision 2" | Pass |
| 19 | Officer | Mark resolved | Item Resolved, 0 open | Pass |
| 20 | Officer | Mark site visit scheduled, Mark site visit done, Route to approval (three dialogs) | Route to Approval; Approve, Return to review, Reject and Preview licence offered | Pass |
| 21 | Officer | Return to review (dialog) | Under Review again with the review actions; audit "Route to Approval → Under Review" | Pass (US-031 follow-up) |
| 22 | Officer | Scheduled, done, route again | Route to Approval | Pass |
| 23 | Officer | Preview licence | In-app PDF, new layout with the brand mark, "PREVIEW, NOT ISSUED" watermark, placeholder FEL-2026-000000 | Pass |
| 24 | Officer | Approve with a note | No unresolved-checks warning (all Verified, correct); Approved; rail shows Licence FEL-2026-000001, valid 19 Sep 2026 to 18 Sep 2027, code, Download licence (PDF); note shown | Pass |
| 25 | Officer | Audit trail (Show) | 37 append-only events in order incl. feedback.withdrawn, feedback.restored (undo), feedback.released, document.replaced, feedback.addressed, the Return to review status change, licence.issued, status Approved | Pass |
| 26 | Operator | Sign in, open the application | Outcome panel: "Your licence application was approved", officer's note, Download licence (PDF), "Licence FEL-2026-000001, valid 19 Sep 2026 to 18 Sep 2027"; feedback "Resolved by the officer"; API download 200 with filename FEL-2026-000001.pdf, text carries the number and business, no watermark | Pass |

Result: 26 of 26 steps pass on the deployed development environment over the custom domain, plus the role guard (an operator opening the officer queue gets "Not available for your role"). One Low finding (R12, the verifier's date line in UTC), fixed before the v0.3.0 release.
