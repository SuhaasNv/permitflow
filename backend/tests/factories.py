"""Small helpers for building test data through the real services/repositories."""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User
from app.models.enums import Role

DEFAULT_PASSWORD = "Correct-Horse-9"


def make_user(
    db: Session, email: str, role: Role, *, password: str = DEFAULT_PASSWORD, active: bool = True
) -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0].title(),
        role=role,
        password_hash=hash_password(password),
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client, email: str, password: str = DEFAULT_PASSWORD) -> dict[str, str]:  # type: ignore[no-untyped-def]
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
