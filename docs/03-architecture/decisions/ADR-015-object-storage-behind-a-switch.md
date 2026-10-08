# ADR-015: Uploads in object storage, behind a switch

Date: 9 October 2026. Story: US-097 (wave 1 of v0.5.0). Status: accepted, built behind a switch whose default is the old behaviour; the bucket itself is not yet created on Railway. Related: ADR-004 (in-process verification, replaced by US-098), ADR-010 (licence in the approval transaction), US-099 (virus scanning).

Numbering note: the build brief called this ADR-013. ADR-013 (site visit appointment) and ADR-014 (administrator) were already taken, so this is the next free number.

## Context

Uploaded files live on a Railway volume mounted into the backend service (`LocalDiskStorage` behind the `FileStorage` interface). A volume belongs to one service. The v0.5.0 plan moves the AI checks into a separate worker service (US-098) and puts a virus scanner in front of every file (US-099); both need to read the files, so the files cannot stay on the API service's disk. The volume also has no backup (readiness rows 6, 13 and 14) and a fixed size that the per-application budget (US-085) exists to protect.

## Constraints

- Authorisation must not change: downloads are streamed through the authorised API endpoint; no public bucket and no presigned URL (SEC-005, T4).
- Keys stay server-generated (`<application_id>/<random>.<ext>`, `<application_id>/licence-<no>.pdf`), so the database rows (`stored_key`) are valid on either backend and a copy keeps every key.
- The change must be reversible with a setting, not a redeploy (build control, 9 Oct 2026: every risky part behind a switch whose default is today's behaviour).
- Memory stays bounded: the local backend streams in 64 KB chunks; the bucket backend must too.
- Local development and CI must not need a cloud account.

## Options considered

### Option A: keep the volume and mount it on the worker too
Railway volumes attach to one service. Not possible.

### Option B: the worker fetches files from the API over HTTP
Needs a service-to-service credential and a new internal endpoint that returns raw files, so a second authorisation path to the same bytes. It also leaves the files without a backup and the API as the single point everything reads through.

### Option C: an S3-compatible bucket behind `FileStorage` (chosen)
One new implementation of an interface that already exists. Railway offers buckets in the same project, reachable from every service. MinIO gives the same API locally and in Compose.

### Option D: store the bytes in PostgreSQL
Removes the second system, but fills the database and its backups with files, and `bytea` streaming through the ORM is the memory profile we are avoiding.

## Decision

Option C, behind a switch.

- `STORAGE_BACKEND=local|s3`, default `local`. `local` is today's behaviour, unchanged, and needs no S3 setting. `s3` selects `S3Storage` (`app/infra/s3_storage.py`).
- Settings for `s3`: `S3_ENDPOINT_URL` (empty means AWS), `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ADDRESSING_STYLE` (`auto`, `path` for MinIO, `virtual`). No default is a real value; with `s3` the app refuses to start when the bucket or either key is empty.
- One bucket per environment (development and production never share one).
- `S3Storage` implements the same six methods with the same contract: `put` streams the chunk iterator (boto3 multipart above 8 MiB, no thread pool), `open` yields 64 KB chunks and raises `FileNotFoundError` for a missing key, `exists` and `size` use a HEAD request (a missing key is absent and size 0), `delete` is idempotent, a key that would climb out of the store raises `ValueError`. A rejected upload leaves nothing behind (a single put is never started, a multipart upload is aborted). Infrastructure failures raise `StorageError`, an `OSError`, so every caller that already treats a disk failure as `storage_error` does the same.
- `disk_usage()` returns `(0, 0)` on a bucket: there is no volume to fill. The database sums behind `permitflow_storage_bytes{kind="documents"|"attachments"}` remain the measure of what is stored.
- A one-off script, `backend/scripts/copy_uploads_to_s3.py`, copies the upload directory to the bucket under the same keys, reads each object back and compares sha256. It is a dry run unless given `--execute`, skips objects already present with the same digest, never overwrites a different object under the same key, and exits non-zero on any conflict or mismatch.
- Compose gets a `minio` service and a one-shot `minio-init` that creates the bucket, under the `storage` profile. The default Compose path (database only, or the `full` profile with the volume) is unchanged.

## Rationale

- The interface already existed for this reason (SCOPE, ADR-001); the change is one class, one factory branch and one script, with no call site touched.
- A switch with a safe default makes the rollout a sequence of small, reversible steps: ship the code dormant, copy, flip on development, run the UAT, flip production at the release. The rollback is the switch.
- Streaming through the API keeps the authorisation model and the audit trail exactly as they are; the bucket is private and only the backend (and later the worker) hold its keys.
- Verifying by read-back sha256 proves the copy rather than trusting the upload call, and the documents table already stores a sha256 per file for the same purpose.

## Consequences

- A new runtime dependency, `boto3` (the AWS SDK for Python; the de facto S3 client, maintained by AWS, speaks to MinIO and Railway buckets alike). Dev-only: `moto` (in-process S3 mock for the contract tests) and `boto3-stubs[s3]` (types, so the module passes `mypy --strict` without `Any`).
- MinIO no longer publishes container images of its own (late 2025). Compose uses the Chainguard build of MinIO and its client, tagged `latest` because that is the only tag the free tier serves. If it disappears, any S3-compatible server (the same settings apply) replaces it; nothing in the application is MinIO specific.
- Two sources of truth exist during the migration. The order is: copy, verify, flip, and keep the volume until the bucket has held for a release. Files uploaded between the last copy and the flip must be copied again, so the copy is run once more immediately before the flip (it is idempotent) and the flip is done in a quiet moment.
- Flipping back to `local` after uploads have landed only in the bucket loses sight of those files. The rollback therefore includes copying back (the reverse copy is not scripted; see "Revisit when").
- The volume gauges (`volume_used`, `volume_total`) read 0 on a bucket, so the "volume above 80%" alert cannot fire; the dashboard row shows no data. They are left alone in this change and removed or replaced when the volume is retired.
- Latency: every `exists`, `size` and `open` is a network call. `storage_usage` makes one HEAD, for the licence certificate only (the document and attachment sizes come from the database), so an application page costs at most one extra round trip to the bucket; that is acceptable and is the first thing to measure on development.
- A 403 on a read is never "absent". Without `s3:ListBucket` a bucket answers 403 for a key that does not exist, indistinguishable from a forbidden one, so `S3Storage` raises `StorageError` (message names the code and the missing permission, nothing from the service) and `OPERATIONS.md` requires the bucket credentials to include `s3:ListBucket`, so that a missing key answers 404.
- Backups: a bucket is not a backup by itself. Versioning or a second bucket is a follow-up (readiness rows 13 and 14).

## Validation

- `tests/unit/test_storage_contract.py`: one suite, every case run against both `LocalDiskStorage` and `S3Storage` (moto): round trip, empty file, a 9 MB multipart upload read back in chunks of at most 64 KB, missing keys, idempotent delete, overwrite, a rejected upload leaving nothing, traversal keys refused, `StorageError` on an unreachable bucket, the default being `local`, the switch selecting the bucket, and start refused without bucket settings.
- `tests/unit/test_copy_uploads_script.py`: dry run changes nothing, execute copies and verifies sha256, a second run skips, an interrupted copy resumes, a conflict is reported and kept, a corrupted copy is removed and reported, the exit codes.
- `tests/integration/test_storage_s3.py`: upload, authorised download (404 for another operator, no redirect) and draft purge through the API with `STORAGE_BACKEND=s3`; the file is in the bucket and not on the disk.
- By hand against a real MinIO from Compose: the copy script dry run, execute and re-run.

## Revisit when

- Files exceed what a single request should hold in a multipart upload, or a scanning service needs to read objects directly (US-099); then presigned URLs for the worker only, never for people, would be considered.
- A rollback from the bucket to the volume is ever needed in earnest: write the reverse copy.
- The volume is retired: remove the `volume_*` gauges, the alert and the dashboard row, or replace them with bucket size from the provider.

## Links

Stories: US-097 (this), US-098 (worker), US-099 (scanning). Documents: `docs/09-operations/OPERATIONS.md` (variables, the switch, the copy procedure), `docs/03-architecture/ARCHITECTURE.md`, `docs/06-security/THREAT_MODEL.md` (T4), `docs/11-reviews/PRODUCTION_READINESS_REVIEW.md` (row 6), `SCOPE.md`.
