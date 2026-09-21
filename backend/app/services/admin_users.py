"""User management (US-073): the directory, role changes, deactivation and reactivation, and the
command-line style account creation the owner asked for in the page. Every change is an audit row
with no application; the rules that keep the platform usable are enforced under a lock."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.core.security import hash_password
from app.models import User
from app.models.enums import Role
from app.repositories.audit import AuditRepository
from app.repositories.concurrency import DeadlockError, deadlock_as_error
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository
from app.schemas.admin import AdminUserOut, AdminUsersOut


class LastAdmin(Conflict):
    code = "last_admin"


class SelfChange(Conflict):
    code = "self_change"


class ProtectedAccount(Conflict):
    code = "protected_account"


class TryAgain(Conflict):
    code = "try_again"


@dataclass(frozen=True)
class Change:
    role: Role | None = None
    is_active: bool | None = None


class AdminUserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)
        self.sessions = SessionRepository(db)

    def directory(self, caller: User) -> AdminUsersOut:
        rows = self.users.list_all()
        return AdminUsersOut(users=[AdminUserOut.model_validate(u) for u in rows], self_id=caller.id)

    def change(self, caller: User, user_id: uuid.UUID, change: Change) -> AdminUserOut:
        """Role and active flag under `SELECT ... FOR UPDATE` on the admin rows, so two administrators
        cannot each demote the other and leave nobody. Self-change wins over the other refusals: an
        admin editing their own row learns that first, whatever else would apply."""
        if change.role is None and change.is_active is None:
            raise ValidationFailed("Nothing to change.", details={"fields": ["role", "is_active"]})
        if user_id == caller.id:
            raise SelfChange("You cannot change your own account.")
        try:
            with deadlock_as_error():
                self._apply(caller, user_id, change)
        except DeadlockError as exc:
            self.db.rollback()
            raise TryAgain("Another administrator changed users at the same time. Try again.") from exc
        target = self.users.get(user_id)
        if target is None:  # pragma: no cover - the row was locked and committed a moment ago
            raise NotFound("User not found.")
        self.db.refresh(target)
        return AdminUserOut.model_validate(target)

    def _apply(self, caller: User, user_id: uuid.UUID, change: Change) -> None:
        admins = {u.id: u for u in self.users.lock_admins()}
        target = self.users.lock(user_id)
        if target is None:
            raise NotFound("User not found.")
        if target.is_protected:
            raise ProtectedAccount("This is a protected demonstration account; it cannot be changed.")
        new_role = change.role if change.role is not None else target.role
        new_active = change.is_active if change.is_active is not None else target.is_active
        # Would the change leave no active administrator?
        if target.role == Role.ADMIN and (new_role != Role.ADMIN or not new_active):
            others = [u for uid, u in admins.items() if uid != target.id and u.is_active]
            if not others:
                raise LastAdmin("This is the last active administrator; it cannot be changed.")
        if change.role is not None and change.role != target.role:
            self.audit.record(
                application_id=None,
                actor_id=caller.id,
                event_type="user.role_changed",
                payload={
                    "user_id": str(target.id),
                    "email": target.email,
                    "from": target.role.value,
                    "to": change.role.value,
                },
            )
            target.role = change.role
        if change.is_active is not None and change.is_active != target.is_active:
            self.audit.record(
                application_id=None,
                actor_id=caller.id,
                event_type="user.deactivated" if not change.is_active else "user.reactivated",
                payload={"user_id": str(target.id), "email": target.email},
            )
            target.is_active = change.is_active
            if not change.is_active:
                # The live session ends with the account, so a reactivation inside the idle window never
                # revives a token issued before it, and a sign-in meanwhile meets no ghost (review, 21 Sep).
                self.sessions.revoke_live(target.id, datetime.now(UTC), "deactivated")
        self.db.commit()

    def create(self, caller: User, *, email: str, full_name: str, role: Role, password: str) -> AdminUserOut:
        """A new account from the users page (the owner's request), the same rules as the command line."""
        normalised = email.strip().lower()
        if self.users.get_by_email(normalised) is not None:
            raise Conflict("An account with this email already exists.", details={"reason": "email_taken"})
        user = self.users.add(
            User(
                email=normalised,
                full_name=full_name.strip(),
                role=role,
                password_hash=hash_password(password),
                is_active=True,
                is_protected=False,
            )
        )
        self.db.flush()
        self.audit.record(
            application_id=None,
            actor_id=caller.id,
            event_type="user.created",
            payload={"user_id": str(user.id), "email": user.email, "role": role.value},
        )
        self.db.commit()
        self.db.refresh(user)
        return AdminUserOut.model_validate(user)
