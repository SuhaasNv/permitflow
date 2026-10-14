"""Abuse case 3 (US-105; THREAT_MODEL T12 CSRF, US-104, ADR-018): in AUTH_MODE=cookie a
page on another origin can make the browser send the session cookie, but not the CSRF header.

Already asserted elsewhere and not repeated here (tests/integration/test_cookie_session.py):
  - every unsafe route refuses a request with no X-CSRF-Token (`test_every_unsafe_route_refuses...`);
  - sign-in refuses a missing, foreign, `null` and http Origin (`test_sign_in_needs_an_allowed_origin`);
  - a planted cookie and another session's token fail (`test_header_must_match_the_cookie_and_the_session`);
  - a foreign origin cannot take over a live session (`test_a_foreign_origin_cannot_take_over...`).
This file adds the wrong-token and forged-content-type sweeps over every unsafe route, a token that belonged
to an earlier session, and Origin values that only look like the frontend.
"""

import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.session_cookie import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from app.models.enums import Role
from tests.abuse.conftest import FRONTEND, fingerprint
from tests.factories import DEFAULT_PASSWORD, make_user
from tests.journeys import PDF
from tests.unit.test_routes_locked import _routes

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def _sign_in(
    c: TestClient, email: str, origin: str | None = FRONTEND, take_over: bool = False
) -> httpx.Response:
    headers = {"Origin": origin} if origin else {}
    body = {"email": email, "password": DEFAULT_PASSWORD, "take_over": take_over}
    return c.post(LOGIN, json=body, headers=headers)


def _unsafe_routes() -> list[tuple[str, str, bool]]:
    """(method, url with random ids, takes a file) for every route that changes state, sign-in excluded."""
    out = []
    for route in _routes():
        for method in sorted(route.methods - {"GET", "HEAD", "OPTIONS"}):
            if (method, route.path) == ("POST", "/auth/login"):
                continue
            url = "/api/v1" + route.path
            for name in route.param_convertors:
                url = url.replace("{" + name + "}", str(uuid.uuid4()))
            out.append((method, url, any(p.name == "file" for p in route.dependant.body_params)))
    return out


def _forged(c: TestClient, method: str, url: str, has_file: bool, headers: dict[str, str]) -> httpx.Response:
    if has_file:
        return c.request(method, url, headers=headers, files={"file": ("a.pdf", PDF, "application/pdf")})
    return c.request(method, url, headers=headers, json={})


def test_a_wrong_token_is_refused_on_every_unsafe_route(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    csrf = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    before = fingerprint(db)
    wrong_tokens = {
        "garbage": "x" * len(csrf),
        "empty": "",
        "right value, upper-cased": csrf.upper(),
        "right value plus a byte": csrf + "0",
        "right value minus a byte": csrf[:-1],
        "all zeros": "0" * len(csrf),
    }
    routes = _unsafe_routes()
    assert len(routes) > 20
    failures = []
    for label, token in wrong_tokens.items():
        for method, url, has_file in routes:
            r = _forged(cookie_app, method, url, has_file, {CSRF_HEADER: token})
            if r.status_code != 403 or r.json()["error"]["code"] != "csrf_failed":
                failures.append(f"{label}: {method} {url} -> {r.status_code}")
    assert not failures, "\n".join(failures)
    assert fingerprint(db) == before


@pytest.mark.parametrize(
    "content_type",
    ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x"],
)
def test_a_cross_site_form_post_carries_the_cookie_and_still_fails(
    cookie_app: TestClient, db: Session, content_type: str
) -> None:
    """The three content types a hostile page can send without a CORS preflight. The browser attaches the
    cookie; the missing header decides."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    _sign_in(cookie_app, "op@example.sg")
    before = fingerprint(db)
    for path in ("/api/v1/applications", "/api/v1/auth/logout", "/api/v1/notifications/read-all"):
        r = cookie_app.post(
            path,
            headers={"Content-Type": content_type, "Origin": "https://evil.example"},
            content=b"--x--" if "multipart" in content_type else b"a=b",
        )
        assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed", path
    assert fingerprint(db) == before
    assert cookie_app.get(ME).status_code == 200  # the forged sign-out did not end the session


def test_the_token_of_an_earlier_session_does_not_work_on_the_next_one(
    cookie_app: TestClient, db: Session
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    old = _sign_in(cookie_app, "op@example.sg").json()["csrf_token"]
    new = _sign_in(cookie_app, "op@example.sg", take_over=True).json()["csrf_token"]
    assert old != new
    path = "/api/v1/notifications/read-all"
    cookie_app.cookies.set(CSRF_COOKIE, old)  # the attacker replays a captured pair
    assert cookie_app.post(path, headers={CSRF_HEADER: old}).status_code == 403
    cookie_app.cookies.set(CSRF_COOKIE, new)
    assert cookie_app.post(path, headers={CSRF_HEADER: new}).status_code == 200


@pytest.mark.parametrize(
    "origin",
    [
        FRONTEND + ".evil.example",  # the frontend as a prefix of a hostile host
        "https://evil." + FRONTEND.removeprefix("https://"),  # as a suffix
        FRONTEND + "/",  # a trailing slash is not an origin
        FRONTEND.upper(),
        FRONTEND + ":8443",
        FRONTEND.replace("https", "http"),
        "https://dev.permitflow.space%2F@evil.example",
        " " + FRONTEND,
        "",
    ],
)
def test_sign_in_origins_that_only_look_like_the_frontend_are_refused(
    cookie_app: TestClient, db: Session, origin: str
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = cookie_app.post(
        LOGIN,
        json={"email": "op@example.sg", "password": DEFAULT_PASSWORD, "take_over": True},
        headers={"Origin": origin},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"
    assert not r.headers.get_list("set-cookie")
    assert SESSION_COOKIE not in cookie_app.cookies


def test_a_referer_alone_does_not_stand_in_for_the_origin(cookie_app: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = cookie_app.post(
        LOGIN,
        json={"email": "op@example.sg", "password": DEFAULT_PASSWORD},
        headers={"Referer": FRONTEND + "/login"},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"
