"""US-097: the one-off copy of the uploads directory to the bucket. Dry run by default, sha256 read-back
on every object, identical objects skipped, a different object under the same key never overwritten."""

import hashlib
import importlib.util
import os
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import boto3
import pytest
from moto import mock_aws

from app.core import settings as settings_module
from app.infra import s3_storage
from app.infra.s3_storage import S3Storage

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "copy_uploads_to_s3.py"
BUCKET = "permitflow-copy-test"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("copy_uploads_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


copy_script = _load()


@pytest.fixture
def bucket() -> Iterator[S3Storage]:
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield S3Storage(client, BUCKET)


@pytest.fixture
def uploads(tmp_path: Path) -> Path:
    root = tmp_path / "uploads"
    files = {
        "11111111/aaa.pdf": b"%PDF-1.7 first",
        "11111111/bbb.png": os.urandom(150_000),
        "22222222/ccc.txt": b"plain text",
        "22222222/licence-PF-2026-0001.pdf": os.urandom(9 * 1024 * 1024),  # crosses the multipart threshold
    }
    for name, data in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (root / "22222222" / "interrupted.pdf.part").write_bytes(b"never kept")
    return root


def _remote(storage: S3Storage, key: str) -> bytes:
    return b"".join(storage.open(key))


def test_dry_run_reports_and_changes_nothing(uploads: Path, bucket: S3Storage) -> None:
    summary = copy_script.copy_uploads(uploads, bucket, execute=False)
    assert summary.execute is False
    assert summary.uploaded == 4 and summary.skipped == 0 and summary.ok
    assert summary.bytes_copied == sum(
        p.stat().st_size for p in uploads.rglob("*") if p.is_file() and p.suffix != ".part"
    )
    assert not bucket.exists("11111111/aaa.pdf")


def test_execute_copies_every_file_and_the_bytes_match(uploads: Path, bucket: S3Storage) -> None:
    summary = copy_script.copy_uploads(uploads, bucket, execute=True)
    assert summary.uploaded == 4 and summary.skipped == 0 and summary.ok
    for path in uploads.rglob("*"):
        if path.is_file() and path.suffix != ".part":
            key = path.relative_to(uploads).as_posix()
            assert (
                hashlib.sha256(_remote(bucket, key)).hexdigest()
                == hashlib.sha256(path.read_bytes()).hexdigest()
            )
    assert not bucket.exists("22222222/interrupted.pdf.part")


def test_a_second_run_skips_identical_objects(uploads: Path, bucket: S3Storage) -> None:
    copy_script.copy_uploads(uploads, bucket, execute=True)
    again = copy_script.copy_uploads(uploads, bucket, execute=True)
    assert again.uploaded == 0 and again.skipped == 4 and again.ok
    dry = copy_script.copy_uploads(uploads, bucket, execute=False)
    assert dry.uploaded == 0 and dry.skipped == 4


def test_an_interrupted_copy_resumes_with_the_rest(uploads: Path, bucket: S3Storage) -> None:
    bucket.put("11111111/aaa.pdf", iter([b"%PDF-1.7 first"]))
    summary = copy_script.copy_uploads(uploads, bucket, execute=True)
    assert summary.skipped == 1 and summary.uploaded == 3 and summary.ok


def test_a_different_object_under_the_same_key_is_a_conflict_and_is_kept(
    uploads: Path, bucket: S3Storage
) -> None:
    bucket.put("11111111/aaa.pdf", iter([b"someone else's bytes"]))
    summary = copy_script.copy_uploads(uploads, bucket, execute=True)
    assert summary.conflicts == ["11111111/aaa.pdf"] and not summary.ok
    assert _remote(bucket, "11111111/aaa.pdf") == b"someone else's bytes"
    assert summary.uploaded == 3


def test_a_copy_that_fails_verification_is_removed_and_reported(uploads: Path, bucket: S3Storage) -> None:
    class Corrupting(S3Storage):
        def put(self, key: str, chunks: Iterator[bytes]) -> None:
            super().put(key, (c[:-1] if c else c for c in chunks))  # drops the last byte of each chunk

    bad = Corrupting(bucket._client, BUCKET)
    summary = copy_script.copy_uploads(uploads, bad, execute=True)
    assert not summary.ok and summary.uploaded == 0 and len(summary.failures) == 4
    assert "sha256 mismatch" in summary.failures[0]
    assert not bucket.exists("11111111/aaa.pdf")


def _configure(monkeypatch: pytest.MonkeyPatch, uploads: Path) -> None:
    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(uploads))
    monkeypatch.setattr(settings, "s3_bucket", BUCKET)
    monkeypatch.setattr(settings, "s3_access_key_id", "test-key-id")
    monkeypatch.setattr(settings, "s3_secret_access_key", "test-secret")
    s3_storage._build.cache_clear()


def test_main_is_a_dry_run_unless_told_otherwise(
    uploads: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure(monkeypatch, uploads)
    try:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=BUCKET)

            monkeypatch.setattr(sys, "argv", ["copy_uploads_to_s3.py"])
            assert copy_script.main() == 0
            out = capsys.readouterr().out
            assert "DRY RUN" in out and "would upload: 4 files" in out
            assert client.list_objects_v2(Bucket=BUCKET)["KeyCount"] == 0

            monkeypatch.setattr(sys, "argv", ["copy_uploads_to_s3.py", "--execute"])
            assert copy_script.main() == 0
            out = capsys.readouterr().out
            assert "EXECUTE" in out and "uploaded and verified: 4 files" in out and "result: OK" in out
            assert client.list_objects_v2(Bucket=BUCKET)["KeyCount"] == 4
    finally:
        s3_storage._build.cache_clear()


def test_main_exits_2_without_bucket_settings(
    uploads: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(uploads))
    monkeypatch.setattr(settings, "s3_bucket", "")
    monkeypatch.setattr(sys, "argv", ["copy_uploads_to_s3.py"])
    assert copy_script.main() == 2
    assert "S3_BUCKET" in capsys.readouterr().err


def test_main_exits_1_on_a_conflict(
    uploads: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure(monkeypatch, uploads)
    try:
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            client.create_bucket(Bucket=BUCKET)
            client.put_object(Bucket=BUCKET, Key="11111111/aaa.pdf", Body=b"different")
            monkeypatch.setattr(sys, "argv", ["copy_uploads_to_s3.py", "--execute"])
            assert copy_script.main() == 1
            assert "NOT OK" in capsys.readouterr().out
    finally:
        s3_storage._build.cache_clear()
