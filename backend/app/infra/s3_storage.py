"""`FileStorage` on an S3-compatible bucket (US-097, ADR-015): a Railway bucket, MinIO locally.

Same contract as `LocalDiskStorage`: server-generated keys, uploads and downloads streamed in chunks (a
file is never held whole in memory by this module), a missing key reads as absent, never a public URL.
Downloads still go through the authorised API endpoint, which iterates `open()`.
"""

import io
from collections.abc import Iterator
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.settings import get_settings
from app.infra.storage import StorageError

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

CHUNK = 64 * 1024
_NOT_FOUND = {"404", "NoSuchKey", "NotFound"}
# Single-threaded transfers: no thread pool is started inside a request, and memory stays bounded by one
# 8 MiB part (the upload ceiling is 10 MB, so at most one multipart upload of two parts).
_TRANSFER = TransferConfig(
    use_threads=False, multipart_threshold=8 * 1024 * 1024, multipart_chunksize=8 * 1024 * 1024
)


class _ChunkReader(io.RawIOBase):
    """Presents an iterator of byte chunks as a readable stream, so boto3 can pull from it."""

    def __init__(self, chunks: Iterator[bytes]) -> None:
        self._chunks = chunks
        self._pending = b""

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray | memoryview) -> int:  # type: ignore[override]
        while not self._pending:
            try:
                self._pending = next(self._chunks)
            except StopIteration:
                return 0
        n = min(len(buffer), len(self._pending))
        buffer[:n] = self._pending[:n]
        self._pending = self._pending[n:]
        return n


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


class S3Storage:
    def __init__(self, client: "S3Client", bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @staticmethod
    def _check(key: str) -> str:
        """Same refusal as the local backend's path check: keys are relative and never climb."""
        parts = key.split("/")
        if not key or "\\" in key or any(p in ("", ".", "..") for p in parts):
            raise ValueError("invalid storage key")
        return key

    def put(self, key: str, chunks: Iterator[bytes]) -> None:
        self._check(key)
        try:
            self._client.upload_fileobj(
                io.BufferedReader(_ChunkReader(chunks), buffer_size=CHUNK),
                self._bucket,
                key,
                Config=_TRANSFER,
            )
        except (BotoCoreError, ClientError) as exc:
            # A rejected upload (too large, wrong bytes) raises from `chunks`, not here, and propagates
            # as it is: S3 then holds nothing (a single put never started; a multipart upload is aborted).
            raise StorageError(f"object storage put failed: {type(exc).__name__}") from exc

    def open(self, key: str) -> Iterator[bytes]:
        self._check(key)
        try:
            body = self._client.get_object(Bucket=self._bucket, Key=key)["Body"]
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND:
                raise FileNotFoundError(key) from exc
            raise StorageError(f"object storage get failed: {_error_code(exc)}") from exc
        except BotoCoreError as exc:
            raise StorageError(f"object storage get failed: {type(exc).__name__}") from exc
        try:
            yield from body.iter_chunks(CHUNK)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"object storage read failed: {type(exc).__name__}") from exc
        finally:
            body.close()

    def delete(self, key: str) -> None:
        self._check(key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"object storage delete failed: {type(exc).__name__}") from exc

    def _head(self, key: str) -> int | None:
        """The object's size in bytes, or None when it does not exist."""
        self._check(key)
        try:
            return int(self._client.head_object(Bucket=self._bucket, Key=key)["ContentLength"])
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND:
                return None
            raise StorageError(f"object storage head failed: {_error_code(exc)}") from exc
        except BotoCoreError as exc:
            raise StorageError(f"object storage head failed: {type(exc).__name__}") from exc

    def check_bucket(self) -> None:
        """Raise StorageError unless the bucket exists and the credentials can reach it."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            raise StorageError(f"bucket {self._bucket!r} is not reachable: {_error_code(exc)}") from exc
        except BotoCoreError as exc:
            raise StorageError(f"bucket {self._bucket!r} is not reachable: {type(exc).__name__}") from exc

    def exists(self, key: str) -> bool:
        return self._head(key) is not None

    def size(self, key: str) -> int:
        return self._head(key) or 0

    def disk_usage(self) -> tuple[int, int]:
        """A bucket has no capacity to fill, so there is no volume to report: (0, 0). The database sums
        (`documents`, `attachments`) stay the measure of what is stored."""
        return 0, 0


@lru_cache
def _build(
    endpoint_url: str,
    bucket: str,
    region: str,
    access_key: str,
    secret_key: str,
    style: Literal["auto", "path", "virtual"],
) -> S3Storage:
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": style},
            connect_timeout=5,
            read_timeout=30,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    return S3Storage(client, bucket)


def s3_storage_from_settings() -> S3Storage:
    """The bucket the settings name. Independent of STORAGE_BACKEND so the copy script can write to the
    bucket while the application still reads the disk."""
    s = get_settings()
    if s.s3_missing():
        raise RuntimeError(f"object storage needs {', '.join(s.s3_missing())} to be set")
    return _build(
        s.s3_endpoint_url,
        s.s3_bucket,
        s.s3_region,
        s.s3_access_key_id,
        s.s3_secret_access_key,
        s.s3_addressing_style,
    )
