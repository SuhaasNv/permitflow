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
