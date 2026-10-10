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


class StepUpFailed(Forbidden):
    """The signed-in administrator's password did not match on a change that asks for it again (US-101)."""

    code = "step_up_failed"


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


class Unavailable(AppError):
    """Busy, not broken: the caller may try again in a moment (US-098)."""

    status_code = 503
    code = "unavailable"


class InsufficientStorage(AppError):
    """The platform has no room left for another file (US-098)."""

    status_code = 507
    code = "storage_full"


class FileInfected(ValidationFailed):
    """The upload was blocked by the virus scan (US-099). The code is what the screens map to the operator
    message; the file stays quarantined."""

    code = "file_infected"


class FileBlocked(Forbidden):
    """A download of a file the scan blocked (US-099); same code as `FileInfected`."""

    code = "file_infected"


class FileScanning(Conflict):
    """A download of a file the virus scan has not cleared yet (US-099). Try again in a moment."""

    code = "file_scanning"


class DocumentsNotClear(Conflict):
    """A submission with a document the virus scan is still checking or has blocked (US-099)."""

    code = "documents_not_clear"


class ScannerUnavailable(Unavailable):
    """The virus scanner could not be reached; nothing was stored as clean (US-099)."""

    code = "scanner_unavailable"
