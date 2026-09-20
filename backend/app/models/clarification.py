import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id


class ClarificationRequest(TimestampMixin, Base):
    """The officer's question on one flagged checklist item, one row per round (US-063 to US-066).
    Round 1 is created and released when the checklist is submitted; later rounds are created by
    "Still needs clarification" and released by "Request another round"."""

    __tablename__ = "clarification_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checklist_items.id"), nullable=False, index=True)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
