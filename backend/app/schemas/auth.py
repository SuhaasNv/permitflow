"""Auth schemas: login request, token, user."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)
    # US-093: sign out the device that holds this account's session and continue here.
    take_over: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class SessionOut(BaseModel):
    """Cookie mode (US-104): the sign-in answer carries no bearer token. `csrf_token` is the value for the
    X-CSRF-Token header; it is useless without the HttpOnly session cookie, and the cookie copy is not
    readable by a script on another origin (the API is a different host), so the body hands it over."""

    expires_at: datetime
    user: UserOut
    csrf_token: str


class MeOut(UserOut):
    csrf_token: str | None = None  # cookie mode only; absent in token mode
