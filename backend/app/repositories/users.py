import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


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
