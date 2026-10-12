"""Abuse case 2 (US-105; THREAT_MODEL T13, US-058, US-082): forged forwarding headers do not buy a fresh
rate-limit bucket. Whatever the caller puts in X-Forwarded-For or X-Real-IP, the key is the socket address,
or, behind a trusted proxy, the hop the proxy itself appended (the rightmost one that is not a proxy).

The unit tests of `client_key` pin the function; these go through the running app: the request middleware
(every route, and the sign-in bucket) and the failed-sign-in limiter of the login route.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.v1 import auth as auth_routes
from app.core.rate_limit import RequestLimiter
from app.models.enums import Role
from tests.factories import DEFAULT_PASSWORD, make_user

ME = "/api/v1/auth/me"
LOGIN = "/api/v1/auth/login"
SOCKET = "testclient"  # the address Starlette's TestClient presents as the peer

Rotate = Callable[[int], dict[str, str]]


def _single_hop(i: int) -> dict[str, str]:
    return {"X-Forwarded-For": f"10.1.{i // 250}.{i % 250 + 1}"}


def _multi_hop(i: int) -> dict[str, str]:
    return {"X-Forwarded-For": f"10.2.{i}.1, 10.3.{i}.1, 10.4.{i}.1"}


def _real_ip(i: int) -> dict[str, str]:
    return {"X-Real-IP": f"10.5.0.{i + 1}", "X-Forwarded-For": f"10.5.1.{i + 1}"}


def _repeated_header(i: int) -> dict[str, str]:
    return {"X-Forwarded-For": f"10.6.0.{i + 1},10.6.1.{i + 1} ,  , 10.6.2.{i + 1}"}


ROTATIONS = [_single_hop, _multi_hop, _real_ip, _repeated_header]


@pytest.fixture
def install(client: TestClient) -> Iterator[Callable[..., RequestLimiter]]:
    previous = client.app.state.limiter  # type: ignore[attr-defined]

    def _install(**kwargs: object) -> RequestLimiter:
        limiter = RequestLimiter(**kwargs)  # type: ignore[arg-type]
        client.app.state.limiter = limiter  # type: ignore[attr-defined]
        return limiter

    yield _install
    client.app.state.limiter = previous  # type: ignore[attr-defined]


@pytest.mark.parametrize("rotate", ROTATIONS)
def test_rotating_headers_without_a_trusted_proxy_keep_one_bucket(
    client: TestClient, install: Callable[..., RequestLimiter], rotate: Rotate
) -> None:
    install(per_minute=5, login_per_minute=3, trusted_proxies="", client_ip_header="X-Real-IP")
    codes = [client.get(ME, headers=rotate(i)).status_code for i in range(8)]
    assert codes == [401] * 5 + [429] * 3, "a new forwarded address bought a new bucket"


@pytest.mark.parametrize("rotate", ROTATIONS)
def test_the_sign_in_bucket_is_not_reset_by_rotating_headers(
    client: TestClient, db: Session, install: Callable[..., RequestLimiter], rotate: Rotate
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    install(per_minute=100, login_per_minute=3, trusted_proxies="", client_ip_header="X-Real-IP")
    body = {"email": "op@example.sg", "password": DEFAULT_PASSWORD, "take_over": True}
    codes = [client.post(LOGIN, json=body, headers=rotate(i)).status_code for i in range(6)]
    assert codes == [200] * 3 + [429] * 3


def test_behind_a_trusted_proxy_the_callers_own_hops_are_ignored(
    client: TestClient, install: Callable[..., RequestLimiter]
) -> None:
    """The proxy appends the address it saw on the right; whatever the caller wrote on the left is noise."""
    install(per_minute=4, login_per_minute=3, trusted_proxies=SOCKET, client_ip_header="")

    def via_proxy(i: int) -> dict[str, str]:
        return {"X-Forwarded-For": f"10.7.{i}.1, 10.8.{i}.1, 198.51.100.7"}

    codes = [client.get(ME, headers=via_proxy(i)).status_code for i in range(7)]
    assert codes == [401] * 4 + [429] * 3


def test_a_chain_of_two_trusted_proxies_is_skipped_hop_by_hop(
    client: TestClient, install: Callable[..., RequestLimiter]
) -> None:
    install(per_minute=3, login_per_minute=3, trusted_proxies=f"{SOCKET},192.0.2.9", client_ip_header="")

    def chain(i: int) -> dict[str, str]:
        return {"X-Forwarded-For": f"10.9.{i}.1, 198.51.100.7, 192.0.2.9"}

    assert [client.get(ME, headers=chain(i)).status_code for i in range(5)] == [401] * 3 + [429] * 2


def test_a_wildcard_proxy_still_keys_on_the_last_hop_not_the_first(
    client: TestClient, install: Callable[..., RequestLimiter]
) -> None:
    install(per_minute=3, login_per_minute=3, trusted_proxies="*", client_ip_header="")
    codes = [
        client.get(ME, headers={"X-Forwarded-For": f"10.10.{i}.1, 203.0.113.77"}).status_code
        for i in range(5)
    ]
    assert codes == [401] * 3 + [429] * 2


def test_naming_a_victims_address_does_not_spend_the_victims_bucket(
    client: TestClient, install: Callable[..., RequestLimiter]
) -> None:
    install(per_minute=3, login_per_minute=3, trusted_proxies=SOCKET, client_ip_header="")
    victim = "198.51.100.99"
    for _ in range(6):  # the attacker writes the victim first; the proxy appends the attacker's own address
        client.get(ME, headers={"X-Forwarded-For": f"{victim}, 203.0.113.50"})
    assert client.get(ME, headers={"X-Forwarded-For": "203.0.113.50"}).status_code == 429
    assert (
        client.get(ME, headers={"X-Forwarded-For": victim}).status_code == 401
    )  # the victim is still served


@pytest.mark.parametrize("rotate", ROTATIONS)
def test_failed_sign_ins_are_counted_per_real_client_whatever_the_headers_say(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, rotate: Rotate
) -> None:
    """The failed-sign-in limiter (SEC-010): ten wrong passwords lock the client out, and then even the
    right password is refused until the window moves on."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    monkeypatch.setattr(auth_routes.login_limiter, "limit", 3)
    monkeypatch.setattr(auth_routes._settings, "trusted_proxies", "")  # noqa: SLF001
    auth_routes.login_limiter.clear()
    try:
        wrong = {"email": "op@example.sg", "password": "Wrong-Guess-1"}
        codes = [client.post(LOGIN, json=wrong, headers=rotate(i)).status_code for i in range(3)]
        assert codes == [401, 401, 401]
        for i in range(3, 6):
            assert client.post(LOGIN, json=wrong, headers=rotate(i)).status_code == 429
        right = {"email": "op@example.sg", "password": DEFAULT_PASSWORD, "take_over": True}
        r = client.post(LOGIN, json=right, headers=rotate(99))
        assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited"
    finally:
        auth_routes.login_limiter.clear()


def test_failed_sign_ins_behind_a_trusted_proxy_follow_the_proxys_hop(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    monkeypatch.setattr(auth_routes.login_limiter, "limit", 3)
    monkeypatch.setattr(auth_routes._settings, "trusted_proxies", SOCKET)  # noqa: SLF001
    monkeypatch.setattr(auth_routes._settings, "client_ip_header", "")  # noqa: SLF001
    auth_routes.login_limiter.clear()
    try:
        wrong = {"email": "op@example.sg", "password": "Wrong-Guess-1"}
        for i in range(3):
            h = {"X-Forwarded-For": f"10.11.{i}.1, 203.0.113.50"}
            assert client.post(LOGIN, json=wrong, headers=h).status_code == 401
        h = {"X-Forwarded-For": "10.11.200.1, 203.0.113.50"}
        assert client.post(LOGIN, json=wrong, headers=h).status_code == 429
        other = {"X-Forwarded-For": "10.11.200.1, 203.0.113.51"}  # a different real client is not locked
        assert client.post(LOGIN, json=wrong, headers=other).status_code == 401
    finally:
        auth_routes.login_limiter.clear()
