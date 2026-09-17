import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id, str_enum
from app.models.enums import DocumentType, FeedbackResolution, FeedbackTargetType


class Feedback(TimestampMixin, Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id"), nullable=False, index=True
    )
    raised_in_revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("application_revisions.id"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    target_type: Mapped[FeedbackTargetType] = mapped_column(
        str_enum(FeedbackTargetType, "feedback_target_type", 16),
        nullable=False,
    )
    section_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    document_type: Mapped[DocumentType | None] = mapped_column(
        str_enum(DocumentType, "document_type", 32), nullable=True
    )
    released_to_operator_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    template_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[FeedbackResolution] = mapped_column(
        str_enum(FeedbackResolution, "feedback_resolution", 16),
        default=FeedbackResolution.OPEN,
        nullable=False,
    )
    addressed_in_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("application_revisions.id"), nullable=True
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
