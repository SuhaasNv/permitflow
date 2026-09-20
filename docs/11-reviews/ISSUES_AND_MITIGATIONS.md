# Issues found and how they were mitigated

One place for the question "what went wrong, and what did you do about it". Grouped by kind, each with where it was found, what the risk was, the mitigation, and where the evidence lives. The detailed review records are `EDGE_CASE_REVIEW.md` (47 items, 31 fixed and 16 deferred, Sprint 2), `LAYOUT_AUDIT.md` (Sprint 3), `BUG_HUNT_REVIEW.md` (39 items plus R1 to R12, Sprint 3) and `docs/07-ai/AI_EVALUATION.md`. Every item was fixed with a regression test where a test could capture it, or kept as a documented decision.

## 1. Workflow and data integrity

| Issue | Found by | Risk | Mitigation | Evidence |
|-------|----------|------|------------|----------|
| Officer queue showed the operator's working copy (`draft_data`) for the business name and address, so a row could carry an unsubmitted value during a resubmission round while the case page showed the submitted one | Final check (20 Sep), first kept as a decision; fixed after the cold repository review the same day (US-076) | An officer reads applicant data the applicant has not submitted; on a licensing platform that is the wrong side of a line even at this severity | `RevisionRepository.latest_for` (one `DISTINCT ON` query) feeds the queue; `draft_data` is used only when no revision exists | `tests/integration/test_officer_queue.py::test_queue_shows_the_submitted_form_not_the_working_copy` |
| Draft quota counted without a row lock: two simultaneous creates at 19 of 20 could both pass | Final check (20 Sep), fixed 20 Sep (US-076) | One extra draft over the ceiling per race; bounded | `UserRepository.lock` takes `SELECT ... FOR UPDATE` on the operator's user row before the count, so the count and the insert are serialised per operator | `tests/integration/test_abuse_limits.py::test_draft_quota_holds_the_operator_row_lock_until_the_transaction_ends` |
| Three services issued SQLAlchemy statements directly instead of through a repository (`LicenceService`, `DraftDeletionService`, the verification task), and the layering test could not see it | Final check (20 Sep), fixed 20 Sep (US-076) | Layering claimed in `ARCHITECTURE.md` but not enforced on that edge | `LicenceRepository`; `DocumentRepository.purge_for_application`, `claim_run`, `fail_interrupted_runs`; `test_services_use_sqlalchemy_only_for_the_session` fails on any SQLAlchemy name other than `Session` imported under `services/` | `tests/unit/test_layering.py` |
| Two officers (or two tabs) acting on the same application could overwrite each other's status change | Threat model T17, design phase | Lost transitions, "no applications lost" violated | Row lock (`SELECT ... FOR UPDATE`) plus an optimistic `version` sent with every transition; a stale write gets 409 `version_conflict` and the UI reloads | `services/workflow.py`, `tests/integration/test_officer_case.py` |
| Undoing a feedback resolve inside the 15 s window after the site visit was scheduled left an open item in a state that forbids it | Bug hunt B1 | State machine invariant broken by a side path | Undo allowed only while the application is still Under Review | `services/feedback.py:restorable`, test |
| A replaced document flipped the only open feedback item to Addressed, so the officer could not request another round without retyping | User run-through (US-049) | Officer stuck; workaround was manual duplication | "Not fixed" reopens the item with the same text as a draft for the next round, audited | `feedback.reopen`, `test_feedback_reopen.py` |
| Officer at Pending Approval had no way back except Reject | Second run-through | Wrong outcome forced by the state table | Return to review transition (`pending_approval → under_review`), one table row, dialog, test | `domain/workflow.py`, `test_outcome.py`, ADR-003 amendment |
| A flagged Declarations section could not be "changed" (checkboxes already true), so the operator could never resubmit | User run-through (US-045 follow-up) | Dead end in the resubmission loop | Re-confirmation stamps `confirmed_at`; the diff reports "Confirmed on" and counts it as the change | `domain/diff.py`, `STAMPED_FIELDS` |
| A second "request resubmission" wrote an empty `feedback.released` audit row | Bug hunt B8 | Audit noise, misleading trail | Audit only when something was released | test |
| Restart with a `pending` verification run left the document "checking" forever and blocked re-run with 409 | Bug hunt B3 | Stuck document, no recovery | Every pending or stale running run is marked `failed: interrupted` at startup; re-run allowed | `services/verification.py`, test |
| Licence number used the UTC year while the printed dates are Singapore dates | Final bug hunt R6 | Wrong year on New Year's morning | Year taken from the Singapore date; test | `services/licence.py` |

