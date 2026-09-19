"""Sliding-window request limits (US-058): the general and the sign-in bucket, the retry hint, the health
exemption, and the client key behind a trusted proxy."""

from types import SimpleNamespace
from typing import Any

from app.core.rate_limit import RequestLimiter, WindowLimiter, client_key


def _request(path: str, method: str = "GET", host: str = "203.0.113.5", forwarded: str | None = None) -> Any:
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    return SimpleNamespace(
        url=SimpleNamespace(path=path), method=method, client=SimpleNamespace(host=host), headers=headers
    )


def test_window_limiter_admits_up_to_the_limit_then_reports_seconds_to_wait() -> None:
    limiter = WindowLimiter(3)
    assert [limiter.hit("a") for _ in range(3)] == [None, None, None]
    wait = limiter.hit("a")
    assert wait is not None and 1 <= wait <= 60
    assert limiter.hit("b") is None  # another client has its own window
    assert WindowLimiter(0).hit("a") is None  # 0 disables


def test_request_limiter_uses_the_login_bucket_for_sign_in_only_and_exempts_health() -> None:
    limiter = RequestLimiter(per_minute=100, login_per_minute=2, trusted_proxies="")
    login = _request("/api/v1/auth/login", "POST")
    assert limiter.check(login) is None and limiter.check(login) is None
    assert limiter.check(login) is not None  # third sign-in attempt in the minute, any outcome
    assert limiter.check(_request("/api/v1/applications")) is None  # general bucket untouched
    assert limiter.check(_request("/api/v1/auth/me")) is None  # only POST /auth/login is special
    for _ in range(200):
        assert limiter.check(_request("/api/v1/health")) is None


def test_client_key_honours_forwarded_for_only_behind_a_trusted_proxy() -> None:
    spoof = _request("/x", host="203.0.113.5", forwarded="10.0.0.9, 198.51.100.1")
    assert client_key(spoof, "") == "203.0.113.5"
    assert client_key(spoof, "203.0.113.5") == "10.0.0.9"
    assert client_key(spoof, "*") == "10.0.0.9"
    assert client_key(_request("/x", host="1.2.3.4"), "*") == "1.2.3.4"
