"""Sign-in sessions (US-093): one live row per account, read by id on every request."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.session import UserSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, session_id: uuid.UUID) -> UserSession | None:
        return self.db.get(UserSession, session_id)

    def live_for_user(self, user_id: uuid.UUID, now: datetime, idle: timedelta) -> UserSession | None:
        """The session that would block a new sign-in: not revoked, token not expired, seen within the
        idle window. Row-locked so two sign-ins racing for one account serialise on it."""
        stmt = (
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > now,
                UserSession.last_seen_at > now - idle,
            )
            .order_by(UserSession.created_at.desc())
            .limit(1)
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def revoke_live(self, user_id: uuid.UUID, now: datetime, reason: str) -> int:
        """Every unrevoked session of one user ends now with the reason (deactivation, US-073)."""
        rows = self.db.scalars(
            select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        ).all()
        for row in rows:
            row.revoked_at = now
            row.revoked_reason = reason
        return len(rows)

    def count_live(self, now: datetime, idle: timedelta) -> int:
        stmt = select(func.count()).where(
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
            UserSession.last_seen_at > now - idle,
        )
        return int(self.db.scalar(stmt) or 0)

    def add(self, session: UserSession) -> UserSession:
        self.db.add(session)
        return session
