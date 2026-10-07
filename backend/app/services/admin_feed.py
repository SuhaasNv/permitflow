"""The cross-application activity feed (US-072): the newest audit events with their sentence, actor
and case reference, keyset-paged."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import BadRequest
from app.domain.audit_labels import summarize
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.users import UserRepository
from app.schemas.admin import AuditFeedOut, FeedEventOut

MAX_LIMIT = 100


EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def encode_cursor(created_at: datetime, event_id: uuid.UUID) -> str:
    """Microseconds since the epoch and the id: digits and hex only, so the cursor survives a query
    string without encoding (an ISO stamp's `+` would arrive as a space)."""
    micros = (created_at.astimezone(UTC) - EPOCH) // timedelta(microseconds=1)
    return f"{micros},{event_id}"


def decode_cursor(value: str) -> tuple[datetime, uuid.UUID]:
    try:
        stamp, raw_id = value.rsplit(",", 1)
        return EPOCH + timedelta(microseconds=int(stamp)), uuid.UUID(raw_id)
    except (ValueError, OverflowError) as exc:  # a 43-digit stamp overflows timedelta (review, 21 Sep)
        raise BadRequest("The cursor is not one this feed issued.", details={"reason": "bad_cursor"}) from exc


class AdminFeedService:
    def __init__(self, db: Session) -> None:
        self.audit = AuditRepository(db)
        self.users = UserRepository(db)
        self.applications = ApplicationRepository(db)

    def feed(self, *, limit: int = 50, before: str | None = None) -> AuditFeedOut:
        limit = max(1, min(limit, MAX_LIMIT))
        cursor = decode_cursor(before) if before else None
        # One row past the page tells whether an older page exists without a count query.
        rows = self.audit.feed(limit=limit + 1, before=cursor)
        more = len(rows) > limit
        rows = rows[:limit]
        names = self.users.names(e.actor_id for e in rows if e.actor_id is not None)
        refs = self.applications.reference_numbers(
            {e.application_id for e in rows if e.application_id is not None}
        )
        events = [
            FeedEventOut(
                id=e.id,
                event_type=e.event_type,
                summary=summarize(e.event_type, e.payload),
                actor_name=names.get(e.actor_id, (None, None))[0] if e.actor_id else None,
                actor_role=names.get(e.actor_id, (None, None))[1] if e.actor_id else None,
                application_id=e.application_id,
                reference_no=refs.get(e.application_id) if e.application_id else None,
                created_at=e.created_at,
            )
            for e in rows
        ]
        last = rows[-1] if rows else None
        return AuditFeedOut(
            events=events,
            next_cursor=encode_cursor(last.created_at, last.id) if more and last is not None else None,
        )
