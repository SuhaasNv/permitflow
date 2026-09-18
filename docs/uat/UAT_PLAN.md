# User acceptance test plan and record

Acceptance scenarios for PermitFlow, run by a person in a browser against a deployed environment, with the result recorded. The automated form of every scenario is `frontend/e2e/scenarios/01..06-*.spec.ts` plus `journey.spec.ts`; the manual pass exists to see what the tests cannot (wording, layout, the feel of the loop) and to run on the deployed URL.

## Environments and accounts

| | Development | Production |
|---|---|---|
| URL | https://dev.permitflow.space (Railway host https://frontend-development-afe2.up.railway.app) | https://permitflow.space (from v0.3.0) |
| AI provider | OpenAI `gpt-4.1-mini` | same |
| Accounts | operator@permitflow.example.sg, officer@permitflow.example.sg (password: `SEED_PASSWORD`) | same, seeded once |
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
| to run | Production | v0.3.0 | U1, U2, U5, U10, U11 on https://permitflow.space after the approval gate | | Recorded here after the release |
