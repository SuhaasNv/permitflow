import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuditEvent


class AuditRepository:
    """Append-only for the licensing record: no update method, and the one delete path is `purge_draft`
    (SEC-009, US-045). A layering test keeps every other module from touching `AuditEvent` rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        application_id: uuid.UUID | None,
        actor_id: uuid.UUID | None,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            application_id=application_id, actor_id=actor_id, event_type=event_type, payload=payload or {}
        )
        self.db.add(event)
        return event

    def list_for_application(self, application_id: uuid.UUID) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.application_id == application_id)
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
        return list(self.db.scalars(stmt))

    def purge_draft(self, application_id: uuid.UUID) -> None:
        """Remove the events of a draft that is being deleted outright (US-045). A draft was never submitted,
        so it is not part of the licensing record; the caller checked the status under a row lock."""
        self.db.execute(delete(AuditEvent).where(AuditEvent.application_id == application_id))
