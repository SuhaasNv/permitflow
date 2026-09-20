"""Document upload, replacement, download and deletion (FR-004, SEC-005)."""

import urllib.parse
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.core.errors import BadRequest, Forbidden, NotFound
from app.domain.enums import ApplicationStatus, DocumentType
from app.domain.uploads import UploadRejected, canonical_content_type, check_name_and_type
from app.infra.storage import FileStorage, get_storage, new_storage_key
from app.models import Application, Document, User, VerificationRun
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.services.applications import ApplicationService
from app.services.quotas import new_run
from app.services.uploads import receive, storage_usage


@dataclass(frozen=True)
class UploadResult:
    application: Application
    document: Document
    run: VerificationRun | None
    unchanged: bool  # identical to the current file of this type (same sha256)


class DocumentService:
    def __init__(self, db: Session, storage: FileStorage | None = None) -> None:
        self.db = db
        self.storage = storage or get_storage()
        self.applications = ApplicationRepository(db)
        self.documents = DocumentRepository(db)
        self.audit = AuditRepository(db)

    def upload(
        self,
        operator: User,
        application_id: uuid.UUID,
        document_type: DocumentType,
        filename: str,
        content_type: str | None,
        stream: BinaryIO,
    ) -> UploadResult:
        try:
            ext = check_name_and_type(filename, content_type)
        except UploadRejected as exc:
            raise BadRequest(exc.message, details={"reason": exc.reason}) from exc

        app = self.applications.get_for(operator, application_id, for_update=True)
        _, editable_types = ApplicationService(self.db).editable_for(app)
        if document_type not in editable_types:
            if app.status == ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
                raise Forbidden("The licensing officer did not ask for a new copy of this document.")
            raise Forbidden("This document is not open for changes.")

        # One pipeline for every upload (US-085): size cap, magic bytes, images without metadata, the
        # application's storage budget; the digest is that of the stored bytes.
        key = new_storage_key(app.id, ext)
        received = receive(self.storage, key, ext, stream, storage_usage(self.db, app.id, self.storage))
        sha, size = received.sha256, received.size_bytes
        previous = self.documents.current_of_type(app.id, document_type)
        if previous is not None and previous.sha256 == sha:
            # Identical re-upload: keep the existing document, report "no change" (SEC-005 duplicate rule).
            self.storage.delete(key)
            self.db.rollback()
            app = self.applications.get_for(operator, application_id)
            return UploadResult(app, previous, self.documents.latest_run(previous.id), unchanged=True)

        doc = Document(
            application_id=app.id,
            document_type=document_type,
            original_filename=_display_name(filename),
            stored_key=key,
            content_type=canonical_content_type(ext),
            size_bytes=size,
            sha256=sha,
            supersedes_id=previous.id if previous else None,
            is_current=True,
            uploaded_by=operator.id,
        )
        if previous is not None:
            previous.is_current = False
        self.documents.add(doc)
        self.db.flush()
        run = new_run(self.db, doc.id, app.operator_id)
        self.documents.add_run(run)
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="document.replaced" if previous else "document.uploaded",
            payload={
                "document_id": str(doc.id),
                "document_type": document_type.value,
                "filename": doc.original_filename,
                "sha256": sha[:12],
                "replaces": str(previous.id) if previous else None,
            },
        )
        app.version += 1
        try:
            self.db.commit()
        except Exception:
            self.storage.delete(key)
            raise
        self.db.refresh(app)
        self.db.refresh(doc)
        self.db.refresh(run)
        return UploadResult(app, doc, run, unchanged=False)

    def delete(self, operator: User, application_id: uuid.UUID, document_id: uuid.UUID) -> Application:
        """Remove a document while the application is still a draft (SCOPE S3)."""
        app = self.applications.get_for(operator, application_id, for_update=True)
        if app.status != ApplicationStatus.DRAFT:
            raise Forbidden("Documents can only be removed while the application is a draft.")
        doc = self.documents.get_in_application(app.id, document_id)
        if doc is None or not doc.is_current:
            raise NotFound("Document not found.")
        doc.is_current = False
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="document.deleted",
            payload={"document_id": str(doc.id), "document_type": doc.document_type.value},
        )
        app.version += 1
        self.db.commit()
        self.db.refresh(app)
        return app

    def open_for_download(
        self, user: User, application_id: uuid.UUID, document_id: uuid.UUID
    ) -> tuple[Document, Iterator[bytes]]:
        app = self.applications.get_for(user, application_id)
        doc = self.documents.get_in_application(app.id, document_id)
        if doc is None:
            raise NotFound("Document not found.")
        if not self.storage.exists(doc.stored_key):
            raise NotFound("This file is no longer available.")
        return doc, self.storage.open(doc.stored_key)


def content_disposition(filename: str) -> str:
    """Attachment header safe for any name: ASCII fallback plus RFC 5987 UTF-8 form (headers are Latin-1)."""
    ascii_name = (
        "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else "_" for ch in filename) or "document"
    )
    utf8 = urllib.parse.quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{utf8}"


def _display_name(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
    cleaned = "".join(ch for ch in name if ch.isprintable() and ch not in '<>:"|?*')
    return cleaned[:255] or "document"
