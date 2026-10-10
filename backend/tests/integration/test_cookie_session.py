"""Cookie sessions (US-104, ADR-017): cookie attributes, no bearer token in the body, double-submit CSRF
bound to the session, sign-out, take-over, and CORS with credentials for the listed origin only."""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.session_cookie import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, csrf_token
from app.core.settings import get_settings
from app.main import create_app
from app.models.enums import Role
from tests.factories import DEFAULT_PASSWORD, make_user

FRONTEND = "https://dev.permitflow.space"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
IPAD = "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Version/17.4 Safari/604.1"


@pytest.fixture
def cookie_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", "cookie")
    monkeypatch.setattr(settings, "cors_origins", f"{FRONTEND},https://other.permitflow.space")
    # Secure cookies are only sent over https, so the client talks to https://testserver.
    with TestClient(create_app(), base_url="https://testserver") as c:
        yield c


def _sign_in(
    c: TestClient, email: str, *, origin: str | None = FRONTEND, take_over: bool = False, ua: str = IPAD
):  # type: ignore[no-untyped-def]
    headers = {"User-Agent": ua}
    if origin:
        headers["Origin"] = origin
    body = {"email": email, "password": DEFAULT_PASSWORD, "take_over": take_over}
    return c.post(LOGIN, json=body, headers=headers)


def _set_cookie_headers(r) -> dict[str, str]:  # type: ignore[no-untyped-def]
    out: dict[str, str] = {}
    for line in r.headers.get_list("set-cookie"):
        out[line.split("=", 1)[0]] = line
    return out


def _attrs(line: str) -> set[str]:
    return {part.strip().lower() for part in line.split(";")[1:]}


