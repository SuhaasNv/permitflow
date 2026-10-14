import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class PlatformSetting(Base):
    """One administrator override of an environment default (US-101). A missing row means "follow the
    environment". The history of changes is the audit trail (`settings.changed`, `settings.reverted`),
    not a second table."""

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    # A JSON scalar: a whole number, a boolean or a short choice string, typed by the setting's spec.
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
