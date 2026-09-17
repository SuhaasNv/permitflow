# ADR-007: Immutable revision snapshots with read-time diff and feedback targeting

## Context
The assessment requires: operators update only flagged sections without re-entering the application; data is never lost between rounds; revision history and previous comments stay visible; officers see only what changed and can compare against previous versions; resolution of flagged issues is tracked; unlimited rounds.

## Constraints
- A form is small (tens of fields), so storage is not a concern; correctness and explainability are.
- Feedback must point at something stable (a section key or a document) that survives revisions.

## Options Considered

### Option A: Full snapshot per revision + working copy on the application + read-time structural diff
`applications.draft_data` is the editable working copy. `application_revisions` rows hold `form_data` (JSON snapshot), `document_ids`, `revision_number`, `submitted_at`. Diff is computed by a pure function over two snapshots. Feedback rows reference `revision_id` (raised in) and a target (`section_key` or `document_type` — the slot, which is stable across file replacements), with `resolution` state.
- Pros: immutability by construction; compare any pair; "what the officer saw" is exact; resubmission logic is "copy working copy into a new revision".
- Cons: unchanged data is duplicated per revision (negligible).

### Option B: Event-sourced field changes
- Pros: elegant history; minimal storage.
- Cons: reconstruction logic, snapshotting for reads, higher bug risk in three days; harder to explain.

### Option C: Mutable application data + change log table
- Pros: simple writes.
- Cons: the "previous version" is a reconstruction; a bug in logging silently loses history; contradicts "never lost".

## Decision
Option A. Additional rules:
- On resubmission, only sections/documents with `open` feedback may differ from the previous revision; the server rejects other changes.
- Feedback whose target changed between the previous and new revision is automatically set to `addressed`; officers set `resolved` or reopen. This is "tracked", not "auto-judged". "Changed" means the section value differs, or the current document's `sha256` differs (re-uploading the identical file does not count).
- Officers can create or withdraw feedback only while the application is `under_review`; once resubmission is requested the round's feedback set is frozen and released to the operator. This prevents the deadlock where withdrawing an item would strand an already-edited section with no open item.
- Documents are versioned by replacement: a new `documents` row supersedes the old (`supersedes_id`), so old revisions keep their original file references.

## Rationale
Snapshots make the two hardest UI requirements (targeted edit and compare) into simple, testable functions and make "never lost" a property of the schema rather than of application code.

## Consequences

### Positive
- Revision compare is deterministic and unit-tested.
- Feedback anchoring is a stable key; the UI can scroll to it in any revision.
- History views need no reconstruction.

### Negative / Tradeoffs
- Free-text fields show whole old/new values, not word diffs.
- The "only flagged sections may change" rule needs a clear error when violated; it is a product decision aligned with the brief.

## Validation
- Unit tests for the diff (added/removed/changed, nested, documents add/remove/replace).
- Integration test: three rounds produce three revisions; revision 1 bytes unchanged; feedback states move open → addressed → resolved as specified; unflagged section edit rejected with 403.
