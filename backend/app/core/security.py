"""Password hashing (argon2) and JWT access tokens (SEC-006)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.errors import Unauthorized
from app.core.settings import get_settings

_hasher = PasswordHasher()
MIN_SECRET_LENGTH = 16
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - malformed hash counts as mismatch
        return False


def _secret(value: str) -> str:
    """There is no fallback secret in any environment (SEC-006): an empty or short value is a configuration
    error, never a silent default that would make tokens forgeable."""
    if len(value) < MIN_SECRET_LENGTH:
        raise RuntimeError(f"JWT_SECRET must be set to at least {MIN_SECRET_LENGTH} characters")
    return value


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload: dict[str, Any] = {"sub": str(user_id), "role": role, "exp": expires_at, "iat": datetime.now(UTC)}
    return jwt.encode(payload, _secret(settings.jwt_secret), algorithm=ALGORITHM), expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    secret = _secret(settings.jwt_secret)
    try:
        payload: dict[str, Any] = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Your session has expired. Sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("Invalid or missing credentials.") from exc
    return payload