def test_sign_in_sets_the_two_host_cookies_with_exact_attributes(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = _sign_in(cookie_app, "op@example.sg")
    assert r.status_code == 200
    cookies = _set_cookie_headers(r)
    assert set(cookies) == {SESSION_COOKIE, CSRF_COOKIE}
    max_age = f"max-age={get_settings().jwt_expires_minutes * 60}"
    session = _attrs(cookies[SESSION_COOKIE])
    assert session == {"path=/", "secure", "httponly", "samesite=strict", max_age}
    csrf = _attrs(cookies[CSRF_COOKIE])
    assert csrf == {"path=/", "secure", "samesite=strict", max_age}  # readable by script: no HttpOnly
    for line in cookies.values():
        assert "domain" not in line.lower()
        assert line.startswith("__Host-")


def test_body_has_no_bearer_token_and_hands_over_the_csrf_value(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = _sign_in(cookie_app, "op@example.sg")
    body = r.json()
    assert "access_token" not in body and "token_type" not in body
    session_value = cookie_app.cookies[SESSION_COOKIE]
    assert session_value not in r.text
    assert body["csrf_token"] == cookie_app.cookies[CSRF_COOKIE]
    assert body["user"]["email"] == "op@example.sg"
    me = cookie_app.get(ME).json()
    assert me["csrf_token"] == body["csrf_token"] and me["email"] == "op@example.sg"


def test_session_cookie_is_the_only_transport_in_cookie_mode(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    _sign_in(cookie_app, "op@example.sg")
    token = cookie_app.cookies[SESSION_COOKIE]
    cookie_app.cookies.clear()
    assert cookie_app.get(ME).status_code == 401
    # A bearer header is not accepted in cookie mode, even with a valid token.
    assert cookie_app.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_sign_in_needs_an_allowed_origin(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    for origin in (None, "https://evil.example", "null", "http://dev.permitflow.space"):
        r = _sign_in(cookie_app, "op@example.sg", origin=origin)
        assert r.status_code == 403, origin
        assert r.json()["error"]["code"] == "csrf_failed"
        assert not r.headers.get_list("set-cookie")
    assert _sign_in(cookie_app, "op@example.sg", origin="https://other.permitflow.space").status_code == 200


def test_unsafe_methods_need_the_csrf_header(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    path = "/api/v1/notifications/read-all"

    missing = cookie_app.post(path)
    assert missing.status_code == 403 and missing.json()["error"]["code"] == "csrf_failed"
    wrong = cookie_app.post(path, headers={CSRF_HEADER: "0" * len(csrf)})
    assert wrong.status_code == 403 and wrong.json()["error"]["code"] == "csrf_failed"
    right = cookie_app.post(path, headers={CSRF_HEADER: csrf})
    assert right.status_code == 200


def test_header_must_match_the_cookie_and_the_session(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    path = "/api/v1/notifications/read-all"

    # A planted cookie cannot help: the header is checked against the cookie and the session's own value.
    cookie_app.cookies.set(CSRF_COOKIE, "planted")
    assert cookie_app.post(path, headers={CSRF_HEADER: "planted"}).status_code == 403
    assert cookie_app.post(path, headers={CSRF_HEADER: csrf}).status_code == 403  # cookie differs from header
    cookie_app.cookies.set(CSRF_COOKIE, csrf)
    assert cookie_app.post(path, headers={CSRF_HEADER: csrf}).status_code == 200

    # Another session's valid token is rejected on this session.
    other_token = csrf_token(uuid.uuid4())
    assert other_token != csrf
    cookie_app.cookies.set(CSRF_COOKIE, other_token)
    assert cookie_app.post(path, headers={CSRF_HEADER: other_token}).status_code == 403


def test_safe_methods_need_no_csrf_header(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    _sign_in(cookie_app, "op@example.sg")
    assert cookie_app.get(ME).status_code == 200
    assert cookie_app.get("/api/v1/notifications").status_code == 200


def test_sign_out_needs_csrf_clears_both_cookies_and_ends_the_session(
    cookie_app: TestClient, db: Session
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    assert cookie_app.post("/api/v1/auth/logout").status_code == 403  # a forged sign-out is refused

    old_cookie = cookie_app.cookies[SESSION_COOKIE]
    r = cookie_app.post("/api/v1/auth/logout", headers={CSRF_HEADER: csrf})
    assert r.status_code == 204
    cleared = _set_cookie_headers(r)
    assert set(cleared) == {SESSION_COOKIE, CSRF_COOKIE}
    assert _attrs(cleared[SESSION_COOKIE]) >= {"path=/", "secure", "httponly", "samesite=strict", "max-age=0"}
    assert _attrs(cleared[CSRF_COOKIE]) >= {"path=/", "secure", "samesite=strict", "max-age=0"}
    assert "httponly" not in _attrs(cleared[CSRF_COOKIE])
    for line in cleared.values():
        assert "domain" not in line.lower()

    # The server session is over: even the old cookie, replayed, is refused.
    cookie_app.cookies.set(SESSION_COOKIE, old_cookie)
    assert cookie_app.get(ME).json()["error"]["code"] == "session_revoked"


def test_one_session_per_account_and_a_taken_over_cookie_stops_working(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", "cookie")
    monkeypatch.setattr(settings, "cors_origins", FRONTEND)
    make_user(db, "off@example.sg", Role.OFFICER)
    with (
        TestClient(create_app(), base_url="https://testserver") as first,
        TestClient(create_app(), base_url="https://testserver") as second,
    ):
        assert _sign_in(first, "off@example.sg").status_code == 200
        refused = _sign_in(second, "off@example.sg")
        assert refused.status_code == 409 and refused.json()["error"]["code"] == "session_active"
        assert not refused.headers.get_list("set-cookie")
        assert _sign_in(second, "off@example.sg", take_over=True).status_code == 200

        assert second.get(ME).status_code == 200
        r = first.get(ME)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "session_revoked"
        assert r.json()["error"]["details"]["reason"] == "taken_over"


def test_cors_allows_credentials_for_listed_origins_only(cookie_app: TestClient) -> None:
    preflight = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-csrf-token",
    }
    ok = cookie_app.options(LOGIN, headers={"Origin": FRONTEND, **preflight})
    assert ok.status_code == 200
    assert ok.headers["access-control-allow-origin"] == FRONTEND
    assert ok.headers["access-control-allow-credentials"] == "true"
    assert "x-csrf-token" in ok.headers["access-control-allow-headers"].lower()

    bad = cookie_app.options(LOGIN, headers={"Origin": "https://evil.example", **preflight})
    assert bad.status_code == 400
    assert "access-control-allow-origin" not in bad.headers  # no origin granted: the browser blocks it

    simple = cookie_app.get("/api/v1/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers


def test_token_mode_cors_and_responses_are_unchanged(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    origin = get_settings().cors_origin_list[0]
    pre = client.options(
        LOGIN,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,x-csrf-token",
        },
    )
    assert "access-control-allow-credentials" not in pre.headers
    assert "x-csrf-token" not in pre.headers.get("access-control-allow-headers", "").lower()

    r = client.post(LOGIN, json={"email": "op@example.sg", "password": DEFAULT_PASSWORD})  # no Origin needed
    assert r.status_code == 200
    assert set(r.json()) == {"access_token", "token_type", "expires_at", "user"}
    assert not r.headers.get_list("set-cookie")
    token = r.json()["access_token"]
    assert set(client.get(ME, headers={"Authorization": f"Bearer {token}"}).json()) == {
        "id",
        "email",
        "full_name",
        "role",
    }
    # Token mode ignores cookies and needs no CSRF header on writes.
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get(ME).status_code == 401
    assert (
        client.post(
            "/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 200
    )