## 2. Authorization and security

| Issue | Found by | Risk | Mitigation | Evidence |
|-------|----------|------|------------|----------|
| Operator could guess another operator's application id | Threat model T1 | Horizontal escalation | Every operator-scoped load filters by owner and answers 404 (no existence leak); officer routers gated by role dependency; sub-resource ids checked against the parent | `repositories/applications.py`, 22 × 403 and 15 × 404 assertions across the integration suite |
| Internal status codes reaching operators | Brief, T3 | Operators see the approval stage | Separate operator response models with labels only; officer-only labels never serialised for operators; decision note only with the final outcome | `services/operator_view.py`, `test_officer_case.py`, `test_labels.py` |
| Uploaded file type spoofing | Threat model T4 | Executable or wrong content stored and served | Allowlist by extension and declared type, 10 MB cap with a `Content-Length` pre-check, magic-byte sniff, server-generated keys, download only through authorised endpoints | `domain/uploads.py`, `test_uploads.py` |
| Valid UTF-8 `.txt` rejected when the 16th byte fell inside a multibyte character | Bug hunt B2 | False upload rejection | Sniff tolerates a character cut at the sample boundary | test |
| Prompt injection inside a document steering the verifier | Threat model T5, AI-004 | Officer misled by the model | Deterministic regex heuristic before the verdict is read forces `needs_review` and adds a finding; prompt frames document text as untrusted; strict wire and domain schemas; the model never touches state | `domain/verification_rules.py`, `test_verification_rules.py`, eval cases `injection_*` |
| Officer re-run of a check on another operator's document, operator re-run after submission | Bug hunt B4 | Rolling a non-deterministic provider until it "passes" | Operator re-run only while the slot is editable; officer re-run audited | `services/verification.py` |
| The upload size gate ran after FastAPI had parsed and spooled the multipart body, so a 500 MB body was received before the 400 | Final check, backend review (Medium, US-075) | Disk and time spent on a body the docs said was refused first | Content-Length check moved to a middleware inside CORS; the streaming cap stays as the second line; T4 reworded | `main.py`, `test_abuse_limits.py` |
| Quota refusals were counted toward the daily verification quota, so a refused attempt extended the applicant's lock-out by another day and ate the platform allowance | Final check, backend review (Medium, US-075) | Applicant locked out for as long as they kept trying | Refused runs excluded from the count | `repositories/documents.py`, `quotas.py`, test |
| The verification task held its pooled database connection through the file read and the model call | Final check, backend review (Medium, US-075) | A burst of slow checks could park every connection and starve the API | The task commits after loading its rows and reconnects only to write the result | `services/verification.py` |
| Operators received provider and infrastructure reason codes on a failed check | Final check, backend review (Low, US-075) | Configuration detail leaked to the public side | Collapsed to `unavailable` for operators; file reasons and the daily limit pass through; officers keep the code | `services/operator_view.py`, test |
| Rate limiter behind a proxy saw one IP | Sprint 2 review | Limiter useless or global | `TRUSTED_PROXIES` with `X-Forwarded-For` handling (`*` on Railway) | `core/rate_limit.py`, test |
| Previous account's cached data visible after sign-out on a shared browser | Bug hunt | Data leak between users | Query cache cleared on sign-out and on 401 | `AuthContext.tsx`, test |
| Secrets in the repository | Brief | Credential leak | gitleaks over full history in CI; `.env` ignored; every variable documented in `.env.example`; Railway tokens created in the dashboard and set as GitHub environment secrets without ever appearing in a transcript | `ci.yml`, `OPERATIONS.md` |
| Licence certificate leaked, forged or issued twice | Threat model T20 | Wrong party downloads, duplicate issue | Owner-or-officer download, 404 before approval, unique row per application, sequence-backed number, sha256 recorded, watermarked in-memory preview | `test_licence.py` |

