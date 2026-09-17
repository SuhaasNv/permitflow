import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent


class AuditRepository:
    """Append-only: there is deliberately no update or delete method (SEC-009)."""

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
