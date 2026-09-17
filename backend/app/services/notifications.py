"""In-app notifications (FR-020, FR-021). Email delivery is mocked: the message is logged."""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models import Application, Notification
from app.models.enums import NotificationKind
from app.repositories.notifications import NotificationRepository

logger = logging.getLogger("permitflow.notifications")


class EmailNotifier:
    """Mock delivery adapter (SCOPE: email is mocked). Logs identifiers only."""

    def send(self, user_id: uuid.UUID, title: str) -> None:
        logger.info("email_mock", extra={"extra_fields": {"user_id": str(user_id), "title": title}})


class NotificationService:
    def __init__(self, db: Session, notifier: EmailNotifier | None = None) -> None:
        self.repo = NotificationRepository(db)
        self.notifier = notifier or EmailNotifier()

    def notify_officers(self, app: Application, kind: NotificationKind, title: str, body: str) -> int:
        """Every active officer (no assignment model in the MVP). Same transaction as the caller's commit."""
        items = [
            Notification(user_id=uid, application_id=app.id, kind=kind, title=title, body=body)
            for uid in self.repo.active_officer_ids()
        ]
        self.repo.add_all(items)
        for item in items:
            self.notifier.send(item.user_id, title)
        return len(items)

    def notify_user(
        self, user_id: uuid.UUID, app: Application, kind: NotificationKind, title: str, body: str
    ) -> None:
        self.repo.add_all(
            [Notification(user_id=user_id, application_id=app.id, kind=kind, title=title, body=body)]
        )
        self.notifier.send(user_id, title)
