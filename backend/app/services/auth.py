"""Authentication use cases: sign in, the per-request session check, sign out (US-001, US-093)."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import SessionActive, SessionRevoked, Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.core.settings import get_settings
from app.models import User, UserSession
from app.repositories.audit import AuditRepository
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository


@dataclass(frozen=True)
class Token:
    access_token: str
    expires_at: datetime
    user: User


# Verified against when the email is unknown so both outcomes cost one argon2 check (timing oracle, T4).
_DUMMY_HASH = hash_password("not-a-real-password")

# "Seen" is written at most this often per session: the per-request check stays one indexed read and
# the idle limit is accurate to the minute, which is all a 60-minute window needs.
TOUCH_INTERVAL = timedelta(seconds=60)

REVOKED_MESSAGES = {
    "taken_over": "Your session ended: this account signed in on another device.",
    "signed_out": "You signed out. Sign in again to continue.",
    "idle": "Your session ended after {minutes} minutes without activity. Sign in again to continue.",
    "deactivated": "Your account was deactivated by an administrator.",
}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AuthService:
    def __init__(self, db: Session, *, clock: Callable[[], datetime] = _utcnow) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.audit = AuditRepository(db)
        self.clock = clock
        self.idle = timedelta(minutes=get_settings().session_idle_minutes)

    def authenticate(self, email: str, password: str, *, device: str, take_over: bool = False) -> Token:
        """One live session per account (US-093): a second sign-in is refused with the other device's
        label unless the caller asks to take over, which revokes the other session and audits it.
        The session check runs only after the password is right, so a wrong password learns nothing."""
        user = self.users.get_by_email(email)
        # Generic message whether the email or the password is wrong (UC0-A 1a).
        ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if user is None or not user.is_active or not ok:
            raise Unauthorized("Email or password is incorrect.")
        now = self.clock()
        # The user row is the serialisation point: `FOR UPDATE` on the live session locks nothing when
        # there is none, so two first sign-ins racing would both pass (review finding, 21 Sep).
        self.users.lock(user.id)
        other = self.sessions.live_for_user(user.id, now, self.idle)
        if other is not None and not take_over:
            self.db.rollback()
            raise SessionActive(
                f"This account is signed in on {other.device_label}.",
                details={"device": other.device_label, "last_seen_at": other.last_seen_at.isoformat()},
            )
        session = self.sessions.add(
            UserSession(user_id=user.id, device_label=device, last_seen_at=now, expires_at=now)
        )
        if other is not None:
            other.revoked_at = now
            other.revoked_reason = "taken_over"
            self.audit.record(
                application_id=None,
                actor_id=user.id,
                event_type="user.session_taken_over",
                payload={
                    "from_device": other.device_label,
                    "to_device": device,
                    "last_seen_at": other.last_seen_at.isoformat(),
                },
            )
        self.db.flush()
        token, expires_at = create_access_token(user.id, user.role.value, session.id)
        session.expires_at = expires_at
        self.db.commit()
        return Token(access_token=token, expires_at=expires_at, user=user)

    def current_user(self, user_id: uuid.UUID, session_id: uuid.UUID) -> User:
        """The per-request check: the user row (role, active flag) and the session row (revoked, idle).
        A session past the idle limit is closed here, the first time it is seen again."""
        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise Unauthorized("Invalid or missing credentials.")
        session = self.sessions.get(session_id)
        if session is None or session.user_id != user.id:
            raise Unauthorized("Invalid or missing credentials.")
        now = self.clock()
        if session.is_revoked:
            raise self._revoked(session)
        if session.last_seen_at + self.idle <= now:
            session.revoked_at = now
            session.revoked_reason = "idle"
            self.db.commit()
            raise self._revoked(session)
        if now - session.last_seen_at >= TOUCH_INTERVAL:
            session.last_seen_at = now
            self.db.commit()
        return user

    def sign_out(self, user: User, session_id: uuid.UUID) -> None:
        session = self.sessions.get(session_id)
        if session is None or session.user_id != user.id or session.is_revoked:
            return
        session.revoked_at = self.clock()
        session.revoked_reason = "signed_out"
        self.audit.record(
            application_id=None,
            actor_id=user.id,
            event_type="user.signed_out",
            payload={"device": session.device_label},
        )
        self.db.commit()

    def live_count(self) -> int:
        return self.sessions.count_live(self.clock(), self.idle)

    def _revoked(self, session: UserSession) -> SessionRevoked:
        reason = session.revoked_reason or "signed_out"
        at = session.revoked_at.isoformat() if session.revoked_at else None
        message = REVOKED_MESSAGES.get(reason, REVOKED_MESSAGES["signed_out"])
        minutes = int(self.idle.total_seconds() // 60)
        return SessionRevoked(message.format(minutes=minutes), details={"reason": reason, "at": at})
