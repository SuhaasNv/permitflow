import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id, str_enum
from app.models.enums import ChecklistResult, ChecklistStatus, ClarificationStatus


class Checklist(TimestampMixin, Base):
    """The inspection record of one visit (US-060): a draft while the officer works, frozen at
    submit. One per (application, visit number); the current one is the highest visit number."""

    __tablename__ = "checklists"
    __table_args__ = (UniqueConstraint("application_id", "visit_no", name="uq_checklists_application_visit"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id"), nullable=False, index=True
    )
    visit_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ChecklistStatus] = mapped_column(
        str_enum(ChecklistStatus, "checklist_status", 16), nullable=False, default=ChecklistStatus.DRAFT
    )
    # Optimistic token for the draft save (US-061): every save bumps it, a stale one is refused.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # The last accepted save id, so a replayed request answers with the current state (US-061).
    last_save_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChecklistItem(Base):
    """One template item on one checklist. `result`, `comment` and `needs_clarification` freeze at
    submit; `clarification_status` keeps changing through the rounds (US-064 to US-066)."""

    __tablename__ = "checklist_items"
    __table_args__ = (UniqueConstraint("checklist_id", "item_key", name="uq_checklist_items_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    checklist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("checklists.id"), nullable=False, index=True)
    item_key: Mapped[str] = mapped_column(String(48), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[ChecklistResult] = mapped_column(
        str_enum(ChecklistResult, "checklist_result", 16),
        nullable=False,
        default=ChecklistResult.NOT_ASSESSED,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_clarification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clarification_status: Mapped[ClarificationStatus] = mapped_column(
        str_enum(ClarificationStatus, "clarification_status", 16),
        nullable=False,
        default=ClarificationStatus.NONE,
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
