import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id


class AuditEvent(TimestampMixin, Base):
    """Append-only for submitted applications: no update path anywhere, and the only delete path is the
    draft purge in `AuditRepository.purge_draft` (SEC-009, US-045), enforced by a layering test."""

    __tablename__ = "audit_events"
    # The admin overview and feed indexes of migration 0013, declared so autogenerate keeps them.
    __table_args__ = (
        Index("ix_audit_events_application_created", "application_id", "created_at"),
        Index("ix_audit_events_created_id", "created_at", "id"),
        Index("ix_audit_events_type_created", "event_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id"), nullable=True, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
