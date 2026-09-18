"""Delete a draft (US-045). A draft was never submitted, so it is not part of the licensing record: the
application, its documents (files included), verification runs and audit events are removed outright.
Submitted applications are never deleted (withdraw instead, US-038)."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.domain.enums import ApplicationStatus
from app.infra.storage import FileStorage, get_storage
from app.models import AuditEvent, Document, User, VerificationRun
from app.repositories.applications import ApplicationRepository


class DraftDeletionService:
    def __init__(self, db: Session, storage: FileStorage | None = None) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.storage = storage or get_storage()

    def delete(self, operator: User, application_id: uuid.UUID) -> str:
        """Returns the deleted reference number. 409 unless the application is a draft."""
        app = self.applications.get_for(operator, application_id, for_update=True)
        if app.status != ApplicationStatus.DRAFT:
            raise Conflict("Only a draft can be deleted. A submitted application can be withdrawn instead.")
        reference = app.reference_no
        documents = list(self.db.scalars(select(Document).where(Document.application_id == app.id)))
        keys = [d.stored_key for d in documents]
        if documents:
            self.db.execute(
                delete(VerificationRun).where(VerificationRun.document_id.in_([d.id for d in documents]))
            )
            self.db.execute(delete(Document).where(Document.application_id == app.id))
        self.db.execute(delete(AuditEvent).where(AuditEvent.application_id == app.id))
        self.db.delete(app)
        self.db.commit()
        # Files go after the commit: a failed transaction must not leave dangling document rows.
        for key in keys:
            self.storage.delete(key)
        return reference
