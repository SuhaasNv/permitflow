import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ApplicationRevision


class RevisionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for(self, application_id: uuid.UUID) -> list[ApplicationRevision]:
        stmt = (
            select(ApplicationRevision)
            .where(ApplicationRevision.application_id == application_id)
            .order_by(ApplicationRevision.revision_number.asc())
        )
        return list(self.db.scalars(stmt))

    def count_for(self, application_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ApplicationRevision)
            .where(ApplicationRevision.application_id == application_id)
        )
        return int(self.db.scalar(stmt) or 0)

    def next_number(self, application_id: uuid.UUID) -> int:
        stmt = select(func.max(ApplicationRevision.revision_number)).where(
            ApplicationRevision.application_id == application_id
        )
        return int(self.db.scalar(stmt) or 0) + 1

    def add(self, revision: ApplicationRevision) -> ApplicationRevision:
        self.db.add(revision)
        return revision
