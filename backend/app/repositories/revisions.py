import uuid
from datetime import datetime

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

    def stats_for(self, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, tuple[int, datetime | None]]:
        """(revision count, first submission time) per application, in one query."""
        if not application_ids:
            return {}
        stmt = (
            select(
                ApplicationRevision.application_id,
                func.count(),
                func.min(ApplicationRevision.submitted_at),
            )
            .where(ApplicationRevision.application_id.in_(application_ids))
            .group_by(ApplicationRevision.application_id)
        )
        return {row[0]: (int(row[1]), row[2]) for row in self.db.execute(stmt)}

    def latest_for(self, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, ApplicationRevision]:
        """The most recent submitted revision per application, one query (`DISTINCT ON`). Officer lists
        read the submitted form from here, never the operator's working copy (`draft_data`)."""
        if not application_ids:
            return {}
        stmt = (
            select(ApplicationRevision)
            .where(ApplicationRevision.application_id.in_(application_ids))
            .distinct(ApplicationRevision.application_id)
            .order_by(ApplicationRevision.application_id, ApplicationRevision.revision_number.desc())
        )
        return {r.application_id: r for r in self.db.scalars(stmt)}

    def next_number(self, application_id: uuid.UUID) -> int:
        stmt = select(func.max(ApplicationRevision.revision_number)).where(
            ApplicationRevision.application_id == application_id
        )
        return int(self.db.scalar(stmt) or 0) + 1

    def add(self, revision: ApplicationRevision) -> ApplicationRevision:
        self.db.add(revision)
        return revision
