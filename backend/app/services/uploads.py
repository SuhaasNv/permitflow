"""The one upload pipeline behind documents and clarification evidence (US-085): the document rules
(allowlist, magic bytes, 10 MB), images re-written without metadata, the storage budget per application,
and the sha256 of what was actually stored."""

import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.errors import AppError, BadRequest, InsufficientStorage, Unavailable, ValidationFailed
from app.core.settings import get_settings
from app.domain.uploads import UploadRejected, check_magic_bytes, too_large_message
from app.infra.images import ImageBusyError, ImageUnreadableError, is_image, strip_metadata
from app.infra.storage import FileStorage, get_storage
from app.models import Application
from app.repositories.checklists import ChecklistRepository
from app.repositories.documents import DocumentRepository
from app.repositories.licences import LicenceRepository
from app.schemas.storage import StorageView
from app.services.platform_settings import live

CHUNK = 64 * 1024


@dataclass(frozen=True)
class Received:
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class StorageUsage:
    used_bytes: int
    budget_bytes: int
    operator_used_bytes: int = 0
    operator_budget_bytes: int | None = None  # None: no per-operator bound

    @property
    def app_remaining_bytes(self) -> int:
        return max(self.budget_bytes - self.used_bytes, 0)

    @property
    def operator_remaining_bytes(self) -> int | None:
        if self.operator_budget_bytes is None:
            return None
        return max(self.operator_budget_bytes - self.operator_used_bytes, 0)

    @property
    def remaining_bytes(self) -> int:
        """Room under the tighter of the application's budget and its operator's."""
        room = self.operator_remaining_bytes
        return self.app_remaining_bytes if room is None else min(self.app_remaining_bytes, room)


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
    settings = get_settings()
    app = db.get(Application, application_id)
    if app is None:
        return StorageUsage(used_bytes=used, budget_bytes=settings.storage_budget_bytes)
    # The same three sums across all of the operator's applications: one account cannot drain the
    # platform ceiling through many applications (audit run 4).
    operator_used = DocumentRepository(db).total_bytes(operator_id=app.operator_id)
    operator_used += ChecklistRepository(db).attachment_bytes(operator_id=app.operator_id)
    operator_used += sum(
        storage.size(k) for k in LicenceRepository(db).stored_keys_for_operator(app.operator_id)
    )
    return StorageUsage(
        used_bytes=used,
        budget_bytes=settings.storage_budget_bytes,
        operator_used_bytes=operator_used,
        operator_budget_bytes=settings.storage_per_operator_bytes,
    )


def storage_view(usage: StorageUsage) -> StorageView:
    return StorageView(
        used_bytes=usage.used_bytes, budget_bytes=usage.budget_bytes, remaining_bytes=usage.remaining_bytes
    )


def budget_error(usage: StorageUsage) -> ValidationFailed:
    operator_room = usage.operator_remaining_bytes
    if operator_room is not None and operator_room < usage.app_remaining_bytes:
        total = format_bytes(usage.operator_budget_bytes or 0)
        return ValidationFailed(
            f"Your account has {format_bytes(operator_room)} of its {total} "
            "storage room left across all your applications. "
            "Remove a file or a draft you no longer need, or send a smaller one.",
            details={
                "reason": "storage_operator_budget",
                "remaining_bytes": operator_room,
                "budget_bytes": usage.operator_budget_bytes,
            },
        )
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


def platform_remaining(db: Session) -> int | None:
    """Room left under the platform-wide ceiling (US-098), from the same two sums as the storage gauge,
    so it holds on either backend; None when there is no ceiling (0, never in production). Parallel
    uploads can overshoot it by a few files: it is a brake on growth, not an accounting lock."""
    cap = get_settings().storage_total_max_bytes
    if cap <= 0:
        return None
    return max(cap - DocumentRepository(db).total_bytes() - ChecklistRepository(db).attachment_bytes(), 0)


def platform_full() -> InsufficientStorage:
    return InsufficientStorage(
        "The platform has no storage room left for this file. Try again later.",
        details={"reason": "platform_storage_full"},
    )


def receive(
    storage: FileStorage,
    key: str,
    ext: str,
    stream: BinaryIO,
    usage: StorageUsage,
    platform_room: int | None = None,
) -> Received:
    """Read the upload under the size cap, check its signature, strip an image's metadata, refuse it
    when it would pass the application's budget, and store it under `key`. On any refusal nothing is
    left on disk. `platform_room` is what `platform_remaining` returned (None: no ceiling). Returns the
    digest and size of the stored bytes."""
    if usage.remaining_bytes <= 0:
        raise budget_error(usage)
    if platform_room is not None and platform_room <= 0:
        raise platform_full()
    limit = live().int_value("upload_max_bytes")
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
            if platform_room is not None and size > platform_room:
                raise platform_full()
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
        except ImageBusyError as exc:
            raise Unavailable("The server is busy. Try again in a moment.") from exc
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
        if platform_room is not None and len(data) > platform_room:
            raise platform_full()
        try:
            storage.put(key, iter([data]))
        except BadRequest:
            storage.delete(key)
            raise
        return Received(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))

    try:
        storage.put(key, chunks())
    except AppError:
        storage.delete(key)
        raise
    return Received(sha256=digest.hexdigest(), size_bytes=size)


__all__ = [
    "Received",
    "StorageUsage",
    "budget_error",
    "format_bytes",
    "platform_remaining",
    "receive",
    "storage_usage",
    "storage_view",
]
