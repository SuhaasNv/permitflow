# Edge-case review (Sprint 2, 18 Sep 2026)

Three independent devil's-advocate reviews were run against the Sprint 1 code: the operator journey (frontend), the backend and workflow, and the product and UX gaps against the requirements. Each returned up to 20 findings ranked by impact. This file records every finding, what was done about it and where, so a reviewer can see the near-misses as well as the fixes. Items marked "later" carry the sprint in which they are planned or the reason they are deferred.

Stories: US-033 (operator, items 1 to 16) and US-034 (system, items 17 to 31) in `docs/05-planning/USER_STORIES.md` and on the Notion board. Branches: `fix/us-033-operator-edge-cases`, `fix/us-034-backend-edge-cases`. The two merge commits on `dev` carry the branches' working names (`fix/operator-edge-cases`, `fix/backend-edge-cases`); the pushed branch refs use the story names above. Verification: `backend/tests/integration/test_edge_cases.py`, `frontend/src/lib/unsaved.test.ts`, `frontend/src/features/operator/queries.test.ts`, plus the existing suites.

## Fixed now

| # | Finding | Impact | Fix |
|---|---------|--------|-----|
| 1 | A 401 mid-session (token expiry, deactivated user) left every page in an error loop | High | One `setUnauthorizedHandler` in the API client and the upload XHR ends the session; the sign-in page explains "Your session ended" and honours the return path only inside the role's own area; the token expiry signs the user out proactively (`AuthContext.tsx`) |
| 2 | Refresh or tab close with unsaved section input lost it silently | High | `lib/unsaved.ts`: `beforeunload` prompt while a section is dirty; in-app navigation keeps the "Leave without saving?" dialog |
| 3 | "Save and exit" did not save; Sign out bypassed the unsaved-changes dialog | High | `SectionForm` exposes `saveDraft()`; "Save and exit" saves the partial draft first; the shell asks "Sign out without saving?" when a form is dirty |
| 4 | A network blip on reload wiped a valid session; blank page while restoring | Medium | Only a 401 or 403 from `/auth/me` signs out; a skeleton renders while the session is restored |
| 5 | Submit could double-fire; a 409 from another tab showed a generic error | Medium | `isPending` guard; 409 explains "already submitted" and refreshes the view; navigation to the confirmation page uses `replace` |
| 6 | Back after submit showed "Not ready yet"; `/submitted` rendered for a draft | Medium | Review redirects when the application is not editable; the confirmation page redirects when there is no revision; "Submitted" date label corrected to "Last updated" |
| 7 | Verification polling had no ceiling and ran in hidden tabs; a stuck check trapped the user | Medium | Polling stops after 3 minutes and only in the visible tab; the block says "taking longer than expected" and offers Re-run; refetch on window focus |
| 8 | Another tab's save silently wiped local typing | Medium | A dirty section is never reset by incoming data; a warning offers "Discard my edits" |
| 9 | Download failures were swallowed; object URL revoked too early | Medium | Errors surface as a toast; revoke after 1.5 s; missing file is a 404 with plain copy |
| 10 | Replace file allowed while a check was running; Re-run allowed on locked applications | Medium | Replace hidden while a check runs (unless stale); Re-run requires an editable slot |
| 11 | Submit with a check still running was silent | Medium | Review page lists checks still running and says the officer will see the result |
| 12 | Locked or decided applications showed editing chrome; delete gated on a display label | Medium | Documents page gates actions on `can_edit`; delete allowed only before the first revision |
| 13 | Confirmation dialogs focused the destructive button; Escape closed a busy dialog; duplicate ids | Medium | Danger dialogs focus Cancel; `aria-describedby`; Escape ignored while busy; `useId` |
| 14 | Copy promised "10 working days" and "by email" with no requirement behind either | High | Removed; the outcome "appears in your workspace" |
| 15 | Multiple files dropped were silently truncated; drag highlight flickered | Low | "One file per document" toast; drag-leave ignores child elements |
| 16 | "Replace file" had no visible keyboard focus | Medium | Focus ring on the label |
| 17 | Login limiter keyed on client-controlled `X-Forwarded-For` | High | Header honoured only when the socket address is in `TRUSTED_PROXIES` (new setting) |
| 18 | A successful login reset the failure window for its IP | High | No reset on success; the window expires naturally |
| 19 | "Streamed 10 MB cap" ran after the multipart body was buffered | High | `Content-Length` checked in a dependency before the body is read; the streamed cap stays as the second line |
| 20 | Runs left `pending` by a restart were stuck forever and blocked re-run | High | Startup marks old `pending` runs `failed: interrupted` as well as `running` ones; the claim from pending to running is an atomic `UPDATE ... WHERE status = 'pending'` |
| 21 | Download 500 on any non-Latin-1 file name | High | RFC 5987 `filename*=UTF-8''...` with an ASCII fallback |
| 22 | Rejected uploads left `.part` files on disk | Medium | Partial file unlinked on any failure |
| 23 | `NaN` or `Infinity` in a number field bypassed validation and would 500 on commit | Medium | `math.isfinite` check, 422 |
| 24 | Injection phrases were dropped when the model declared the document unreadable | Medium | Injection branch runs first |
| 25 | Raw exception text stored as `error_reason` and served to operators | Medium | Fixed vocabulary (`provider_unavailable`, `provider_error`, `storage_error`, `internal_error`); detail goes to the log |
| 26 | Re-run had no lock and no audit event; section saves were not audited | Medium | Re-run takes the application row lock and writes `verification.requested`; section saves write `section.updated` with field names only |
| 27 | Mock email "sent" inside the transaction, before commit | Medium | Notifications are queued and flushed after the commit |
| 28 | Operator list was 3N+1 queries | Medium | Two batched queries |
| 29 | Admin could download any submitted document while being denied the list | Low | Download is operator or officer only until the admin oversight story (US-072) grants read access explicitly |
| 30 | Login timing oracle (unknown email answered faster) | Low | A dummy hash is verified when the email is unknown |
| 31 | Queue "all caught up" could mislead | Low | Filtered-empty copy distinguishes "nothing waiting for you" from "nothing submitted"; the three counts stay visible in the subtitle |

