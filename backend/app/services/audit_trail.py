"""Audit trail read side (FR-025, ADR-008): every event on an application with a plain-language summary."""

import uuid

from sqlalchemy.orm import Session

from app.domain.audit_labels import summarize
from app.models import User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.users import UserRepository
from app.schemas.officer import AuditEventOut, AuditTrailOut


class AuditTrailService:
    def __init__(self, db: Session) -> None:
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)
        self.users = UserRepository(db)

    def for_application(self, officer: User, application_id: uuid.UUID) -> AuditTrailOut:
        app = self.applications.get_for(officer, application_id)
        events = self.audit.list_for_application(app.id)
        names: dict[uuid.UUID, tuple[str, str]] = {}
        out: list[AuditEventOut] = []
        for e in events:
            actor: tuple[str, str] | None = None
            if e.actor_id is not None:
                if e.actor_id not in names:
                    u = self.users.get(e.actor_id)
                    names[e.actor_id] = (u.full_name, u.role.value) if u else ("", "")
                actor = names[e.actor_id]
            out.append(
                AuditEventOut(
                    id=e.id,
                    event_type=e.event_type,
                    summary=summarize(e.event_type, e.payload),
                    actor_name=actor[0] if actor else None,
                    actor_role=actor[1] if actor else None,
                    payload=dict(e.payload),
                    created_at=e.created_at,
                )
            )
        return AuditTrailOut(application_id=app.id, events=out)
