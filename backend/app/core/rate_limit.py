"""In-memory rate limiting (SEC-010, US-058).

Two limiters share one idea, a sliding one-minute window per key, kept in process memory:

- `FailedLoginLimiter` counts failed sign-ins per client (the original SEC-010 control): a wrong password
  ten times in a minute blocks that client until the window moves on.
- `WindowLimiter` counts every request per client, one bucket for sign-in attempts (all of them, not only
  failures, because Argon2 makes each attempt cost CPU) and one for everything else. Used by the request
  middleware in `main.py`.

Single-process only by design (SCOPE: rate limiting is simplified for the MVP; the production step is the
same windows in Redis, or a limit at the edge). The client key honours `X-Forwarded-For` only behind a
trusted proxy, so a caller cannot pick a fresh bucket per request (T4).
"""

import math
import threading
import time
from collections import deque

from fastapi import Request


def client_key(request: Request, trusted_proxies: str) -> str:
    """The socket address, or the client address a trusted proxy recorded in X-Forwarded-For.

    A proxy appends the address it saw to the end of the header, so the rightmost hop that is not itself a
    trusted proxy is the one the proxy vouches for; anything left of it was supplied by the caller and would
    let an attacker pick a fresh limiter bucket per request (T4). With `*`, every hop but the last is
    treated as caller-supplied.
    """
    host = request.client.host if request.client else "unknown"
    trusted = {p.strip() for p in trusted_proxies.split(",") if p.strip()}
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded or not (host in trusted or "*" in trusted):
        return host
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if hop not in trusted:
            return hop
    return hops[-1] if hops else host


class _Window:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    def _prune(self, key: str, now: float) -> deque[float]:
        if len(self._hits) > 10_000:
            # Many distinct clients (a scan, or spoofed addresses): drop every window that has gone quiet,
            # so the map is bounded by the number of clients active in the last minute.
            self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] <= self.window}
        q = self._hits.setdefault(key, deque())
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


class FailedLoginLimiter(_Window):
    """Blocks a client after `limit` failed sign-ins within a minute."""

    def __init__(self, limit_per_minute: int) -> None:
        super().__init__(limit_per_minute)

    def is_blocked(self, key: str) -> bool:
        if not self.enabled:
            return False
        with self._lock:
            return len(self._prune(key, time.monotonic())) >= self.limit

    def record_failure(self, key: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._prune(key, time.monotonic()).append(time.monotonic())


class WindowLimiter(_Window):
    """Counts every hit; `hit` returns None when allowed, or the seconds until the window admits again."""

    def hit(self, key: str) -> int | None:
        if not self.enabled:
            return None
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if len(q) >= self.limit:
                return max(1, math.ceil(self.window - (now - q[0])))
            q.append(now)
            return None


class RequestLimiter:
    """The two request buckets the middleware consults, replaceable on `app.state` in tests."""

    def __init__(self, *, per_minute: int, login_per_minute: int, trusted_proxies: str) -> None:
        self.general = WindowLimiter(per_minute)
        self.login = WindowLimiter(login_per_minute)
        self.trusted_proxies = trusted_proxies

    def check(self, request: Request) -> int | None:
        path = request.url.path
        # Health checks and the metrics scrape are exempt: the deploy gate and the monitor must keep
        # answering while a client is being refused (the scrape is bearer-token protected, US-077).
        if path.endswith(("/health", "/healthz", "/metrics")):
            return None
        key = client_key(request, self.trusted_proxies)
        bucket = self.login if path.endswith("/auth/login") and request.method == "POST" else self.general
        return bucket.hit(key)

    def clear(self) -> None:
        self.general.clear()
        self.login.clear()
