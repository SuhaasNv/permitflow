# Bug hunt (19 Sep 2026)

Three independent read-only reviews, run in parallel by agents with different briefs, after Sprint 3's features had landed: backend rules and races, frontend interaction, and the seams (API contract, CI/CD, Docker, docs versus code). Every finding was reproduced with a throwaway test, a Playwright script or a concrete trace before it was reported. Fixed on `fix/us-050-bug-hunt` (US-050) with regression tests where a test could capture it. Earlier reviews: `EDGE_CASE_REVIEW.md` (Sprint 2), `LAYOUT_AUDIT.md` (Sprint 3).

## Backend (4 Medium, 6 Low)

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| B1 | Medium | Undoing a resolve within the 15 s window after the officer had scheduled the site visit put an open item under `site_visit_scheduled`, a state the machine forbids | `restorable` only lets an item go back to open while Under Review; back to addressed stays allowed (test `test_bug_hunt_regressions`) |
| B2 | Medium | A valid UTF-8 `.txt` whose 16th byte fell inside a multibyte character was rejected as "content does not match its type" | The sniff tolerates a character cut at the end of the sample (test) |
| B3 | Medium | A `pending` run younger than the timeout window at restart was never marked failed, so the document showed "checking" forever and re-run answered 409 | Every `pending` run found at startup is marked `failed: interrupted`; only `running` keeps the age cutoff |
| B4 | Medium | Operators could re-run the check on their own document at any status and keep rolling a non-deterministic provider after submission | Operator re-run follows the same rule as replacing the file: only while the slot is editable (403 otherwise, test) |
| B5 | Low | Officer case listed an unsubmitted replacement document with `in_current_revision=false` while the round was open | Kept: it is the product choice the flag exists for (the officer sees what is coming), documented here |
| B6 | Low | Queue read business name from the working copy while the case read the revision | Kept and documented: the queue is a live index, the case is the record |
| B7 | Low | Officer hitting the system-only edge got 409 `kind=forbidden`, docs said 403 | STATE_MACHINE.md corrected (routers answer 403 before a wrong role can reach the table) |
| B8 | Low | A second "request resubmission" wrote `feedback.released` with no ids | Audit written only when something was released |
| B9 | Low | A verbose but valid model answer failed the strict domain limits and became `failed: provider_error` | Wire strings are trimmed to the domain limits before validation |
| B10 | Low | ARCHITECTURE API table listed endpoints that do not exist (revisions, admin) and the wrong download roles | Table corrected; admin rows marked planned |

## Frontend (2 High, 7 Medium, 7 Low)

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| F1 | High | Re-run check on a document older than 3 minutes never showed its result: staleness was measured from the upload time | The view carries `requested_at` per run; staleness and polling use it |
| F2 | High | Resubmit or Withdraw after the officer decided showed the raw internal message ("Cannot move from rejected to ...") and a stale page | A 409 shows "This application changed since you opened it" and refetches the view |
| F3 | Medium | Section save after the application was locked (403) left the form editable | 403 or 409 on save refetches the view; the form locks itself |
| F4 | Medium | Sign-out kept the previous account's cache: the next account saw the other user's notifications until the refetch | The query cache is cleared on sign-out and on 401 |
| F5 | Medium | Withdrawn applications were grouped under "With the licensing office" | Withdrawn is Decided |
| F6 | Medium | The stale-version banner survived Reload | Reload resets the mutation state |
| F7 | Medium | Readiness copy counted feedback items, not targets ("1 of 2" next to "every item changed") | Counts targets from the server's readiness |
| F8 | Medium | "Save and review" on the last section landed on Documents | Label is "Save and continue" everywhere |
| F9 | Medium | "Back to form" during a resubmission opened a locked section | The form opens the first flagged section |
| F10 | Low | Dialogs focused the wrong control (autoFocus runs before the dialog opens) | Focus set after `showModal()`: Cancel on destructive dialogs, the action otherwise |
| F11 | Low | Closing the notifications popover dropped focus on the body | Focus returns to the bell |
| F12 | Low | A decision note typed then cancelled reappeared in the next decision dialog | Cleared on cancel |
| F13 | Low | Remove-document failure left the dialog open over the error | Dialog closes; the slot shows the error |
| F14 | Low | "Try again" after a failed New application only dismissed | Inline alert with Dismiss; the button itself is the retry |
| F15 | Low | Compare panel kept the old pair after a resubmission arrived live | Panel keyed on the current revision |
| F16 | Low | Review page reachable by URL during a resubmission; breadcrumb went to the dashboard | Redirects to the application; breadcrumb and Not found links go to My applications |

