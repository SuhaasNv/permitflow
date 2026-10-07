"""The one upload pipeline behind documents and clarification evidence (US-085): the document rules
(allowlist, magic bytes, 10 MB), images re-written without metadata, the storage budget per application,
and the sha256 of what was actually stored."""

import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.errors import BadRequest, ValidationFailed
from app.core.settings import get_settings
from app.domain.uploads import UploadRejected, check_magic_bytes, too_large_message
from app.infra.images import ImageUnreadableError, is_image, strip_metadata
from app.infra.storage import FileStorage, get_storage
from app.repositories.checklists import ChecklistRepository
from app.repositories.documents import DocumentRepository
from app.repositories.licences import LicenceRepository
from app.schemas.storage import StorageView

CHUNK = 64 * 1024


@dataclass(frozen=True)
class Received:
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class StorageUsage:
    used_bytes: int
    budget_bytes: int

    @property
    def remaining_bytes(self) -> int:
        return max(self.budget_bytes - self.used_bytes, 0)


def format_bytes(n: int) -> str:
    if n >= 1024 * 1024:
        value = n / (1024 * 1024)
        return f"{value:.0f} MB" if value >= 10 else f"{value:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def storage_usage(db: Session, application_id: uuid.UUID, storage: FileStorage | None = None) -> StorageUsage:
    """Everything the application holds on the volume: every document version, the clarification
    evidence, the licence certificate."""
    storage = storage or get_storage()
    used = DocumentRepository(db).total_bytes(application_id)
    used += ChecklistRepository(db).attachment_bytes(application_id)
    licence = LicenceRepository(db).for_application(application_id)
    if licence is not None:
        used += storage.size(licence.stored_key)
    return StorageUsage(used_bytes=used, budget_bytes=get_settings().storage_budget_bytes)


def storage_view(usage: StorageUsage) -> StorageView:
    return StorageView(
        used_bytes=usage.used_bytes, budget_bytes=usage.budget_bytes, remaining_bytes=usage.remaining_bytes
    )


def budget_error(usage: StorageUsage) -> ValidationFailed:
    room = format_bytes(usage.remaining_bytes)
    return ValidationFailed(
        f"This application has {room} of its {format_bytes(usage.budget_bytes)} storage room left. "
        "Remove a file you no longer need, or send a smaller one.",
        details={
            "reason": "storage_budget",
            "remaining_bytes": usage.remaining_bytes,
            "budget_bytes": usage.budget_bytes,
        },
    )


def receive(storage: FileStorage, key: str, ext: str, stream: BinaryIO, usage: StorageUsage) -> Received:
    """Read the upload under the size cap, check its signature, strip an image's metadata, refuse it
    when it would pass the application's budget, and store it under `key`. On any refusal nothing is
    left on disk. Returns the digest and size of the stored bytes."""
    if usage.remaining_bytes <= 0:
        raise budget_error(usage)
    limit = get_settings().upload_max_bytes
    digest = hashlib.sha256()
    size = 0

    def chunks() -> Iterator[bytes]:
        nonlocal size
        first = True
        while chunk := stream.read(CHUNK):
            if first:
                try:
                    check_magic_bytes(ext, chunk[:16])
                except UploadRejected as exc:
                    raise BadRequest(exc.message, details={"reason": exc.reason}) from exc
                first = False
            size += len(chunk)
            if size > limit:
                raise BadRequest(too_large_message(limit), details={"reason": "too_large"})
            if size > usage.remaining_bytes:
                raise budget_error(usage)
            digest.update(chunk)
            yield chunk
        if first:
            raise BadRequest("The file is empty.", details={"reason": "empty"})

    if is_image(ext):
        # Images are buffered (at most the size cap) so the pixels can be re-written without metadata;
        # the digest and the size are those of the stored bytes, not the phone's original.
        data = b"".join(chunks())
        try:
            data = strip_metadata(data, ext)
        except ImageUnreadableError as exc:
            raise BadRequest(
                "The image could not be read. Send it again, or save it as a PDF.",
                details={"reason": "unreadable_image"},
            ) from exc
        if len(data) > limit:
            # Re-encoding can grow a file that was just under the cap on the wire (a level-9 PNG).
            raise BadRequest(too_large_message(limit), details={"reason": "too_large"})
        if len(data) > usage.remaining_bytes:
            raise budget_error(usage)
        try:
            storage.put(key, iter([data]))
        except BadRequest:
            storage.delete(key)
            raise
        return Received(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))

    try:
        storage.put(key, chunks())
    except (BadRequest, ValidationFailed):
        storage.delete(key)
        raise
    return Received(sha256=digest.hexdigest(), size_bytes=size)


__all__ = [
    "Received",
    "StorageUsage",
    "budget_error",
    "format_bytes",
    "receive",
    "storage_usage",
    "storage_view",
]
