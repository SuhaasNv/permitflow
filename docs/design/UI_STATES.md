# PermitFlow: UI states

UX-002 requires explicit loading, empty, error and success states for every data view. This document lists them per screen and specifies the two lifecycles the brief singles out: upload → verification, and feedback open → addressed → resolved.

## Global states

| State | Rendering | Notes |
|-------|-----------|-------|
| Loading (page) | skeleton in the shape of the final layout (title bar, 3–5 rows) | never a blank page or a spinner-only page |
| Loading (mutation) | button shows spinner + "Saving…", inputs stay editable-but-disabled | input never cleared |
| Empty | `EmptyState` with icon, one-line title, one-line explanation, one action | copy is specific ("No applications yet: start a new application") |
| Error (query) | `ErrorState` with request id and Retry | REL-005 |
| Error (mutation) | inline `Alert error` above the form/action + field errors; input preserved | REL-005 |
| Permission denied (403) | full-panel "Not available for your role" | UC0-A 3a |
| Not found (404) | "Application not found" with back link | SEC-002 (other operators' applications look like 404) |
| Stale version (409 `version_conflict`) | banner "This application changed since you opened it: Reload" | REL-007 |
| Invalid transition (409 `invalid_transition`) | dialog error line listing allowed actions | SEC-004 |
| Session expired (401) | redirect to login with "Your session ended: sign in again"; return path kept | SEC-006 |
| Offline / network | toast "You appear to be offline"; retries on reconnect for reads |: |

## Upload → verification lifecycle (S-12, S-15)

These are two separate stages and are shown separately: the **upload badge** in the card header and the **verification block** below it.

| # | Stage | Upload badge | Verification block | User can |
|---|-------|--------------|--------------------|----------|
| 1 | Idle slot | "Missing" (neutral) |: | drop / browse |
| 2 | Dragging over | drop zone `over` style (primary border, soft fill) "Drop to upload <file>" |: | drop |
| 3 | Client validation fails | inline error in the slot: "Word documents are not accepted. Save the file as PDF and try again." / "File is larger than 10 MB." / "Only PDF, PNG, JPG or TXT." |: | choose another file |
| 4 | Uploading | progress bar with % |: | cancel |
| 5 | Server validation fails (400: extension/MIME/magic bytes/size) | error with the server message |: | choose another file |
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
| S-00 | button spinner |: | generic "Email or password is incorrect"; 429 "Too many attempts: try again in a minute" | redirect by role |
| S-10 | strip + table skeleton | no applications | retry |: |
| S-11 | form skeleton | new draft (all sections "Not started") | save failed (input kept); 403 if not draft ("This application can no longer be edited") | "Draft saved" note; section "Complete" badge |
| S-12 | slot skeletons | all four slots empty | upload errors above; poll error → block shows "Could not refresh: retry" | see lifecycle |
| S-13 | summary skeleton |: | 422 gaps listed and linked; submit disabled until complete | → S-14 |
| S-15 | status bar + feedback skeleton | no released feedback (read-only view) | 403 non-flagged, 422 no change, 409 conflict | toast "Resubmitted"; status bar updates |
| S-16 | list skeleton | single revision ("Compare available after your first resubmission") | retry |: |
| S-20 | strip + rows skeleton | "No applications in the queue" / filtered empty | retry |: |
| S-21 | facts + sections skeleton | feedback rail empty ("No feedback yet: use Comment on a section or document") | 409 stale (reload banner), composer disabled with reason | toast per feedback action |
| S-23 | as S-21 | nothing changed (cannot happen: resubmit requires change) | as S-21 | toast on resolve |
| S-24 | table skeleton | single revision → disabled control with explanation | retry |: |
| S-25 | rows skeleton | new application (only created event) | retry |: |
| S-40 | strip skeleton | provider none → "Provider: none (mock)" | retry |: |

## Partial failure

- Upload succeeded but verification `failed` / `unavailable`: card shows the state and re-run; nothing else changes.
- Resubmit succeeded but notification delivery (mock email) failed: no user-visible effect (in-app notification is in the same transaction).
- One of several polled cards errors: only that block shows the error; others keep updating.
