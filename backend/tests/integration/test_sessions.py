"""One live session per account (US-093): refusal, take-over, revocation, idle expiry, sign-out."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import SessionRevoked
from app.core.security import create_access_token
from app.core.settings import get_settings
from app.models import AuditEvent, UserSession
from app.models.enums import Role
from app.services.auth import AuthService
from tests.factories import DEFAULT_PASSWORD, make_user

IPAD = (
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4 Mobile/15E148 Safari/604.1"
)
MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


def _sign_in(client: TestClient, email: str, ua: str, *, take_over: bool = False):  # type: ignore[no-untyped-def]
    body = {"email": email, "password": DEFAULT_PASSWORD}
    if take_over:
        body["take_over"] = True
    return client.post("/api/v1/auth/login", json=body, headers={"User-Agent": ua})


def _auth(r) -> dict[str, str]:  # type: ignore[no-untyped-def]
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_second_sign_in_is_refused_and_names_the_other_device(client: TestClient, db: Session) -> None:
    make_user(db, "off@example.sg", Role.OFFICER)
    first = _sign_in(client, "off@example.sg", IPAD)
    assert first.status_code == 200
    claims = jwt.decode(first.json()["access_token"], options={"verify_signature": False})
    assert uuid.UUID(claims["sid"])

    second = _sign_in(client, "off@example.sg", MAC)
    assert second.status_code == 409
    err = second.json()["error"]
    assert err["code"] == "session_active"
    assert err["details"]["device"] == "Safari on iPad"
    assert err["details"]["last_seen_at"]
    # The first device keeps working; a refused sign-in changes nothing.
    assert client.get("/api/v1/auth/me", headers=_auth(first)).status_code == 200
    # No raw user agent anywhere in the session row.
    rows = db.scalars(select(UserSession)).all()
    assert [r.device_label for r in rows] == ["Safari on iPad"]


def test_take_over_revokes_the_other_device_and_audits(client: TestClient, db: Session) -> None:
    user = make_user(db, "off@example.sg", Role.OFFICER)
    ipad = _sign_in(client, "off@example.sg", IPAD)
    laptop = _sign_in(client, "off@example.sg", MAC, take_over=True)
    assert laptop.status_code == 200

    # The laptop works; the iPad's next request is a 401 that says why.
    assert client.get("/api/v1/auth/me", headers=_auth(laptop)).status_code == 200
    r = client.get("/api/v1/auth/me", headers=_auth(ipad))
    assert r.status_code == 401
    err = r.json()["error"]
    assert err["code"] == "session_revoked"
    assert err["details"]["reason"] == "taken_over"
    assert err["details"]["at"]
    assert "another device" in err["message"]

    events = db.scalars(select(AuditEvent).where(AuditEvent.event_type == "user.session_taken_over")).all()
    assert len(events) == 1
    assert events[0].actor_id == user.id
    assert events[0].application_id is None
    assert events[0].payload["from_device"] == "Safari on iPad"
    assert events[0].payload["to_device"] == "Chrome on Mac"
    assert "Mozilla" not in str(events[0].payload)


def test_wrong_password_never_reveals_a_live_session(client: TestClient, db: Session) -> None:
    make_user(db, "off@example.sg", Role.OFFICER)
    assert _sign_in(client, "off@example.sg", IPAD).status_code == 200
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "off@example.sg", "password": "wrong", "take_over": True},
        headers={"User-Agent": MAC},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"
    assert db.scalar(select(UserSession).where(UserSession.revoked_at.is_not(None))) is None


def test_sign_out_revokes_the_session_and_audits(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = _sign_in(client, "op@example.sg", IPAD)
    headers = _auth(r)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    again = client.get("/api/v1/auth/me", headers=headers)
    assert again.status_code == 401
    assert again.json()["error"]["code"] == "session_revoked"
    assert again.json()["error"]["details"]["reason"] == "signed_out"
    # A second sign-out with the dead token is the same 401, not a 500.
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 401
    assert db.scalar(select(AuditEvent).where(AuditEvent.event_type == "user.signed_out")) is not None
    # After signing out, the account is free: a plain sign-in needs no take-over.
    assert _sign_in(client, "op@example.sg", MAC).status_code == 200


def test_idle_session_ends_by_itself(client: TestClient, db: Session) -> None:
    user = make_user(db, "off@example.sg", Role.OFFICER)
    r = _sign_in(client, "off@example.sg", IPAD)
    sid = uuid.UUID(jwt.decode(r.json()["access_token"], options={"verify_signature": False})["sid"])
    later = datetime.now(UTC) + timedelta(minutes=61)
    with pytest.raises(SessionRevoked) as info:
        AuthService(db, clock=lambda: later).current_user(user.id, sid)
    assert info.value.details == {"reason": "idle", "at": later.isoformat()}
    assert info.value.message == "Your session ended after 60 minutes without activity. Sign in again to continue."
    # Once idle, the account is free for the next device without a take-over.
    assert _sign_in(client, "off@example.sg", MAC).status_code == 200


def test_activity_refreshes_seen_and_keeps_the_session_alive(db: Session) -> None:
    user = make_user(db, "off@example.sg", Role.OFFICER)
    start = datetime.now(UTC)
    token = AuthService(db, clock=lambda: start).authenticate(
        "off@example.sg", DEFAULT_PASSWORD, device="Safari on iPad"
    )
    sid = uuid.UUID(jwt.decode(token.access_token, options={"verify_signature": False})["sid"])
    # Seen 50 minutes in: refreshed, so 50 minutes after that is still inside the window.
    AuthService(db, clock=lambda: start + timedelta(minutes=50)).current_user(user.id, sid)
    AuthService(db, clock=lambda: start + timedelta(minutes=100)).current_user(user.id, sid)
    row = db.get(UserSession, sid)
    assert row is not None
    assert row.last_seen_at >= start + timedelta(minutes=100)


def test_token_without_a_session_claim_is_refused(client: TestClient, db: Session) -> None:
    """Tokens from before US-093 (no `sid`) and tokens whose session belongs to someone else."""
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    other = make_user(db, "other@example.sg", Role.OPERATOR)
    legacy = jwt.encode(
        {"sub": str(user.id), "role": "operator", "exp": datetime.now(UTC) + timedelta(hours=1)},
        get_settings().jwt_secret,
        algorithm="HS256",
    )
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {legacy}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"

    theirs = _sign_in(client, "other@example.sg", IPAD)
    sid = uuid.UUID(jwt.decode(theirs.json()["access_token"], options={"verify_signature": False})["sid"])
    forged, _ = create_access_token(user.id, "operator", sid)
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"
    # The genuine holder is unaffected.
    assert client.get("/api/v1/auth/me", headers=_auth(theirs)).json()["id"] == str(other.id)


def test_every_role_holds_one_session(client: TestClient, db: Session) -> None:
    for email, role in (("op@example.sg", Role.OPERATOR), ("adm@example.sg", Role.ADMIN)):
        make_user(db, email, role)
        assert _sign_in(client, email, IPAD).status_code == 200
        assert _sign_in(client, email, MAC).status_code == 409
        assert _sign_in(client, email, MAC, take_over=True).status_code == 200


def test_sessions_gauge_counts_live_sessions(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    op = _sign_in(client, "op@example.sg", IPAD)
    _sign_in(client, "off@example.sg", MAC)
    assert AuthService(db).live_count() == 2
    client.post("/api/v1/auth/logout", headers=_auth(op))
    assert AuthService(db).live_count() == 1
    assert AuthService(db, clock=lambda: datetime.now(UTC) + timedelta(minutes=61)).live_count() == 0
