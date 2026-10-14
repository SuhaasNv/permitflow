"""US-107 red-team R-1: X-Forwarded-For rate-limit bypass via uvicorn proxy headers.

The app's `client_key` (core/rate_limit.py) deliberately keys the per-client limiters on
`request.client.host` and only honours `X-Forwarded-For` behind a configured trusted proxy, so that a
caller cannot pick a fresh bucket per request (threat T4, SEC-010). That guard assumes `request.client`
is the real socket address.

uvicorn breaks the assumption. It is started (backend/Dockerfile) as

    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header

with no `--forwarded-allow-ips`, so uvicorn's ProxyHeadersMiddleware runs with its default
`forwarded_allow_ips="127.0.0.1"` and REWRITES `scope["client"]` from the caller-supplied
`X-Forwarded-For` whenever the immediate peer is trusted. `client_key` then reads the spoofed value, so a
brute-force attacker gets one bucket per forged address and the login limiter never trips. Reproduced
empirically against a local stack: 25 failed logins carrying distinct forged `X-Forwarded-For` all
returned 401 (never 429), while 25 on a single connection blocked at the 11th.

Fix: launch uvicorn so a forged `X-Forwarded-For` cannot rewrite `request.client` for an untrusted peer,
e.g. `--forwarded-allow-ips=` (empty, trust nobody) and let `client_key` resolve the client, or pin it to
the one edge address. The test flips to pass once the production entrypoint no longer leaves uvicorn at
its trusting default.
"""

import asyncio
import re
from pathlib import Path

from app.core.rate_limit import FailedLoginLimiter, client_key

_DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile"


def _uvicorn_trusted_hosts_from_entrypoint() -> str:
    """What uvicorn's ProxyHeadersMiddleware trusts, as the production image launches it. Absent
    `--forwarded-allow-ips` means uvicorn's default, which trusts the local peer and so honours a forged
    header from it."""
    cmd = _DOCKERFILE.read_text(encoding="utf-8")
    m = re.search(r"--forwarded-allow-ips[= ]([^\s\"']*)", cmd)
    if "--no-proxy-headers" in cmd:
        return ""  # proxy headers disabled: nothing is trusted
    if m is None:
        return "127.0.0.1"  # uvicorn default
    return m.group(1)


def _client_after_uvicorn(peer: str, forwarded_for: str, trusted_hosts: str) -> str:
    """The `request.client.host` the app sees, after uvicorn's ProxyHeadersMiddleware has processed a
    request from `peer` carrying `X-Forwarded-For: forwarded_for`."""
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    seen: dict[str, str] = {}

    async def inner(scope, receive, send):
        client = scope.get("client")
        seen["host"] = client[0] if client else ""

    app = ProxyHeadersMiddleware(inner, trusted_hosts=trusted_hosts or [])
    scope = {
        "type": "http",
        "client": (peer, 54321),
        "scheme": "http",
        "headers": [(b"x-forwarded-for", forwarded_for.encode())],
    }

    async def receive():  # pragma: no cover - never awaited by the middleware here
        return {"type": "http.request"}

    async def send(_message):  # pragma: no cover
        return None

    asyncio.run(app(scope, receive, send))
    return seen["host"]


class _Req:
    def __init__(self, host: str) -> None:
        self.client = type("C", (), {"host": host})()
        self.headers: dict[str, str] = {}


def test_forged_x_forwarded_for_cannot_bypass_the_login_limiter() -> None:
    peer = "127.0.0.1"  # the immediate peer uvicorn sees (the local socket / the edge)
    trusted = _uvicorn_trusted_hosts_from_entrypoint()
    limiter = FailedLoginLimiter(5)  # as main.py builds it, but with a small limit for the test
    blocked_at = None
    for i in range(1, 9):
        # Each attempt forges a different client address; the real socket is unchanged.
        host = _client_after_uvicorn(peer, f"10.0.0.{i}", trusted)
        key = client_key(_Req(host), trusted_proxies="")  # the app is configured with no trusted proxy
        if limiter.is_blocked(key):
            blocked_at = i
            break
        limiter.record_failure(key)
    # Five failures from one attacker must trip the limiter; a forged header must not buy fresh buckets.
    assert blocked_at is not None and blocked_at <= 6
