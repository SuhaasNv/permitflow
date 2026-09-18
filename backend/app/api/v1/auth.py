from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.api.v1.schemas import LoginRequest, TokenOut, UserOut
from app.core.errors import RateLimited, Unauthorized
from app.core.rate_limit import FailedLoginLimiter
from app.core.settings import get_settings
from app.services.auth import AuthService

router = APIRouter(prefix="/auth")

_settings = get_settings()
login_limiter = FailedLoginLimiter(
    0 if _settings.app_env == "test" else _settings.login_rate_limit_per_minute
)


def _client_key(request: Request) -> str:
    """Rate-limit key: the socket address, or X-Forwarded-For only when the socket is a trusted proxy.

    Honouring the header from any client would let an attacker pick a fresh bucket per request (T4).
    """
    host = request.client.host if request.client else "unknown"
    trusted = {p.strip() for p in _settings.trusted_proxies.split(",") if p.strip()}
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and host in trusted:
        return forwarded.split(",")[0].strip()
    return host


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenOut:
    key = _client_key(request)
    if login_limiter.is_blocked(key):
        raise RateLimited("Too many failed attempts. Try again in a minute.")
    try:
        token = AuthService(db).authenticate(payload.email, payload.password)
    except Unauthorized:
        login_limiter.record_failure(key)
        raise
    # No reset on success: a valid account must not be able to clear the failure window for its IP.
    return TokenOut(
        access_token=token.access_token,
        expires_at=token.expires_at,
        user=UserOut.model_validate(token.user),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