## Seams (1 High, 8 Medium, 12 Low)

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| S1 | High | The deploy health gate tested the old container: `railway redeploy` returns before the rollout | The job waits for Railway to report the new deployment of each service as SUCCESS, and Railway health checks are set on both services |
| S2 | Medium | Image tags used the raw ref; on pull requests that is `12/merge`, an invalid tag | Ref sanitised |
| S3 | Medium | A mistyped or truncated application link answered 422 "validation failed" | Path validation errors answer 404 |
| S4 | Medium | OPERATIONS described CI with four jobs and "nothing deploys"; the rollback text suggested re-running the deploy workflow, which cannot roll back | Rewritten |
| S5 | Medium | ARCHITECTURE and BRANCHING said Railway builds the frontend from source and only from `main` | Corrected to the image flow |
| S6 | Medium | README said Sprint 2 and five jobs; SCOPE said React 18; ARCHITECTURE said generated OpenAPI types | Corrected |
| S7 | Medium | Root `.env.example` carried `VITE_API_URL`, which Vite never reads from the root | Pointer to `frontend/.env` |
| S8 | Low | gitleaks did not gate the image push; readiness loops exited 0 after 30 misses | Images need gitleaks; loops fail with the log tail |
| S9 | Low | `/assets/` 404s carried a one-year immutable cache header | `always` dropped on that header |
| S10 | Low | Swagger and the OpenAPI schema were public in production | Disabled when `APP_ENV=production` |
| S11 | Low | Tests and evals shipped in the backend image | Excluded by `.dockerignore` |
| S12 | Low | Stale counts and a missing link in TEST_STRATEGY; dates written as 20 Sep; a stray PNG | Corrected; image removed |
| S13 | Low | `details.fields` has two shapes (dict from services, list from request validation); the UI reads the dict | Documented here; unreachable today because client limits mirror the server's |

## Browser run-through with the demo documents (19 Sep 2026, US-051 branch)

A full operator and officer journey in Chrome with `docs/demo/documents` (clean set, then the wrong file in the floor plan slot, Not fixed, a second resubmission, site visit, preview, approval, download) after the bug-hunt batch. Two more defects, fixed on `feat/us-051-licence-certificate`:

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| R1 | High | Operator outcome panel, and with it the licence download, rendered only when the officer left a decision note; an approval without a note hid the licence | Panel renders whenever a note or a licence exists; note line optional; unit test |
| R2 | Low | Feedback group heading read "Round N · Revision N" (the same number twice), so a reopened item looked stale once the application moved on | Both sides say "Raised against Revision N" |

A follow-up read-only audit of the Document checks card (same day) confirmed the counters are per document, by the latest run only, and correct for the reading that prompted it (four documents, four `issues_found`). Three small items fixed on `fix/us-050-document-checks`, with a mixed-case test that asserts the card's buckets and the queue's "to check" count from the same facts:

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| R3 | Medium | Queue and card disagreed: `unreadable` read "Clear" in the queue while the operator was told an officer would look at it; `failed` read "to check" in the queue but neutral on the card | Queue attention set includes `unreadable`; the card's remainder row is "Not checked" in warning tone |
| R4 | Low | "Analysed" counted documents still checking or never checked | Label is "Documents" |
| R5 | Low | Provider could answer `verified` with issues listed, or `issues_found` with none; mock never does, OpenAI could | Domain model settles status from the issue list (validator + unit test) |

The certificate itself was also reworked on the same pass (real brand mark, wrapping values, signature strip pinned at the bottom, two-pass layout), recorded under US-051 in `CHANGELOG.md`.

## Not changed

B5 and B6 are product choices, recorded above. S13 is documented rather than changed. Everything else shipped with the batch; all suites were green afterwards (backend, vitest, the Playwright journey and six scenarios).
