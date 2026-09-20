import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
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


class ClarificationResponse(TimestampMixin, Base):
    """The operator's answer to one request (US-065): one per request, drafted then sent."""

    __tablename__ = "clarification_responses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clarification_requests.id"), nullable=False, unique=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClarificationAttachment(Base):
    """Evidence on a response (US-065): the document upload rules, three per response, removable
    until sent."""

    __tablename__ = "clarification_attachments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("clarification_responses.id"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
