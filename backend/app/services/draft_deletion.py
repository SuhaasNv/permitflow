"""Delete a draft (US-045). A draft was never submitted, so it is not part of the licensing record: the
application, its documents (files included), verification runs and audit events are removed outright.
Submitted applications are never deleted (withdraw instead, US-038)."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.domain.enums import ApplicationStatus
from app.infra.storage import FileStorage, get_storage
from app.models import User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository


class DraftDeletionService:
    def __init__(self, db: Session, storage: FileStorage | None = None) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)
        self.documents = DocumentRepository(db)
        self.storage = storage or get_storage()

    def delete(self, operator: User, application_id: uuid.UUID) -> str:
        """Returns the deleted reference number. 409 unless the application is a draft."""
        app = self.applications.get_for(operator, application_id, for_update=True)
        if app.status != ApplicationStatus.DRAFT:
            raise Conflict("Only a draft can be deleted. A submitted application can be withdrawn instead.")
        reference = app.reference_no
        keys = self.documents.purge_for_application(app.id)
        self.audit.purge_draft(app.id)
        self.db.delete(app)
        self.db.commit()
        # Files go after the commit: a failed transaction must not leave dangling document rows.
        for key in keys:
            self.storage.delete(key)
        return reference
