"""Administrator routes (US-070, US-072, US-073, US-101): read-only oversight of cases, user management and
the platform settings."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import AdminUser, DbSession
from app.api.v1 import auth as auth_api
from app.core.errors import RateLimited, StepUpFailed
from app.core.rate_limit import client_key
from app.core.settings import get_settings
from app.models import User
from app.schemas.admin import (
    AdminOverviewOut,
    AdminUserOut,
    AdminUsersOut,
    AuditFeedOut,
    UserCreateIn,
    UserPatchIn,
)
from app.schemas.officer import OfficerApplicationOut
from app.schemas.platform_settings import (
    SettingChangeIn,
    SettingOut,
    SettingRevertIn,
    SettingsHistoryOut,
    SettingsOut,
)
from app.services.admin_feed import AdminFeedService
from app.services.admin_overview import AdminOverviewService
from app.services.admin_users import AdminUserService, Change
from app.services.auth import AuthService
from app.services.officer_view import OfficerViewService
from app.services.platform_settings import PlatformSettingsService

router = APIRouter(prefix="/admin")


@router.get("/overview", response_model=AdminOverviewOut)
def overview(user: AdminUser, db: DbSession) -> AdminOverviewOut:
    """Counts by status, the idle list, today's numbers and check health, on the Singapore day (US-070)."""
    return AdminOverviewService(db).overview()


@router.get("/audit-feed", response_model=AuditFeedOut)
def audit_feed(
    user: AdminUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before: Annotated[str | None, Query(max_length=80)] = None,
) -> AuditFeedOut:
    """The newest audit events across every application and every user change, keyset-paged (US-072)."""
    return AdminFeedService(db).feed(limit=limit, before=before)


@router.get("/applications/{application_id}", response_model=OfficerApplicationOut)
def admin_application(application_id: uuid.UUID, user: AdminUser, db: DbSession) -> OfficerApplicationOut:
    """The case as the officer sees it, with no actions: administrators read, never act (US-072)."""
    return OfficerViewService(db).get(user, application_id)


@router.get("/users", response_model=AdminUsersOut)
def users(user: AdminUser, db: DbSession) -> AdminUsersOut:
    return AdminUserService(db).directory(user)


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateIn, request: Request, user: AdminUser, db: DbSession) -> AdminUserOut:
    """A new account (US-073, added at the owner's request). Needs the administrator's own password
    (`admin_password`, step-up): 403 `step_up_failed`, audited as `user.step_up_failed`, 429 after
    repeated failures. Audit `user.created`."""
    _step_up(
        request,
        user,
        db,
        payload.admin_password,
        failure_event="user.step_up_failed",
        failure_payload={"action": "create", "email": payload.email.strip().lower()},
    )
    return AdminUserService(db).create(
        user, email=payload.email, full_name=payload.full_name, role=payload.role, password=payload.password
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def patch_user(
    user_id: uuid.UUID, payload: UserPatchIn, request: Request, user: AdminUser, db: DbSession
) -> AdminUserOut:
    """Change the role and/or the active flag (US-073). Needs the administrator's own password
    (`admin_password`, step-up): 403 `step_up_failed`, audited as `user.step_up_failed`, 429 after
    repeated failures. 409 `self_change`, `protected_account`, `last_admin`, `try_again`; audit
    `user.role_changed`, `user.deactivated`, `user.reactivated`."""
    _step_up(
        request,
        user,
        db,
        payload.admin_password,
        failure_event="user.step_up_failed",
        failure_payload={"action": "change", "user_id": str(user_id)},
    )
    return AdminUserService(db).change(user, user_id, Change(role=payload.role, is_active=payload.is_active))


def _step_up(
    request: Request,
    user: User,
    db: DbSession,
    password: str,
    *,
    failure_event: str,
    failure_payload: dict[str, str | None],
) -> None:
    """Re-verify the administrator's own password before a sensitive change (US-101, security audit F2). A
    wrong password is 403 `step_up_failed`, is audited as `failure_event` in its own transaction and counts
    against the sign-in limiter of the client address, which answers 429 once it is full, so the
    confirmation cannot be used to guess the password."""
    settings = get_settings()
    key = client_key(request, settings.trusted_proxies, settings.client_ip_header)
    limiter = auth_api.login_limiter
    if limiter.is_blocked(key):
        raise RateLimited("Too many failed attempts. Try again in a minute.")
    try:
        AuthService(db).confirm_password(
            user, password, failure_event=failure_event, failure_payload=failure_payload
        )
    except StepUpFailed:
        limiter.record_failure(key)
        raise


@router.get("/settings", response_model=SettingsOut)
def platform_settings(user: AdminUser, db: DbSession) -> SettingsOut:
    """Every editable setting with its current value, default, bounds and who last changed it (US-101)."""
    return PlatformSettingsService(db).overview()


@router.get("/settings/history", response_model=SettingsHistoryOut)
def platform_settings_history(
    user: AdminUser,
    db: DbSession,
    key: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before: Annotated[str | None, Query(max_length=80)] = None,
) -> SettingsHistoryOut:
    """Changes and reverts, newest first, keyset-paged, optionally for one setting (US-101)."""
    return PlatformSettingsService(db).history(key=key, limit=limit, before=before)


@router.put("/settings/{key}", response_model=SettingOut)
def change_platform_setting(
    key: str, payload: SettingChangeIn, request: Request, user: AdminUser, db: DbSession
) -> SettingOut:
    """Move one setting inside its bounds (US-101). Needs a reason and the administrator's password:
    403 `step_up_failed`, 429 after repeated failures, 404 unknown key, 422 `validation_failed` naming the
    bound (or `no_change`); audit `settings.changed`."""
    _step_up(
        request,
        user,
        db,
        payload.password,
        failure_event="settings.step_up_failed",
        failure_payload={"key": key, "action": "change"},
    )
    return PlatformSettingsService(db).change(user, key, payload.value, payload.reason)


@router.post("/settings/history/{event_id}/revert", response_model=SettingOut)
def revert_platform_setting(
    event_id: uuid.UUID, payload: SettingRevertIn, request: Request, user: AdminUser, db: DbSession
) -> SettingOut:
    """Undo one history entry: the setting returns to the value it had before it (US-101). Same step-up,
    reason and bounds as a change; audit `settings.reverted`."""
    service = PlatformSettingsService(db)
    _step_up(
        request,
        user,
        db,
        payload.password,
        failure_event="settings.step_up_failed",
        failure_payload={
            "key": service.key_of_entry(event_id),
            "action": "revert",
            "history_entry": str(event_id),
        },
    )
    return service.revert(user, event_id, payload.reason)
