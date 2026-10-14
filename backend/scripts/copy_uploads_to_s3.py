"""One-off copy of the uploads directory to the object-storage bucket (US-097, ADR-015). Run from backend/:

    uv run python scripts/copy_uploads_to_s3.py                 # dry run (the default): changes nothing
    uv run python scripts/copy_uploads_to_s3.py --execute       # upload, then read every object back

Every file under the upload directory is copied to the bucket under the same key (its path relative to
the directory), then read back from the bucket and compared by sha256 with the local file. An object that
is already in the bucket with the same sha256 is skipped, so the script can be run again after an
interruption or once more just before the switch. An object that exists with different content is a
conflict: it is reported and never overwritten. Keys are server-generated and unique, so a conflict means
the wrong bucket or a corrupted object, and a person has to look.

The bucket comes from the S3_* settings (the environment or .env), whatever STORAGE_BACKEND says, so the
application can keep reading the disk while the copy runs. Exit code 0 when every file is in the bucket
and verified (or, in a dry run, would be); 1 when any file conflicted or failed; 2 for bad configuration.
"""

import argparse
import hashlib
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings  # noqa: E402
from app.infra.s3_storage import S3Storage, s3_storage_from_settings  # noqa: E402

CHUNK = 64 * 1024


@dataclass
class Summary:
    execute: bool
    uploaded: int = 0  # copied and verified (execute) or would be copied (dry run)
    skipped: int = 0  # already in the bucket with the same sha256
    bytes_copied: int = 0
    conflicts: list[str] = field(default_factory=list)  # in the bucket with different content
    failures: list[str] = field(default_factory=list)  # upload or read-back failed, or sha256 mismatch

    @property
    def ok(self) -> bool:
        return not self.conflicts and not self.failures


def _read_file(path: Path) -> Iterator[bytes]:
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            yield chunk


def _local_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    for chunk in _read_file(path):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def _remote_digest(storage: S3Storage, key: str) -> str:
    digest = hashlib.sha256()
    for chunk in storage.open(key):
        digest.update(chunk)
    return digest.hexdigest()


def local_files(source: Path) -> list[Path]:
    """Every upload, in a stable order. A `.part` file is an interrupted upload the app never kept."""
    return sorted(p for p in source.rglob("*") if p.is_file() and p.suffix != ".part")


def copy_uploads(source: Path, storage: S3Storage, *, execute: bool) -> Summary:
    summary = Summary(execute=execute)
    for path in local_files(source):
        key = path.relative_to(source).as_posix()
        try:
            digest, size = _local_digest(path)
            if storage.exists(key):
                if storage.size(key) == size and _remote_digest(storage, key) == digest:
                    summary.skipped += 1
                else:
                    summary.conflicts.append(key)
                continue
            if not execute:
                summary.uploaded += 1
                summary.bytes_copied += size
                continue
            storage.put(key, _read_file(path))
            if _remote_digest(storage, key) != digest:
                storage.delete(key)  # we just created it: a bad copy must not stay for the switch to find
                summary.failures.append(f"{key} (sha256 mismatch after upload, object removed)")
                continue
            summary.uploaded += 1
            summary.bytes_copied += size
        except (OSError, ValueError) as exc:
            summary.failures.append(f"{key} ({type(exc).__name__}: {exc})")
    return summary


def print_summary(summary: Summary, source: Path, bucket: str) -> None:
    mode = "EXECUTE" if summary.execute else "DRY RUN (nothing was changed; pass --execute to copy)"
    verb = "uploaded and verified" if summary.execute else "would upload"
    print(f"copy_uploads_to_s3: {mode}")
    print(f"  source:    {source}")
    print(f"  bucket:    {bucket}")
    print(f"  {verb}: {summary.uploaded} files, {summary.bytes_copied} bytes")
    print(f"  skipped (identical sha256 already in the bucket): {summary.skipped}")
    print(f"  conflicts (different content under the same key, not overwritten): {len(summary.conflicts)}")
    for item in summary.conflicts:
        print(f"    {item}")
    print(f"  failures: {len(summary.failures)}")
    for item in summary.failures:
        print(f"    {item}")
    print("  result: " + ("OK" if summary.ok else "NOT OK, do not flip STORAGE_BACKEND"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy the uploads directory to the object-storage bucket.")
    parser.add_argument("--dry-run", action="store_true", help="report only (this is the default)")
    parser.add_argument(
        "--execute", action="store_true", help="upload and verify; without it nothing changes"
    )
    parser.add_argument("--source", help="uploads directory (default: UPLOAD_DIR)")
    args = parser.parse_args()
    if args.dry_run and args.execute:
        print("--dry-run and --execute exclude each other", file=sys.stderr)
        return 2

    settings = get_settings()
    source = Path(args.source or settings.upload_dir)
    if not source.is_dir():
        print(f"upload directory not found: {source}", file=sys.stderr)
        return 2
    try:
        storage = s3_storage_from_settings()
        storage.check_bucket()
    except (RuntimeError, OSError) as exc:
        print(f"object storage is not ready: {exc}", file=sys.stderr)
        return 2

    summary = copy_uploads(source, storage, execute=args.execute)
    print_summary(summary, source, settings.s3_bucket)
    return 0 if summary.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
