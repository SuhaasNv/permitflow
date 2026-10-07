"""Request bodies are bounded before anything reads them (T4, review finding 21 Sep 2026).

FastAPI reads a body before a route's dependencies run, so an unauthenticated caller could push an
unbounded JSON body into memory, or a multipart body onto disk, on any route that takes one. This pure
ASGI middleware sits inside the logging and metrics layers and answers from the headers alone:

- a `Content-Length` above the cap is refused at once (the two multipart upload routes get the upload
  cap plus the form overhead; every other route the JSON cap);
- a body method without `Content-Length` (a chunked body) is refused with 411: browsers and the
  frontend's `fetch` and `XMLHttpRequest` always send a length, so nothing legitimate is lost;
- as a second fence, the bytes actually received are counted and the app sees a disconnect past the
  cap, so a dishonest length never turns into an unbounded read.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# Every JSON route's body is a few kilobytes; the largest, a checklist save with 17 long comments and
# extra findings in a wide script, stays well under this.
JSON_BODY_LIMIT = 256 * 1024
BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
UPLOAD_SUFFIXES = ("/documents", "/attachments")


def is_upload(method: str, path: str) -> bool:
    return method == "POST" and path.endswith(UPLOAD_SUFFIXES)


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, upload_limit: int, upload_message: str) -> None:
        self.app = app
        self.upload_limit = upload_limit
        self.upload_message = upload_message

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in BODY_METHODS:
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        upload = is_upload(scope["method"], scope["path"])
        limit = self.upload_limit if upload else JSON_BODY_LIMIT
        raw = headers.get("content-length")
        request_id = scope.get("state", {}).get("request_id")  # set by the logging layer outside
        if raw is None:
            if "chunked" in headers.get("transfer-encoding", "").lower():
                await _refuse(
                    send, 411, "length_required", "Send the body with a Content-Length header.", request_id
                )
                return
        elif not raw.isdigit() or int(raw) > limit:
            if upload:
                await _refuse(
                    send, 400, "bad_request", self.upload_message, request_id, {"reason": "too_large"}
                )
            else:
                await _refuse(send, 413, "payload_too_large", "The request body is too large.", request_id)
            return
        received = 0

        async def counted() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # A dishonest length: the app sees the client go away and stops reading.
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, counted, send)


async def _refuse(
    send: Send,
    status: int,
    code: str,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> None:
    payload = {
        "error": {"code": code, "message": message, "details": {**(details or {}), "request_id": request_id}}
    }
    body = json.dumps(payload).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})


__all__ = ["JSON_BODY_LIMIT", "BodyLimitMiddleware", "is_upload"]
