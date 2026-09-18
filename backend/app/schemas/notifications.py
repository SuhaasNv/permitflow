"""Notification schemas (FR-020, FR-021)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    kind: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime


class NotificationsOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int
