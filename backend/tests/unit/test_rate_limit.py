"""Sliding-window request limits (US-058): the general and the sign-in bucket, the retry hint, the health
exemption, and the client key behind a trusted proxy."""

from types import SimpleNamespace
from typing import Any

from app.core.rate_limit import RequestLimiter, WindowLimiter, client_key


def _request(
    path: str,
    method: str = "GET",
    host: str = "203.0.113.5",
    forwarded: str | None = None,
    real_ip: str | None = None,
) -> Any:
    headers = {"x-forwarded-for": forwarded} if forwarded else {}
    if real_ip:
        headers["x-real-ip"] = real_ip
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


def test_request_limiter_uses_the_login_bucket_for_sign_in_only_and_exempts_health_and_metrics() -> None:
    limiter = RequestLimiter(per_minute=100, login_per_minute=2, trusted_proxies="")
    login = _request("/api/v1/auth/login", "POST")
    assert limiter.check(login) is None and limiter.check(login) is None
    assert limiter.check(login) is not None  # third sign-in attempt in the minute, any outcome
    assert limiter.check(_request("/api/v1/applications")) is None  # general bucket untouched
    assert limiter.check(_request("/api/v1/auth/me")) is None  # only POST /auth/login is special
    for _ in range(200):
        assert limiter.check(_request("/api/v1/health")) is None
        assert limiter.check(_request("/api/v1/metrics")) is None


def test_client_key_takes_the_hop_the_trusted_proxy_appended_not_the_one_the_caller_sent() -> None:
    # The caller sent "10.0.0.9"; the proxy at 203.0.113.5 appended the real client 198.51.100.1.
    spoof = _request("/x", host="203.0.113.5", forwarded="10.0.0.9, 198.51.100.1")
    assert client_key(spoof, "") == "203.0.113.5"  # no trusted proxy: the socket address
    assert client_key(spoof, "203.0.113.5") == "198.51.100.1"
    assert client_key(spoof, "*") == "198.51.100.1"
    # Two trusted proxies in a chain: skip both, take the client they vouch for.
    chain = _request("/x", host="203.0.113.5", forwarded="10.0.0.9, 198.51.100.1, 203.0.113.6")
    assert client_key(chain, "203.0.113.5,203.0.113.6") == "198.51.100.1"
    assert client_key(_request("/x", host="1.2.3.4"), "*") == "1.2.3.4"


def test_client_key_prefers_the_edge_client_header_behind_a_trusted_proxy() -> None:
    """Railway writes the connecting address in X-Real-IP and leaves the edge instance as the last hop
    of X-Forwarded-For (readiness row 25): behind the edge the header wins, the chain is the fallback."""
    hdr = "X-Real-IP"
    edge = _request("/x", host="10.10.0.1", forwarded="198.51.100.1, 10.10.0.1", real_ip="198.51.100.1")
    assert client_key(edge, "*", hdr) == "198.51.100.1"
    assert client_key(edge, "*", "") == "10.10.0.1"  # the old behaviour, without the header configured
    # A caller cannot pick a bucket by sending the header: without a trusted proxy the socket wins.
    forged = _request("/x", host="203.0.113.5", forwarded="10.0.0.9", real_ip="10.0.0.7")
    assert client_key(forged, "", hdr) == "203.0.113.5"
    # Behind the edge but without the header (an older platform): the forwarded logic as before.
    older = _request("/x", host="10.10.0.1", forwarded="10.0.0.9, 198.51.100.1")
    assert client_key(older, "*", hdr) == "198.51.100.1"
    # A multi-value header keeps the first address; a blank header falls through.
    multi = _request("/x", host="10.10.0.1", real_ip="198.51.100.1, 10.10.0.1")
    assert client_key(multi, "*", hdr) == "198.51.100.1"
    assert client_key(_request("/x", host="10.10.0.1", real_ip=" "), "*", hdr) == "10.10.0.1"


def test_request_limiter_buckets_by_the_edge_client_header() -> None:
    limiter = RequestLimiter(
        per_minute=2, login_per_minute=1, trusted_proxies="*", client_ip_header="X-Real-IP"
    )
    path = "/api/v1/applications"
    a = _request(path, host="10.10.0.1", forwarded="198.51.100.1, 10.10.0.1", real_ip="198.51.100.1")
    b = _request(path, host="10.10.0.1", forwarded="198.51.100.2, 10.10.0.1", real_ip="198.51.100.2")
    assert limiter.check(a) is None and limiter.check(a) is None
    assert limiter.check(a) is not None  # the third request from the same caller
    assert limiter.check(b) is None  # another caller behind the same edge keeps its own bucket


def test_limiter_map_stays_bounded_under_many_distinct_clients() -> None:
    limiter = WindowLimiter(5)
    for i in range(10_500):
        limiter.hit(f"10.0.{i // 256}.{i % 256}")
    limiter.hit("fresh")
    assert len(limiter._hits) <= 10_501  # noqa: SLF001 - the bound is the property under test
