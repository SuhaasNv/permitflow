"""Cookie sessions (US-104, ADR-018): the `__Host-` session cookie, the double-submit CSRF token and the
Origin check on sign-in. Only used when AUTH_MODE=cookie; token mode never reaches this module."""

import hashlib
import hmac
import logging
import uuid

from fastapi import Request, Response

from app.core.errors import CsrfFailed
from app.core.security import _secret
from app.core.settings import get_settings

logger = logging.getLogger("permitflow.auth")

SESSION_COOKIE = "__Host-pf_session"
CSRF_COOKIE = "__Host-pf_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def csrf_token(session_id: uuid.UUID) -> str:
    """Bound to the session: a value planted for one session, or minted without the server secret, fails."""
    # A sub-key, so the CSRF values never come from the key that signs the tokens themselves.
    key = hmac.new(
        _secret(get_settings().jwt_secret).encode(), b"permitflow-csrf-v1", hashlib.sha256
    ).digest()
    return hmac.new(key, str(session_id).encode(), hashlib.sha256).hexdigest()


def set_session_cookies(response: Response, token: str, session_id: uuid.UUID) -> None:
    """`__Host-` demands Secure, Path=/ and no Domain. The session cookie is HttpOnly; the CSRF cookie is not
    (a same-origin script may read it), and both live exactly as long as the token."""
    max_age = get_settings().jwt_expires_minutes * 60
    for name, value, http_only in (
        (SESSION_COOKIE, token, True),
        (CSRF_COOKIE, csrf_token(session_id), False),
    ):
        response.set_cookie(
            name, value, max_age=max_age, path="/", secure=True, httponly=http_only, samesite="strict"
        )


def clear_session_cookies(response: Response) -> None:
    for name, http_only in ((SESSION_COOKIE, True), (CSRF_COOKIE, False)):
        response.delete_cookie(name, path="/", secure=True, httponly=http_only, samesite="strict")


def check_csrf(request: Request, session_id: uuid.UUID) -> None:
    """Header, cookie and the session's own value must all agree, compared in constant time."""
    header = request.headers.get(CSRF_HEADER, "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    reason = None
    if not header:
        reason = "header_missing"
    elif not hmac.compare_digest(header.encode(), cookie.encode()):
        reason = "cookie_mismatch"
    elif not hmac.compare_digest(header.encode(), csrf_token(session_id).encode()):
        reason = "session_mismatch"
    if reason:
        _refuse(request, reason)
        raise CsrfFailed("The request could not be verified. Reload the page and try again.")


def check_origin(request: Request) -> None:
    """Sign-in has no session yet, so no token to check: the browser's Origin header must name a frontend
    origin (login CSRF). A request without one is refused; every browser sends it on a cross-origin POST."""
    if request.headers.get("origin") not in get_settings().cors_origin_list:
        _refuse(request, "origin")
        raise CsrfFailed("This sign-in did not come from PermitFlow.")


def _refuse(request: Request, reason: str) -> None:
    """One structured event per refusal, never a token value; the request log line carries the user."""
    logger.warning(
        "csrf_failed",
        extra={
            "extra_fields": {
                "reason": reason,
                "method": request.method,
                "path": request.url.path,
                "user_id": getattr(request.state, "user_id", None),
            }
        },
    )
