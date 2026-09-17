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
    except ValueError as exc:
        raise Unauthorized("Invalid or missing credentials.") from exc
    # Role and active flag are re-checked against the row on every request (T19).
    user = AuthService(db).current_user(user_id)
    request.state.user_id = str(user.id)
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
