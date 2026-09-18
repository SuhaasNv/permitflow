"""In-memory limiter for failed login attempts per client IP (SEC-010).

Single-process only by design (SCOPE: rate limiting is simplified for the MVP).
"""

import threading
import time
from collections import deque


class FailedLoginLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self._window = 60.0
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self.limit > 0

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._failures.setdefault(key, deque())
        while q and now - q[0] > self._window:
            q.popleft()
        return q

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

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()
