"""Domain and API errors. Every error response uses the same body shape (REL-001):

{"error": {"code": "...", "message": "...", "details": {...}}}
"""

from typing import Any

# ruff: noqa: N818 - names are HTTP semantics, used as `raise NotFound(...)`


class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def to_body(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details
        return {"error": error}


class BadRequest(AppError):
    status_code = 400
    code = "bad_request"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class SessionRevoked(Unauthorized):
    """The token is valid but its session ended: taken over from another device, signed out, or idle
    past the limit (US-093). The details say which, so the sign-in page can explain."""

    code = "session_revoked"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class InvalidTransition(Conflict):
    code = "invalid_transition"


class VersionConflict(Conflict):
    code = "version_conflict"


class SessionActive(Conflict):
    """Another device holds this account's session (US-093); the details name it and when it was last
    seen, so the sign-in page can offer to sign it out."""

    code = "session_active"


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"
