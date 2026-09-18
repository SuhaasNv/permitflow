"""In-app notifications (FR-020, FR-021). Email delivery is mocked: the message is logged."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models import Application, Notification
from app.models.enums import NotificationKind
from app.repositories.notifications import NotificationRepository

logger = logging.getLogger("permitflow.notifications")


class EmailNotifier:
    """Mock delivery adapter (SCOPE: email is mocked). Logs identifiers only."""

    def send(self, user_id: uuid.UUID, title: str) -> None:
        logger.info("email_mock", extra={"extra_fields": {"user_id": str(user_id), "title": title}})


class NotificationService:
    """Notification rows are written in the caller's transaction; delivery is queued until `flush_sent()`
    is called after the commit, so a failed commit never sends a message for something that did not happen."""

    def __init__(self, db: Session, notifier: EmailNotifier | None = None) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.notifier = notifier or EmailNotifier()
        self._outbox: list[tuple[uuid.UUID, str]] = []

    def notify_officers(self, app: Application, kind: NotificationKind, title: str, body: str) -> int:
        """Every active officer (no assignment model in the MVP)."""
        items = [
            Notification(user_id=uid, application_id=app.id, kind=kind, title=title, body=body)
            for uid in self.repo.active_officer_ids()
        ]
        self.repo.add_all(items)
        self._outbox.extend((item.user_id, title) for item in items)
        return len(items)

    def notify_user(
        self, user_id: uuid.UUID, app: Application, kind: NotificationKind, title: str, body: str
    ) -> None:
        self.repo.add_all(
            [Notification(user_id=user_id, application_id=app.id, kind=kind, title=title, body=body)]
        )
        self._outbox.append((user_id, title))

    def flush_sent(self) -> int:
        """Deliver everything queued since the last flush. Call after the transaction committed."""
        sent = 0
        for user_id, title in self._outbox:
            self.notifier.send(user_id, title)
            sent += 1
        self._outbox.clear()
        return sent

    def list_for(self, user_id: uuid.UUID) -> tuple[list[Notification], int]:
        return self.repo.list_for_user(user_id), self.repo.unread_count(user_id)

    def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
        """Scoped to the caller: another user's notification id looks like 404."""
        item = self.repo.get_for_user(user_id, notification_id)
        if item is None:
            raise NotFound("Notification not found.")
        if item.read_at is None:
            item.read_at = datetime.now(UTC)
            self.db.commit()
        return item

    def mark_all_read(self, user_id: uuid.UUID) -> int:
        n = self.repo.mark_all_read(user_id, datetime.now(UTC))
        self.db.commit()
        return n
