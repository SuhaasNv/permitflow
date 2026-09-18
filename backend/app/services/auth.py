"""Authentication use cases."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import Unauthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.repositories.users import UserRepository


@dataclass(frozen=True)
class Token:
    access_token: str
    expires_at: datetime
    user: User


# Verified against when the email is unknown so both outcomes cost one argon2 check (timing oracle, T4).
_DUMMY_HASH = hash_password("not-a-real-password")


class AuthService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def authenticate(self, email: str, password: str) -> Token:
        user = self.users.get_by_email(email)
        # Generic message whether the email or the password is wrong (UC0-A 1a).
        ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if user is None or not user.is_active or not ok:
            raise Unauthorized("Email or password is incorrect.")
        token, expires_at = create_access_token(user.id, user.role.value)
        return Token(access_token=token, expires_at=expires_at, user=user)

    def current_user(self, user_id: uuid.UUID) -> User:
        user = self.users.get(user_id)
        if user is None or not user.is_active:
            raise Unauthorized("Invalid or missing credentials.")
        return user
