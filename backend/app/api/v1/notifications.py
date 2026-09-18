"""In-app notifications (FR-020, FR-021): every role reads only its own."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.notifications import NotificationOut, NotificationsOut
from app.services.notifications import NotificationService

router = APIRouter(prefix="/notifications")


@router.get("", response_model=NotificationsOut)
def list_notifications(user: CurrentUser, db: DbSession) -> NotificationsOut:
    items, unread = NotificationService(db).list_for(user.id)
    return NotificationsOut(items=[NotificationOut.model_validate(i) for i in items], unread_count=unread)


@router.post("/read-all", response_model=NotificationsOut)
def mark_all_read(user: CurrentUser, db: DbSession) -> NotificationsOut:
    service = NotificationService(db)
    service.mark_all_read(user.id)
    items, unread = service.list_for(user.id)
    return NotificationsOut(items=[NotificationOut.model_validate(i) for i in items], unread_count=unread)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: uuid.UUID, user: CurrentUser, db: DbSession) -> NotificationOut:
    return NotificationOut.model_validate(NotificationService(db).mark_read(user.id, notification_id))
