# ADR-010: Licence certificate issued inside the approval transaction

Date: 19 September 2026. Story: US-051 (beyond the brief, product decision). Status: accepted, built.

## Context
Approval ends the workflow, but the brief's outcome is a status, not a document. A business that is granted a licence needs something it can show; an officer wants to see what will be issued before committing. The certificate must be a faithful record of the decision: one per approved application, never issued for a rejected or withdrawn one, never changed after issue, and retrievable only by the owner or the licensing office.

## Constraints
- Approval and issuance must be atomic: no approved application without a certificate, no certificate without an approval (AUD-001, ADR-008).
- The certificate is a record, not a legal instrument (fictional issuer); it must say so.
- No new infrastructure: the existing `FileStorage` and the uploads volume are the only durable file store.
- Officers must be able to preview without anything being stored.

## Options Considered

### Option A: render on approval, store the bytes, audit the issue
- Pros: the PDF is immutable and hash-recorded; download is a file read; the preview is the same renderer with a watermark flag and no storage; the audit trail shows exactly when and by whom it was issued.
- Cons: a PDF library in the backend (reportlab); storage grows by one file per approval.

### Option B: render on every download from the stored facts
- Pros: no file to store; layout changes apply retroactively.
- Cons: the document a business holds could change after issue (a later layout fix would alter an issued certificate); no hash to verify a printed copy against; every download pays the render.

### Option C: client-side rendering (browser PDF from the JSON)
- Pros: no backend change.
- Cons: two renderers to keep identical (preview and issued), the operator's browser decides what the certificate says, nothing auditable.

## Decision
Option A. `LicenceService.issue()` is called by `WorkflowService.transition()` inside the approval transaction: it draws the next value of `licence_no_seq` (`FEL-<year>-<n>`, the year being the Singapore date's year), builds `LicenceData` from the approved revision, renders the PDF with reportlab, writes it under `<application_id>/licence-<no>.pdf`, inserts the `licences` row (unique per application) with the `sha256`, and records `licence.issued`; if any step fails the whole transition rolls back. Validity is one year in Singapore calendar dates. The preview endpoint (officers, `pending_approval` only) renders in memory with a "PREVIEW, NOT ISSUED" watermark and a placeholder number. Download is owner-or-officer, 404 before approval, never a direct file URL.

## Rationale
The certificate is part of the decision, so it lives where the decision lives: same transaction, same audit trail, same storage rules as the evidence it summarises. The hash lets an officer match a printed copy to the record without trusting the paper.

## Consequences

### Positive
- One code path produces both the preview and the issued document; what the officer saw is what was issued.
- Rollback safety: a storage failure leaves the application unapproved rather than approved without a certificate.

### Negative / Tradeoffs
- A commit failure after the file write leaves an orphan file and a gap in the sequence; harmless, noted in `docs/11-reviews/BUG_HUNT_REVIEW.md`.
- Base-14 fonts only: non-Latin business names render as boxes (`SCOPE.md`, known limitation).
- No digital signature or public verification page (production gap T20 in the threat model).

## Validation
- `tests/integration/test_licence.py`: preview 409 outside pending approval, officer-only preview, licence issued on approve, owner and officer download, 404 before approval, admin 403, nothing issued on reject, Singapore-year licence number.
- `tests/unit/test_licence_render.py`: every fact present as text, watermark on preview only, deterministic bytes, long values clipped.
- Playwright journey: preview page, approve, both downloads, audit line.
