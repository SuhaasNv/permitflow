# Issues found and how they were mitigated

One place for the question "what went wrong, and what did you do about it". Grouped by kind, each with where it was found, what the risk was, the mitigation, and where the evidence lives. The detailed review records are `EDGE_CASE_REVIEW.md` (31 items, Sprint 2), `LAYOUT_AUDIT.md` (Sprint 3), `BUG_HUNT_REVIEW.md` (45 items plus R1 to R11, Sprint 3) and `docs/07-ai/AI_EVALUATION.md`. Nothing here was hidden: every item was fixed with a regression test where a test could capture it, or kept as a documented decision.

## 1. Workflow and data integrity

| Issue | Found by | Risk | Mitigation | Evidence |
|-------|----------|------|------------|----------|
| Two officers (or two tabs) acting on the same application could overwrite each other's status change | Threat model T17, design phase | Lost transitions, "no applications lost" violated | Row lock (`SELECT ... FOR UPDATE`) plus an optimistic `version` sent with every transition; a stale write gets 409 `version_conflict` and the UI reloads | `services/workflow.py`, `tests/integration/test_transitions.py` |
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
| Rate limiter behind a proxy saw one IP | Sprint 2 review | Limiter useless or global | `TRUSTED_PROXIES` with `X-Forwarded-For` handling (`*` on Railway) | `core/ratelimit.py`, test |
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
| Queue reads the business name from the working copy, the case from the revision (B6) | The queue is a live index; the case is the record |
| Operator sees the label "Pending Approval" (brief's own table) while never seeing internal codes (SCOPE assumption 17) | Follows the table and the spirit of the criteria |
| Approval is not blocked by unresolved AI findings | AI is advisory (AI-005); the dialog warns instead |
| Low confidence only escalates a `verified` answer, never `issues_found` | An issue is an issue regardless of confidence; documented |
| Live OpenAI evaluation is not a CI gate | Non-deterministic and paid; run by hand on every prompt change and recorded |