## Later (planned or deferred, with the reason)

| # | Finding | Plan |
|---|---------|------|
| L1 | Lost update on section save: `version` incremented but never checked | Sprint 2, US-018: `If-Match` / `version` on section PATCH with `409 version_conflict`, which the resubmission flow needs anyway |
| L2 | Verification result silently stale after the form changes | Sprint 2, US-022: store a hash of the compared form section on the run and serve `stale` to officers; operators get "form changed since this check" copy |
| L3 | Verification runs in the shared thread pool; a slow provider can starve API requests | Sprint 3: dedicated bounded executor; documented in SCOPE as the queue-ready seam |
| L4 | Officer queue is unpaginated and loads every run row | Sprint 2, US-020 follow-up when the queue grows: `DISTINCT ON (document_id)` and paging; not a problem at assessment scale |
| L5 | No token revocation on role or password change | Sprint 3 with US-073: `token_version` column checked on every request |
| L6 | Officer rejects while the operator is mid-resubmission: working-copy handling undefined | Sprint 2, US-025 and US-018: state-machine side-effects row and a "This application changed: reload" banner on 403/409 during save |
| L7 | Non-flagged section correction has no UI path | Sprint 2, US-018: read-only reason copy ("the officer did not ask for changes here") and a note-to-officer field on resubmit |
| L8 | Operator has no notification surface (FR-020 satisfied only by a database row) | Sprint 2: US-025 adds the operator notification list and unread count in the shell (S-17) |
| L9 | Officer at a site visit on a phone | Sprint 2, US-031: the site-visit actions work at 390 px |
| L10 | Time zone unstated (browser-local rendering) | Sprint 3 docs: NFR line "store UTC, render Asia/Singapore, year shown outside the current year"; `format.ts` gains the year rule |
| L11 | Per-tab sessions (`sessionStorage`): new-tab links land on sign-in; sign-out does not propagate | Documented trade-off in UC0-A (shared-desk safety over convenience); `BroadcastChannel` sign-out if time allows |
| L12 | Admin credential provisioning enables officer impersonation | Sprint 3, US-073 and THREAT_MODEL T19: one-time set-password link, forced change on first sign-in, role change blocked while the user owns non-terminal applications |
| L13 | Queue filter tabs use `role="tab"` without arrow-key handling | Sprint 3 polish: button group with `aria-pressed` |
| L14 | Very long file names in toasts and dialogs | Sprint 3 polish: `shortName()` helper |
| L15 | Enter in a text input triggers "Save and continue" | Kept: standard form behaviour; complete-mode validation blocks navigation when fields are missing |
| L16 | Dashboard grouping keyed on `status_tone` | Sprint 2, US-025: the serializer sends `needs_operator_action` explicitly |
