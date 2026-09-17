import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import auth as auth_module
from app.models.enums import Role
from tests.factories import DEFAULT_PASSWORD, login, make_user


def test_login_returns_token_with_role_claim(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = client.post("/api/v1/auth/login", json={"email": "op@example.sg", "password": DEFAULT_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "operator"
    assert body["token_type"] == "bearer"
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["role"] == "operator"
    assert claims["sub"] == body["user"]["id"]


def test_wrong_password_is_generic_401(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = client.post("/api/v1/auth/login", json={"email": "op@example.sg", "password": "nope"})
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "unauthorized", "message": "Email or password is incorrect."}}
    r2 = client.post("/api/v1/auth/login", json={"email": "ghost@example.sg", "password": "nope"})
    assert r2.status_code == 401
    assert r2.json() == r.json()


def test_inactive_user_cannot_login(client: TestClient, db: Session) -> None:
    make_user(db, "old@example.sg", Role.OFFICER, active=False)
    r = client.post("/api/v1/auth/login", json={"email": "old@example.sg", "password": DEFAULT_PASSWORD})
    assert r.status_code == 401


def test_me_requires_token_and_returns_user(client: TestClient, db: Session) -> None:
    make_user(db, "off@example.sg", Role.OFFICER)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me").json()["error"]["code"] == "unauthorized"
    headers = login(client, "off@example.sg")
    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "off@example.sg"
    assert r.json()["role"] == "officer"
    assert "password_hash" not in r.json()


def test_garbage_token_is_401(client: TestClient) -> None:
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401


def test_login_validation_error_shape(client: TestClient) -> None:
    r = client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": ""})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_failed"
    assert r.json()["error"]["details"]["fields"]


def test_rate_limit_after_failed_attempts(client: TestClient, db: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    make_user(db, "op@example.sg", Role.OPERATOR)
    limiter = auth_module.login_limiter
    monkeypatch.setattr(limiter, "limit", 3)
    limiter.clear()
    for _ in range(3):
        assert (
            client.post("/api/v1/auth/login", json={"email": "op@example.sg", "password": "bad"}).status_code
            == 401
        )
    r = client.post("/api/v1/auth/login", json={"email": "op@example.sg", "password": DEFAULT_PASSWORD})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    limiter.clear()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "op@example.sg", "password": DEFAULT_PASSWORD}
        ).status_code
        == 200
    )
