"""Administrator routes (US-070, US-072, US-073): read-only oversight of cases plus user management."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, DbSession
from app.schemas.admin import (
    AdminOverviewOut,
    AdminUserOut,
    AdminUsersOut,
    AuditFeedOut,
    UserCreateIn,
    UserPatchIn,
)
from app.schemas.officer import OfficerApplicationOut
from app.services.admin_feed import AdminFeedService
from app.services.admin_overview import AdminOverviewService
from app.services.admin_users import AdminUserService, Change
from app.services.officer_view import OfficerViewService

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
def create_user(payload: UserCreateIn, user: AdminUser, db: DbSession) -> AdminUserOut:
    """A new account (US-073, added at the owner's request): audit `user.created`."""
    return AdminUserService(db).create(
        user, email=payload.email, full_name=payload.full_name, role=payload.role, password=payload.password
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def patch_user(user_id: uuid.UUID, payload: UserPatchIn, user: AdminUser, db: DbSession) -> AdminUserOut:
    """Change the role and/or the active flag (US-073): 409 `self_change`, `protected_account`,
    `last_admin`, `try_again`; audit `user.role_changed`, `user.deactivated`, `user.reactivated`."""
    return AdminUserService(db).change(user, user_id, Change(role=payload.role, is_active=payload.is_active))
