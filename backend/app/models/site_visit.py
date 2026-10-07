import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id, str_enum
from app.models.enums import SiteVisitProposalOutcome, SiteVisitSlot, SiteVisitStatus


class SiteVisit(TimestampMixin, Base):
    """The appointment for one visit of an application (US-084). `date` and `slot` are the current
    proposal's, and the confirmed ones once `status` is confirmed."""

    __tablename__ = "site_visits"
    __table_args__ = (
        UniqueConstraint("application_id", "visit_no", name="uq_site_visits_application_visit"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id"), nullable=False, index=True
    )
    visit_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[SiteVisitStatus] = mapped_column(
        str_enum(SiteVisitStatus, "site_visit_status", 16), nullable=False, default=SiteVisitStatus.PROPOSED
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    slot: Mapped[SiteVisitSlot] = mapped_column(
        str_enum(SiteVisitSlot, "site_visit_slot", 16), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SiteVisitProposal(TimestampMixin, Base):
    """One round of the appointment: who proposed which date and slot, why, and what became of it."""

    __tablename__ = "site_visit_proposals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    site_visit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("site_visits.id"), nullable=False, index=True)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    author_role: Mapped[str] = mapped_column(String(16), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    slot: Mapped[SiteVisitSlot] = mapped_column(
        str_enum(SiteVisitSlot, "site_visit_slot", 16), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[SiteVisitProposalOutcome] = mapped_column(
        str_enum(SiteVisitProposalOutcome, "site_visit_proposal_outcome", 16),
        nullable=False,
        default=SiteVisitProposalOutcome.PENDING,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
