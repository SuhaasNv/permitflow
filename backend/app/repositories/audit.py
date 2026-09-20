import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.orm import Session

from app.domain.enums import ApplicationStatus
from app.models import Application, AuditEvent


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

    def feed(self, *, limit: int, before: tuple[datetime, uuid.UUID] | None = None) -> list[AuditEvent]:
        """The newest events across every application and every user change, keyset-paged on
        (created_at, id) so a page deep in the history costs the same as the first (US-072)."""
        stmt = select(AuditEvent)
        if before is not None:
            stmt = stmt.where(tuple_(AuditEvent.created_at, AuditEvent.id) < before)
        stmt = stmt.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def idle_applications(
        self, cutoff: datetime, statuses: Iterable[ApplicationStatus]
    ) -> list[tuple[Application, datetime]]:
        """Open applications (in `statuses`) whose newest audit event, or their `updated_at` when they
        have none, is older than `cutoff`, oldest first (the admin's idle list, US-070, US-086). One
        grouped query over the (application_id, created_at) index, never a row per application."""
        last = func.coalesce(func.max(AuditEvent.created_at), Application.updated_at)
        stmt = (
            select(Application, last.label("last_activity"))
            .outerjoin(AuditEvent, AuditEvent.application_id == Application.id)
            .where(Application.status.in_(list(statuses)))
            .group_by(Application.id)
            .having(last < cutoff)
            .order_by(last.asc(), Application.reference_no.asc())
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt)]

    def last_activity(self, application_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        """The newest event per application (the idle list, US-070)."""
        ids = list(application_ids)
        if not ids:
            return {}
        stmt = (
            select(AuditEvent.application_id, func.max(AuditEvent.created_at))
            .where(AuditEvent.application_id.in_(ids))
            .group_by(AuditEvent.application_id)
        )
        return {row[0]: row[1] for row in self.db.execute(stmt) if row[0] is not None}

    def count_since(self, event_type: str, since: datetime, until: datetime) -> int:
        stmt = select(func.count()).where(
            AuditEvent.event_type == event_type,
            AuditEvent.created_at >= since,
            AuditEvent.created_at < until,
        )
        return int(self.db.scalar(stmt) or 0)

    def transitions_since(self, since: datetime, until: datetime) -> list[dict[str, Any]]:
        """The `status.changed` payloads in a window (today's submissions and resubmissions)."""
        stmt = select(AuditEvent.payload).where(
            AuditEvent.event_type == "status.changed",
            AuditEvent.created_at >= since,
            AuditEvent.created_at < until,
        )
        return [dict(p) for p in self.db.scalars(stmt)]

    def purge_draft(self, application_id: uuid.UUID) -> None:
        """Remove the events of a draft that is being deleted outright (US-045). A draft was never submitted,
        so it is not part of the licensing record; the caller checked the status under a row lock."""
        self.db.execute(delete(AuditEvent).where(AuditEvent.application_id == application_id))
