"""US-097: one contract, run against both storages. Whatever the backend, `FileStorage` behaves the same:
streamed in and out, a missing key reads as absent, a bad key is refused, a rejected upload leaves nothing.
The S3 side runs on moto's in-process mock, so no network and no real bucket is involved."""

import hashlib
import os
from collections.abc import Iterator
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from app.core import settings as settings_module
from app.infra import s3_storage
from app.infra.s3_storage import S3Storage
from app.infra.storage import FileStorage, LocalDiskStorage, StorageError, get_storage

BUCKET = "permitflow-test"


@pytest.fixture(params=["local", "s3"])
def storage(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[FileStorage]:
    if request.param == "local":
        yield LocalDiskStorage(str(tmp_path / "uploads"))
        return
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield S3Storage(client, BUCKET)


def _chunks(data: bytes, size: int = 64 * 1024) -> Iterator[bytes]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


def _read(storage: FileStorage, key: str) -> bytes:
    return b"".join(storage.open(key))


def test_round_trip_keeps_the_bytes(storage: FileStorage) -> None:
    storage.put("app-1/doc.pdf", iter([b"%PDF-1.7 ", b"hello ", b"world"]))
    assert _read(storage, "app-1/doc.pdf") == b"%PDF-1.7 hello world"
    assert storage.exists("app-1/doc.pdf")
    assert storage.size("app-1/doc.pdf") == len(b"%PDF-1.7 hello world")


def test_an_empty_file_is_stored(storage: FileStorage) -> None:
    storage.put("app-1/empty.txt", iter([]))
    assert storage.exists("app-1/empty.txt")
    assert storage.size("app-1/empty.txt") == 0
    assert _read(storage, "app-1/empty.txt") == b""


def test_a_large_file_is_streamed_in_and_out(storage: FileStorage) -> None:
    """9 MB crosses boto3's multipart threshold; the read side must hand it back in many chunks."""
    data = os.urandom(9 * 1024 * 1024 + 123)
    storage.put("app-1/big.bin", _chunks(data, 100_000))
    chunks = list(storage.open("app-1/big.bin"))
    assert len(chunks) > 10
    assert max(len(c) for c in chunks) <= 64 * 1024
    assert hashlib.sha256(b"".join(chunks)).digest() == hashlib.sha256(data).digest()
    assert storage.size("app-1/big.bin") == len(data)


def test_a_missing_key_is_absent(storage: FileStorage) -> None:
    assert not storage.exists("app-1/nope.pdf")
    assert storage.size("app-1/nope.pdf") == 0
    with pytest.raises(FileNotFoundError):
        _read(storage, "app-1/nope.pdf")


def test_delete_removes_and_is_idempotent(storage: FileStorage) -> None:
    storage.put("app-1/doc.pdf", iter([b"x"]))
    storage.delete("app-1/doc.pdf")
    assert not storage.exists("app-1/doc.pdf")
    storage.delete("app-1/doc.pdf")
    storage.delete("app-1/never-existed.pdf")


def test_put_replaces_an_existing_key(storage: FileStorage) -> None:
    storage.put("app-1/doc.pdf", iter([b"first"]))
    storage.put("app-1/doc.pdf", iter([b"second version"]))
    assert _read(storage, "app-1/doc.pdf") == b"second version"
    assert storage.size("app-1/doc.pdf") == len(b"second version")


def test_a_rejected_upload_leaves_nothing_behind(storage: FileStorage) -> None:
    """The upload service aborts a too-large or wrong-bytes stream by raising from the chunk iterator."""

    class RejectedError(Exception):
        pass

    def chunks() -> Iterator[bytes]:
        yield b"partial"
        raise RejectedError

    with pytest.raises(RejectedError):
        storage.put("app-1/bad.pdf", chunks())
    assert not storage.exists("app-1/bad.pdf")


def test_a_rejected_overwrite_keeps_the_previous_file(storage: FileStorage) -> None:
    storage.put("app-1/doc.pdf", iter([b"good"]))

    def chunks() -> Iterator[bytes]:
        yield b"partial"
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        storage.put("app-1/doc.pdf", chunks())
    assert _read(storage, "app-1/doc.pdf") == b"good"


@pytest.mark.parametrize("key", ["", "../escape.pdf", "app-1/../../escape.pdf", "/absolute.pdf"])
def test_keys_cannot_leave_the_store(storage: FileStorage, key: str) -> None:
    with pytest.raises(ValueError, match="invalid storage key"):
        storage.put(key, iter([b"x"]))
    with pytest.raises(ValueError, match="invalid storage key"):
        storage.exists(key)


def test_disk_usage_reports_two_non_negative_numbers(storage: FileStorage) -> None:
    used, total = storage.disk_usage()
    assert used >= 0 and total >= 0


def test_an_unreachable_bucket_is_a_storage_error() -> None:
    """Infrastructure failures surface as OSError subclasses, so callers that treat a disk failure as a
    storage failure (the verification run's `storage_error`) treat this the same way."""
    with mock_aws():
        broken = S3Storage(boto3.client("s3", region_name="us-east-1"), "bucket-that-does-not-exist")
        with pytest.raises(StorageError):
            broken.put("app-1/doc.pdf", iter([b"x"]))
        with pytest.raises(StorageError):
            _read(broken, "app-1/doc.pdf")
        with pytest.raises(StorageError):
            broken.check_bucket()
    assert issubclass(StorageError, OSError)


def test_the_switch_defaults_to_local_disk() -> None:
    assert settings_module.get_settings().storage_backend == "local"
    assert isinstance(get_storage(), LocalDiskStorage)


def test_the_switch_selects_the_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", BUCKET)
    monkeypatch.setattr(settings, "s3_access_key_id", "test-key-id")
    monkeypatch.setattr(settings, "s3_secret_access_key", "test-secret")
    s3_storage._build.cache_clear()
    try:
        with mock_aws():
            boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
            chosen = get_storage()
            assert isinstance(chosen, S3Storage)
            chosen.put("app-1/doc.pdf", iter([b"via the switch"]))
            assert _read(chosen, "app-1/doc.pdf") == b"via the switch"
    finally:
        s3_storage._build.cache_clear()


def test_the_bucket_backend_refuses_to_start_without_its_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "")
    monkeypatch.setattr(settings, "s3_access_key_id", "")
    monkeypatch.setattr(settings, "s3_secret_access_key", "")
    with pytest.raises(RuntimeError, match="S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY"):
        settings.validate_for_startup()
    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        get_storage()
