"""Cookie sessions (US-104, ADR-018): cookie attributes, no bearer token in the body, double-submit CSRF
bound to the session, sign-out, take-over, and CORS with credentials for the listed origin only."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import auth as auth_routes
from app.core.security import ALGORITHM
from app.core.session_cookie import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE, csrf_token
from app.core.settings import get_settings
from app.main import create_app
from app.models import User
from app.models.enums import Role
from tests.factories import DEFAULT_PASSWORD, make_user
from tests.journeys import PDF, draft, upload
from tests.unit.test_routes_locked import _routes

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
) -> httpx.Response:
    headers = {"User-Agent": ua}
    if origin:
        headers["Origin"] = origin
    body = {"email": email, "password": DEFAULT_PASSWORD, "take_over": take_over}
    return c.post(LOGIN, json=body, headers=headers)


def _set_cookie_headers(r: httpx.Response) -> dict[str, str]:
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
    # A reload has no sign-in answer, so /me carries the session's end for the page's expiry timer (L5).
    assert me["expires_at"][:19] == body["expires_at"][:19]  # to the second


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
            "Access-Control-Request-Headers": "authorization",
        },
    )
    # The frontend sends credentials on sign-in before it knows the mode: a listed origin gets them here too.
    assert pre.headers["access-control-allow-origin"] == origin
    assert pre.headers["access-control-allow-credentials"] == "true"
    assert "x-csrf-token" not in pre.headers.get("access-control-allow-headers", "").lower()
    csrf = client.options(
        LOGIN,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-csrf-token",
        },
    )
    assert csrf.status_code == 400  # the CSRF header is a cookie-mode header only
    unlisted = client.options(
        LOGIN,
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert unlisted.status_code == 400
    assert "access-control-allow-origin" not in unlisted.headers  # no origin granted: the browser blocks it

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


def test_a_revoked_or_expired_cookie_without_the_header_is_401_not_403(
    cookie_app: TestClient, db: Session
) -> None:
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    live = cookie_app.cookies[SESSION_COOKIE]
    path = "/api/v1/notifications/read-all"
    assert cookie_app.post("/api/v1/auth/logout", headers={CSRF_HEADER: csrf}).status_code == 204

    # Revoked: the session ended, so the answer is 401 whether or not the header is there.
    cookie_app.cookies.set(SESSION_COOKIE, live)
    r = cookie_app.post(path)
    assert r.status_code == 401 and r.json()["error"]["code"] == "session_revoked"

    # Expired: a token past its `exp`.
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "role": "operator",
        "sid": str(uuid.uuid4()),
        "iat": now - timedelta(days=2),
    }
    old = jwt.encode(
        {**claims, "exp": now - timedelta(days=1)}, get_settings().jwt_secret, algorithm=ALGORITHM
    )
    cookie_app.cookies.set(SESSION_COOKIE, old)
    r = cookie_app.post(path)
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


def test_sign_out_clears_the_cookies_even_when_the_session_is_gone(
    cookie_app: TestClient, db: Session
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    live = cookie_app.cookies[SESSION_COOKIE]
    assert cookie_app.post("/api/v1/auth/logout", headers={CSRF_HEADER: csrf}).status_code == 204

    for cookie in (live, "not-a-token", None):  # revoked, malformed, missing
        cookie_app.cookies.clear()
        if cookie:
            cookie_app.cookies.set(SESSION_COOKIE, cookie)
        r = cookie_app.post("/api/v1/auth/logout", headers={CSRF_HEADER: csrf})
        assert r.status_code == 401
        cleared = _set_cookie_headers(r)
        assert set(cleared) == {SESSION_COOKIE, CSRF_COOKIE}
        assert all("max-age=0" in line.lower() for line in cleared.values())


def test_a_foreign_origin_cannot_take_over_and_the_live_session_survives(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", "cookie")
    monkeypatch.setattr(settings, "cors_origins", FRONTEND)
    make_user(db, "off@example.sg", Role.OFFICER)
    with (
        TestClient(create_app(), base_url="https://testserver") as live,
        TestClient(create_app(), base_url="https://testserver") as attacker,
    ):
        assert _sign_in(live, "off@example.sg").status_code == 200
        r = _sign_in(attacker, "off@example.sg", origin="https://evil.example", take_over=True)
        assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"
        assert not r.headers.get_list("set-cookie")
        assert live.get(ME).status_code == 200  # not revoked


def test_a_foreign_origin_does_not_count_against_the_failed_login_limiter(
    cookie_app: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    monkeypatch.setattr(auth_routes.login_limiter, "limit", 2)
    auth_routes.login_limiter.clear()
    try:
        for _ in range(5):
            assert _sign_in(cookie_app, "op@example.sg", origin="https://evil.example").status_code == 403
        # Five refusals later the real page can still sign in: they were not recorded as failures.
        assert _sign_in(cookie_app, "op@example.sg").status_code == 200
    finally:
        auth_routes.login_limiter.clear()


def test_every_unsafe_route_refuses_a_request_without_the_csrf_header(
    cookie_app: TestClient, db: Session
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    _sign_in(cookie_app, "op@example.sg")
    seen = []
    for route in _routes():
        for method in route.methods - {"GET", "HEAD", "OPTIONS"}:
            if (method, route.path) == ("POST", "/auth/login"):
                continue  # no session yet: covered by the Origin check
            url = "/api/v1" + route.path
            for name in route.param_convertors:
                url = url.replace("{" + name + "}", str(uuid.uuid4()))
            if any(p.name == "file" for p in route.dependant.body_params):
                r = cookie_app.request(method, url, files={"file": ("a.pdf", PDF, "application/pdf")})
            else:
                r = cookie_app.request(method, url, json={})
            assert r.status_code == 403, (method, route.path, r.status_code)
            assert r.json()["error"]["code"] == "csrf_failed", (method, route.path)
            seen.append((method, route.path))
    assert len(seen) > 20 and ("POST", "/applications/{application_id}/documents") in seen


def test_the_admin_step_up_sits_behind_the_csrf_check(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "adm@example.sg", Role.ADMIN, protected=True)
    csrf = _sign_in(cookie_app, "adm@example.sg").json()["csrf_token"]
    url = "/api/v1/admin/settings/max_drafts_per_user"
    body = {"value": 5, "reason": "Load from the open day", "password": "Not-The-Password-1"}

    r = cookie_app.put(url, json=body)
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"
    r = cookie_app.put(url, json=body, headers={CSRF_HEADER: csrf})
    assert r.status_code == 403 and r.json()["error"]["code"] == "step_up_failed"


def test_responses_are_never_cached_in_cookie_mode(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    assert _sign_in(cookie_app, "op@example.sg").headers["cache-control"] == "no-store"
    assert cookie_app.get(ME).headers["cache-control"] == "no-store"


def test_a_file_downloads_with_the_cookie_alone(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    h = {CSRF_HEADER: csrf}  # the writes need it; the download below sends no header at all
    app_id = draft(cookie_app, h)
    doc_id = upload(cookie_app, h, app_id, "tenancy_agreement", "tenancy.pdf", PDF).json()["document"]["id"]
    r = cookie_app.get(f"/api/v1/applications/{app_id}/documents/{doc_id}/download")
    assert r.status_code == 200 and r.content == PDF


def test_a_user_row_is_all_the_cookie_session_reads(cookie_app: TestClient, db: Session) -> None:
    """Deactivating the account ends the cookie session on the next request, as it does in token mode."""
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    _sign_in(cookie_app, "op@example.sg")
    db_user = db.get(User, user.id)
    assert db_user is not None
    db_user.is_active = False
    db.commit()
    assert cookie_app.get(ME).status_code == 401


def test_a_refusal_is_logged_with_its_reason_and_no_token_value(
    cookie_app: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    with caplog.at_level("WARNING", logger="permitflow.auth"):
        cookie_app.post("/api/v1/notifications/read-all")
        cookie_app.post("/api/v1/notifications/read-all", headers={CSRF_HEADER: "wrong" + csrf})
    fields = [r.__dict__["extra_fields"] for r in caplog.records if r.getMessage() == "csrf_failed"]
    assert [f["reason"] for f in fields] == ["header_missing", "cookie_mismatch"]
    assert all(f["user_id"] for f in fields)
    assert csrf not in caplog.text and cookie_app.cookies[SESSION_COOKIE] not in caplog.text
