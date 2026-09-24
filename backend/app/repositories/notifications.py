import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import Notification, User
from app.models.enums import Role


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_all(self, items: list[Notification]) -> None:
        self.db.add_all(items)

    def list_for_user(self, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def get_for_user(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
        return self.db.scalar(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )

    def unread_count(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        return int(self.db.scalar(stmt) or 0)

    def mark_all_read(self, user_id: uuid.UUID, at: datetime) -> int:
        result = self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=at)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    def delete_for_user(self, user_id: uuid.UUID) -> None:
        self.db.execute(delete(Notification).where(Notification.user_id == user_id))

    def active_officer_ids(self) -> list[uuid.UUID]:
        stmt = select(User.id).where(User.role == Role.OFFICER, User.is_active.is_(True))
        return list(self.db.scalars(stmt))
