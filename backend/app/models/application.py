import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id, str_enum, utcnow
from app.models.enums import ApplicationStatus, LicenceType


class Application(TimestampMixin, Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    reference_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    operator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    licence_type: Mapped[LicenceType] = mapped_column(
        str_enum(LicenceType, "licence_type", 32),
        default=LicenceType.FOOD_ESTABLISHMENT,
        nullable=False,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        str_enum(ApplicationStatus, "application_status", 48),
        default=ApplicationStatus.DRAFT,
        nullable=False,
        index=True,
    )
    draft_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("application_revisions.id", use_alter=True, name="fk_applications_current_revision"),
        nullable=True,
    )
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Operator's optional reason when they withdraw (US-038). Shown to officers and to the operator.
    withdrawal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class ApplicationRevision(Base):
    __tablename__ = "application_revisions"
    __table_args__ = (UniqueConstraint("application_id", "revision_number", name="uq_revision_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    form_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    submitted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
