"""FastAPI dependencies: database session, current user, role guards."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.core.session_cookie import SAFE_METHODS, SESSION_COOKIE, check_csrf
from app.core.settings import get_settings
from app.infra.db import get_db
from app.models import User
from app.models.enums import Role
from app.services.auth import AuthService

DbSession = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    # One transport per mode (ADR-017): the cookie in cookie mode, the bearer header in token mode, never
    # both, so the other one cannot be used to dodge the CSRF check or the HttpOnly flag.
    cookie_mode = get_settings().auth_mode == "cookie"
    if cookie_mode:
        raw = request.cookies.get(SESSION_COOKIE)
    elif credentials is not None and credentials.scheme.lower() == "bearer":
        raw = credentials.credentials
    else:
        raw = None
    if not raw:
        raise Unauthorized("Invalid or missing credentials.")
    payload = decode_access_token(raw)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
        session_id = uuid.UUID(str(payload.get("sid")))
    except ValueError as exc:
        raise Unauthorized("Invalid or missing credentials.") from exc
    # Role, active flag and the session row are re-checked on every request (T19, T27).
    user = AuthService(db).current_user(user_id, session_id)
    # A cookie is sent by the browser on any request to this host, so unsafe methods need the CSRF token.
    # After the session check, so a revoked session still answers 401 session_revoked.
    if cookie_mode and request.method not in SAFE_METHODS:
        check_csrf(request, session_id)
    request.state.user_id = str(user.id)
    request.state.session_id = session_id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: Role) -> Callable[[User], User]:
    def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise Forbidden("Not available for your role.")
        return user

    return _check


OperatorUser = Annotated[User, Depends(require_role(Role.OPERATOR))]
OfficerUser = Annotated[User, Depends(require_role(Role.OFFICER))]
AdminUser = Annotated[User, Depends(require_role(Role.ADMIN))]
# Reads an administrator may make alongside the officer (US-072): the queue, the case, the audit trail,
# the checklist. Every mutation keeps `OfficerUser`.
OfficerOrAdmin = Annotated[User, Depends(require_role(Role.OFFICER, Role.ADMIN))]
# The shared downloads and the compare view: the owner, any officer, or an administrator.
AnyReader = Annotated[User, Depends(require_role(Role.OPERATOR, Role.OFFICER, Role.ADMIN))]