## 3. AI verifier (product)

| Issue | Found by | Risk | Mitigation | Evidence |
|-------|----------|------|------------|----------|
| First live run: the model invented enum values (`status: rejected`, `severity: error`) | Live run, US-002 | Every answer rejected as malformed | Enums pinned in the OpenAI strict schema and listed in the prompt; domain model re-validates with bounds | `openai_provider.py`, `test_openai_wire.py` |
| Expired certificate reported as valid | Live run | Wrong verdict | Today's date passed in the user message | `AI_VERIFICATION_DESIGN.md` |
| Verbose but valid answer failed strict length limits and became `failed` | Bug hunt B9 | Lost result | Wire strings trimmed to domain limits before validation | test |
| Model could answer `verified` with issues listed, or `issues_found` with none | Checks audit R5 | Counters disagree with the list beneath | Domain validator settles status from the issue list | `verification_rules.py`, test |
| The demo documents' "fictional document" footer reported as a possible injection | Second run-through | False MEDIUM finding on every demo | Prompt 2026-09-19.3 defines an injection as text that tries to direct the model and excludes template disclaimers; two wordings rejected by the harness first | `AI_EVALUATION.md` |
| Confidence self-reported and uncalibrated (95 % almost always) | Run-through question | Officer over-trusts a number | Used only for the "verified below 0.6 becomes needs review" rule; documented as a limitation; calibration in "what next" | `AI_EVALUATION.md`, README |
| Re-run result on an older document never displayed (staleness measured from upload time) | Bug hunt F1 (High) | Officer sees a stale verdict | View carries `requested_at` per run; staleness and polling keyed on it | `operator_view.py`, test |
| Provider outage or missing key | Design | Uploads blocked | `unavailable` run with reason; upload and submission succeed; re-run later | `test_verification.py` |

## 4. Officer and operator experience

| Issue | Found by | Risk | Mitigation | Evidence |
|-------|----------|------|------------|----------|
| 401 mid-session left every page in an error loop | Edge review 1 (High) | Unusable app after expiry | One unauthorized handler ends the session; sign-in explains; return path honoured inside the role's area | `api/client.ts`, test |
| Refresh or tab close lost unsaved section input silently | Edge review 2 (High) | Data loss | `beforeunload` prompt while dirty; in-app "Leave without saving?" | `lib/unsaved.ts`, test |
| Resubmit or Withdraw after a decision showed the raw internal message | Bug hunt F2 (High) | Internal code leaked, stale page | 409 shows a plain message and reloads | test |
| Save and continue landed on a locked section during a resubmission | User screenshot (US-041) | Operator lost | Respond mode walks only flagged targets and leads to Resubmit; flagged markers in rail and stepper | `respond.ts`, tests, scenario 03 |
| Officer case unreadable on a phone; navigation landed mid-page | User screenshots (US-037) | Unusable on mobile | Layout fixes at 390; scroll restoration | `LAYOUT_AUDIT.md` |
| Licence download hidden when the officer approved without a note | First run-through R1 (High) | Operator cannot get the certificate | Outcome panel keyed on licence or note, not note alone; unit test | `ApplicationPage.tsx` |
| Queue and case disagreed on unreadable and failed checks; "Analysed" counted unchecked documents | Checks audit R3, R4 | Officer misreads the summary | Same attention set on both; labels corrected; mixed-case test | `officer_queue.py`, `test_verification_summary.py` |
| Approval possible while checks were unresolved with no warning | Second run-through | Officer misses findings | Approve dialog warns with the count; approval stays allowed (advisory principle) | `CasePage.tsx`, test |
| "Session expires tomorrow at 7:53" in the top bar all day | User walkthrough (US-048) | Noise, questions | Warning only in the last 30 minutes | `lib/session.ts` |
| A failed background poll (a 429 from the limiter, a network blip while a check was polling) replaced the whole page with the error panel and dropped unsaved form text | Final check, frontend review (High, US-075) | Data loss while typing; the panel even said nothing was lost | The error panel is shown only when there is no data (`isError && data === undefined`); a failed refetch keeps the cached view until the next poll succeeds, on every operator page and the officer case | `FormPage.tsx` and six siblings, `FormPage.test.tsx` (types while a poll fails) |
| A check stuck past the three-minute window never showed "taking longer than expected" or Re-run until the operator navigated away; the officer case page polled forever with no Re-run | Final check, frontend review (Medium, US-075) | Operator and officer stuck on "Checking" | The slot wakes itself when the window closes; the officer view carries `requested_at`, stops polling after the window and offers Re-run | `DocumentSlot.tsx`, `officer/queries.ts`, tests |

