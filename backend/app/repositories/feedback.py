import uuid
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Feedback
from app.models.enums import FeedbackResolution


class FeedbackRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def open_counts(self, application_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Open feedback items per application, in one query."""
        ids = list(application_ids)
        if not ids:
            return {}
        stmt = (
            select(Feedback.application_id, func.count())
            .where(Feedback.application_id.in_(ids), Feedback.resolution == FeedbackResolution.OPEN)
            .group_by(Feedback.application_id)
        )
        return {row[0]: int(row[1]) for row in self.db.execute(stmt)}

    def list_for(self, application_id: uuid.UUID) -> list[Feedback]:
        stmt = (
            select(Feedback)
            .where(Feedback.application_id == application_id)
            .order_by(Feedback.created_at.asc(), Feedback.id.asc())
        )
        return list(self.db.scalars(stmt))

    def open_for(self, application_id: uuid.UUID) -> list[Feedback]:
        stmt = select(Feedback).where(
            Feedback.application_id == application_id, Feedback.resolution == FeedbackResolution.OPEN
        )
        return list(self.db.scalars(stmt))

    def get_in_application(self, application_id: uuid.UUID, feedback_id: uuid.UUID) -> Feedback | None:
        """Sub-resource check: the item must belong to the application (SEC-002)."""
        return self.db.scalar(
            select(Feedback).where(Feedback.id == feedback_id, Feedback.application_id == application_id)
        )

    def add(self, item: Feedback) -> Feedback:
        self.db.add(item)
        return item
