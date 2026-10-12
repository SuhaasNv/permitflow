"""Abuse case 4 (US-105; THREAT_MODEL T14 token theft, T27 stolen sign-in, US-093, US-104): a token or
cookie that was
copied before sign-out, take-over or expiry stops working at once, in both AUTH_MODEs, on every kind of route
and for every role. A token that never belonged to a live session, or that claims more than the account has,
gets nothing either.

Already asserted elsewhere (not repeated): the reason strings of a signed-out, taken-over and idle session
(tests/integration/test_sessions.py) and the cookie-mode sign-out with a replayed cookie
(tests/integration/test_cookie_session.py).
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ALGORITHM
from app.core.session_cookie import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from app.core.settings import get_settings
from app.main import create_app
from app.models import Application, User
from app.models.enums import Role
from tests.abuse.conftest import FRONTEND
from tests.factories import DEFAULT_PASSWORD, make_user

LOGIN = "/api/v1/auth/login"
API = "/api/v1"

# One safe read per kind of route, each in front of a different guard, plus two writes.
REPLAYS = [
    ("GET", "/auth/me", {Role.OPERATOR, Role.OFFICER, Role.ADMIN}),
    ("GET", "/notifications", {Role.OPERATOR, Role.OFFICER, Role.ADMIN}),
    ("POST", "/notifications/read-all", {Role.OPERATOR, Role.OFFICER, Role.ADMIN}),
    ("POST", "/auth/logout", {Role.OPERATOR, Role.OFFICER, Role.ADMIN}),
    ("GET", "/applications", {Role.OPERATOR}),
    ("POST", "/applications", {Role.OPERATOR}),
    ("GET", "/officer/applications", {Role.OFFICER}),
    ("GET", "/admin/overview", {Role.ADMIN}),
]


class Mode:
    """Token mode (bearer header) or cookie mode (cookie pair plus the CSRF header)."""

    def __init__(self, name: str, client: TestClient) -> None:
        self.name, self.client = name, client

    def sign_in(self, email: str, *, take_over: bool = True) -> dict[str, str]:
        origin = {"Origin": FRONTEND} if self.name == "cookie" else {}
        r = self.client.post(
            LOGIN, json={"email": email, "password": DEFAULT_PASSWORD, "take_over": take_over}, headers=origin
        )
        assert r.status_code == 200, r.text
        body = r.json()
        if self.name == "token":
            return {"Authorization": f"Bearer {body['access_token']}"}
        return {
            SESSION_COOKIE: self.client.cookies[SESSION_COOKIE],
            CSRF_COOKIE: self.client.cookies[CSRF_COOKIE],
            CSRF_HEADER: body["csrf_token"],
        }

    def call(self, held: dict[str, str], method: str, path: str) -> int:
        """Send one request with only `held`, as a thief on another machine would."""
        self.client.cookies.clear()
        headers = {}
        if self.name == "token":
            headers = held
        else:
            self.client.cookies.set(SESSION_COOKIE, held[SESSION_COOKIE])
            self.client.cookies.set(CSRF_COOKIE, held[CSRF_COOKIE])
            headers = {CSRF_HEADER: held[CSRF_HEADER]}
        r = self.client.request(
            method, API + path, headers=headers, **({"json": {}} if method != "GET" else {})
        )
        self.client.cookies.clear()
        return r.status_code


@pytest.fixture(params=["token", "cookie"])
def mode(request: pytest.FixtureRequest, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> Mode:
    if request.param == "token":
        return Mode("token", client)
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", "cookie")
    monkeypatch.setattr(settings, "cors_origins", FRONTEND)
    cookie_client = TestClient(create_app(), base_url="https://testserver")
    request.addfinalizer(cookie_client.close)
    return Mode("cookie", cookie_client)


def _users(db: Session) -> dict[Role, str]:
    emails = {Role.OPERATOR: "op@example.sg", Role.OFFICER: "off@example.sg", Role.ADMIN: "adm@example.sg"}
    for role, email in emails.items():
        make_user(db, email, role, protected=role == Role.ADMIN)
    return {role: email for role, email in emails.items()}


@pytest.mark.parametrize("role", [Role.OPERATOR, Role.OFFICER, Role.ADMIN])
def test_a_copied_token_is_dead_on_every_route_after_sign_out(mode: Mode, db: Session, role: Role) -> None:
    email = _users(db)[role]
    held = mode.sign_in(email)
    live = [(m, p) for m, p, roles in REPLAYS if role in roles and p != "/auth/logout"]
    assert all(mode.call(held, m, p) in (200, 201, 204) for m, p in live), "the credential never worked"

    assert mode.call(held, "POST", "/auth/logout") == 204
    for method, path, _ in REPLAYS:
        assert mode.call(held, method, path) == 401, f"{method} {path} accepted a signed-out credential"


def test_a_replayed_write_after_sign_out_changes_nothing(mode: Mode, db: Session) -> None:
    email = _users(db)[Role.OPERATOR]
    held = mode.sign_in(email)
    assert mode.call(held, "POST", "/auth/logout") == 204
    assert mode.call(held, "POST", "/applications") == 401
    assert db.scalar(select(Application)) is None


def test_signing_in_again_does_not_revive_the_old_credential(mode: Mode, db: Session) -> None:
    email = _users(db)[Role.OPERATOR]
    first = mode.sign_in(email)
    assert mode.call(first, "POST", "/auth/logout") == 204
    second = mode.sign_in(email)
    assert mode.call(second, "GET", "/auth/me") == 200
    assert mode.call(first, "GET", "/auth/me") == 401


def test_a_credential_taken_over_elsewhere_stops_working(mode: Mode, db: Session) -> None:
    email = _users(db)[Role.OPERATOR]
    stolen = mode.sign_in(email)
    mine = mode.sign_in(email, take_over=True)  # the owner signs in again on another device
    assert mode.call(stolen, "GET", "/auth/me") == 401
    assert mode.call(mine, "GET", "/auth/me") == 200


def test_a_deactivated_account_loses_the_session_on_the_next_request(mode: Mode, db: Session) -> None:
    email = _users(db)[Role.OPERATOR]
    held = mode.sign_in(email)
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_active = False
    db.commit()
    assert mode.call(held, "GET", "/auth/me") == 401


# ---- tokens that never belonged to a live session ----


def _jwt(claims: dict[str, object], secret: str, algorithm: str = ALGORITHM) -> str:
    now = datetime.now(UTC)
    return jwt.encode({"iat": now, "exp": now + timedelta(hours=1), **claims}, secret, algorithm=algorithm)


def _forged(db: Session, user: User) -> dict[str, str]:
    secret = get_settings().jwt_secret
    sub, sid = str(user.id), str(uuid.uuid4())
    return {
        "unknown session": _jwt({"sub": sub, "role": "operator", "sid": sid}, secret),
        "wrong secret": _jwt(
            {"sub": sub, "role": "operator", "sid": sid}, "another-secret-of-32-characters!!"
        ),
        "alg none": jwt.encode({"sub": sub, "role": "admin", "sid": sid}, key="", algorithm="none"),
        "no sid": _jwt({"sub": sub, "role": "operator"}, secret),
        "no sub": _jwt({"role": "operator", "sid": sid}, secret),
        "not a uuid": _jwt({"sub": "1 OR 1=1", "role": "operator", "sid": sid}, secret),
        "truncated": _jwt({"sub": sub, "sid": sid}, secret)[:-4],
    }


def test_tokens_that_never_belonged_to_a_live_session_get_nothing(mode: Mode, db: Session) -> None:
    emails = _users(db)
    user = db.scalar(select(User).where(User.email == emails[Role.OPERATOR]))
    assert user is not None
    for label, token in _forged(db, user).items():
        if mode.name == "token":
            held = {"Authorization": f"Bearer {token}"}
        else:
            held = {SESSION_COOKIE: token, CSRF_COOKIE: "x", CSRF_HEADER: "x"}
        for method, path in (("GET", "/auth/me"), ("GET", "/applications"), ("GET", "/admin/overview")):
            assert mode.call(held, method, path) == 401, f"{label}: {method} {path}"


def test_a_role_claim_in_the_token_is_not_what_decides_the_role(mode: Mode, db: Session) -> None:
    """Even a token signed with the server's own key cannot promote its holder: the role is read from the
    user row on every request (T14)."""
    emails = _users(db)
    held = mode.sign_in(emails[Role.OPERATOR])
    token = held["Authorization"].split()[1] if mode.name == "token" else held[SESSION_COOKIE]
    claims = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    promoted = _jwt({**claims, "role": "admin"}, get_settings().jwt_secret)
    held_up = (
        {"Authorization": f"Bearer {promoted}"}
        if mode.name == "token"
        else {**held, SESSION_COOKIE: promoted}
    )
    assert mode.call(held_up, "GET", "/admin/overview") == 403
    assert mode.call(held_up, "GET", "/applications") == 200


def test_a_valid_session_cannot_be_worn_by_another_account(mode: Mode, db: Session) -> None:
    """The token's sub and the session's owner must agree: A's session id under the admin's sub is refused."""
    emails = _users(db)
    held = mode.sign_in(emails[Role.OPERATOR])
    token = held["Authorization"].split()[1] if mode.name == "token" else held[SESSION_COOKIE]
    claims = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
    admin = db.scalar(select(User).where(User.email == emails[Role.ADMIN]))
    assert admin is not None
    swapped = _jwt({**claims, "sub": str(admin.id), "role": "admin"}, get_settings().jwt_secret)
    held_up = (
        {"Authorization": f"Bearer {swapped}"} if mode.name == "token" else {**held, SESSION_COOKIE: swapped}
    )
    assert mode.call(held_up, "GET", "/admin/overview") == 401
