import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.models.enums import Role


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def lock(self, user_id: uuid.UUID) -> User | None:
        """`SELECT ... FOR UPDATE` on the user row: the serialisation point for per-operator quotas
        (US-058), so two simultaneous creates cannot both pass a count of limit minus one."""
        return self.db.get(User, user_id, with_for_update=True)

    def add(self, user: User) -> User:
        self.db.add(user)
        return user

    def list_all(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.created_at.asc(), User.id.asc())))

    def lock_admins(self) -> list[User]:
        """`SELECT ... FOR UPDATE` on every admin row, in id order so two admins changing roles at once
        take the locks in the same order (US-073): the serialisation point for "never zero admins"."""
        stmt = select(User).where(User.role == Role.ADMIN).order_by(User.id).with_for_update()
        return list(self.db.scalars(stmt))

    def names(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, tuple[str, str]]:
        wanted = list({i for i in ids if i is not None})
        if not wanted:
            return {}
        stmt = select(User).where(User.id.in_(wanted))
        return {u.id: (u.full_name, u.role.value) for u in self.db.scalars(stmt)}
