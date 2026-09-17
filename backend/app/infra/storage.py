"""File storage behind a small interface (SCOPE: local disk now, object storage later)."""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol

from app.core.settings import get_settings


class FileStorage(Protocol):
    def put(self, key: str, chunks: Iterator[bytes]) -> None: ...
    def open(self, key: str) -> Iterator[bytes]: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...


class LocalDiskStorage:
    """Server-generated keys under UPLOAD_DIR; never the client's file name (SEC-005)."""

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or get_settings().upload_dir)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError("invalid storage key")
        return p

    def put(self, key: str, chunks: Iterator[bytes]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        with tmp.open("wb") as f:
            for chunk in chunks:
                f.write(chunk)
        os.replace(tmp, path)

    def open(self, key: str) -> Iterator[bytes]:
        path = self._path(key)
        with path.open("rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


def new_storage_key(application_id: uuid.UUID, extension: str) -> str:
    return f"{application_id}/{uuid.uuid4().hex}{extension}"


def get_storage() -> FileStorage:
    return LocalDiskStorage()
