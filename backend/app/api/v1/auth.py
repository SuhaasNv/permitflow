from fastapi import APIRouter, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.errors import RateLimited, Unauthorized
from app.core.rate_limit import FailedLoginLimiter, client_key
from app.core.session_cookie import (
    check_origin,
    clear_session_cookies,
    csrf_token,
    set_session_cookies,
)
from app.core.settings import get_settings
from app.domain.device_label import device_label
from app.schemas.auth import LoginRequest, MeOut, SessionOut, TokenOut, UserOut
from app.services.auth import AuthService

router = APIRouter(prefix="/auth")

_settings = get_settings()
login_limiter = FailedLoginLimiter(
    0 if _settings.app_env == "test" else _settings.login_rate_limit_per_minute
)


@router.post("/login", response_model=TokenOut | SessionOut)
def login(
    payload: LoginRequest, request: Request, response: Response, db: DbSession
) -> TokenOut | SessionOut:
    cookie_mode = get_settings().auth_mode == "cookie"
    if cookie_mode:
        check_origin(request)  # before the password is looked at: a foreign page learns nothing (US-104)
    key = client_key(request, _settings.trusted_proxies, _settings.client_ip_header)
    if login_limiter.is_blocked(key):
        raise RateLimited("Too many failed attempts. Try again in a minute.")
    try:
        token = AuthService(db).authenticate(
            payload.email,
            payload.password,
            device=device_label(request.headers.get("user-agent")),
            take_over=payload.take_over,
        )
    except Unauthorized:
        login_limiter.record_failure(key)
        raise
    # No reset on success: a valid account must not be able to clear the failure window for its IP.
    if cookie_mode:
        set_session_cookies(response, token.access_token, token.session_id)
        return SessionOut(
            expires_at=token.expires_at,
            user=UserOut.model_validate(token.user),
            csrf_token=csrf_token(token.session_id),
        )
    return TokenOut(
        access_token=token.access_token,
        expires_at=token.expires_at,
        user=UserOut.model_validate(token.user),
    )


@router.get("/me", response_model=MeOut, response_model_exclude_none=True)
def me(request: Request, user: CurrentUser) -> MeOut:
    """Who is signed in. In cookie mode (US-104) it also hands the page its CSRF token after a reload."""
    out = MeOut.model_validate(user)
    if get_settings().auth_mode == "cookie":
        out.csrf_token = csrf_token(request.state.session_id)
    return out


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, user: CurrentUser, db: DbSession) -> Response:
    """Ends this sign-in on the server (US-093): the token stops working on its next use."""
    AuthService(db).sign_out(user, request.state.session_id)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if get_settings().auth_mode == "cookie":
        clear_session_cookies(response)
    return response