## 5. Delivery pipeline and operations

| Issue | Found by | Risk | Mitigation | Evidence |
|-------|----------|------|------------|----------|
| Deploy health gate tested the old container (`railway redeploy` returns before the rollout) | Bug hunt S1 (High) | Green deploy of a broken image | Job polls the new deployment until SUCCESS (fails on FAILED, CRASHED, REMOVED), then health and `config.js` gates | `deploy.yml`, ADR-011 |
| A green CI on a weekend could change production | Product decision | Unreviewed production change | GitHub `production` environment with a required reviewer, `main` only | `deploy.yml`, repository settings |
| Unhandled exception escaped the CORS layer; browser reported "server unreachable" | Layout audit backend note (US-044) | Misleading error | Error middleware inside CORS, request id in the envelope, 503 on pool timeout | `main.py`, test |
| Remote CI failed twice on `ruff` line length not run locally | CI | Red pipeline | Pre-commit routine tightened (ruff, format, mypy, tsc before every commit) | commit history |
| E2E under `vite preview` on a different port hit CORS | US-006 | Flaky E2E | CI serves the preview on :3000 (the allowed origin) | `ci.yml` |
| Subagent scratch file swept into a commit by `git add -A` | Review pass | Junk in history | Removed and recommitted; explicit staging since | `AI_USAGE.md` |
| Sprint dates in docs disagreed with the git history | Consistency pass | Reviewer distrust | Dates aligned with `git log`; planned versus executed stated in `DELIVERY_PLAN.md` | `SPRINTS.md`, `CHANGELOG.md` |
| Production hosts published but not deployed | Independent review | Dead links | Production state and the reason stated in `OPERATIONS.md` and README; first deploy at v0.3.0 behind the approval gate | `OPERATIONS.md` |

## 6. Kept as decisions (not changed)

| Item | Why it stays |
|------|--------------|
| Officer case lists an unsubmitted replacement document with `in_current_revision=false` while a round is open (B5) | That is what the flag is for: the officer sees what is coming without it counting as submitted |
| Operator sees the label "Pending Approval" (brief's own table) while never seeing internal codes (SCOPE assumption 17) | Follows the table and the spirit of the criteria |
| Approval is not blocked by unresolved AI findings | AI is advisory (AI-005); the dialog warns instead |
| Low confidence only escalates a `verified` answer, never `issues_found` | An issue is an issue regardless of confidence; documented |
| Live OpenAI evaluation is not a CI gate | Non-deterministic and paid; run by hand on every prompt change and recorded |
| Final-check findings kept as they are: undo of "Not fixed" resets the release time, `Retry-After` not surfaced | Each is cosmetic or self-healing on the next action; listed with the production fix in `PRODUCTION_READINESS_REVIEW.md` row 23. Three findings first kept in this row (the queue reading the working copy, B6 above; the draft quota counted without a lock; services issuing SQL directly) were fixed on 20 Sep after a cold review of the repository rated them as the one shipped defect worth fixing (US-076): see section 1 |

## 7. How the final check was run (US-075)

The findings above marked "Final check" came from one overnight session on the eve of submission, prompted with: "Do one last review of the whole code base for me and all the docs and everything from top to bottom, as I will be submitting in the morning. Do any fixes and verify everything again. Don't push to dev. Do some UAT cases and make sure no edge cases are being missed." The method: every suite from a cold clone; three read-only reviewers with separate briefs (backend correctness and authorization, frontend behaviour and copy rules, every document against the code), each finding verified in the code before it was acted on; an API-level edge-case driver of 166 checks (`backend/scripts/uat_edges.py`) run against the local stack; fixes with a regression test each; everything re-run; the work on `feat/us-075-final-check`, unmerged for the owner to read. The full prompts and what came of them: `AI_USAGE.md`, "Final check before submission".
