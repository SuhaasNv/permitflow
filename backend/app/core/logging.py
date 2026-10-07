"""Structured request logging with a request id (NFR-007). Identifiers only, never payloads."""

import json
import logging
import re
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("permitflow")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(isinstance(h, logging.StreamHandler) and getattr(h, "_pf", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._pf = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)


REQUEST_ID_SHAPE = re.compile(r"[A-Za-z0-9_-]{1,64}")


async def request_logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # A caller may carry its own id for correlation, but only a plain token: anything else would be
    # echoed into the response header, the logs and every error body (review finding, 21 Sep).
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if REQUEST_ID_SHAPE.fullmatch(supplied) else uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    user_id = getattr(request.state, "user_id", None)
    logger.info(
        "request",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
            }
        },
    )
    return response
