from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.core.errors import RateLimited, Unauthorized
from app.core.rate_limit import FailedLoginLimiter, client_key
from app.core.settings import get_settings
from app.schemas.auth import LoginRequest, TokenOut, UserOut
from app.services.auth import AuthService

router = APIRouter(prefix="/auth")

_settings = get_settings()
login_limiter = FailedLoginLimiter(
    0 if _settings.app_env == "test" else _settings.login_rate_limit_per_minute
)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenOut:
    key = client_key(request, _settings.trusted_proxies, _settings.client_ip_header)
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
