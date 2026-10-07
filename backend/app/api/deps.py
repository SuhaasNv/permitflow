"""FastAPI dependencies: database session, current user, role guards."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, Unauthorized
from app.core.security import decode_access_token
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
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise Unauthorized("Invalid or missing credentials.")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
        session_id = uuid.UUID(str(payload.get("sid")))
    except ValueError as exc:
        raise Unauthorized("Invalid or missing credentials.") from exc
    # Role, active flag and the session row are re-checked on every request (T19, T27).
    user = AuthService(db).current_user(user_id, session_id)
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
