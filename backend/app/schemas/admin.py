"""The administrator's read models (US-070, US-072) and user management (US-073)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import Role


class StatusCountOut(BaseModel):
    status: str
    label: str
    tone: str
    turn: str  # draft | office | operator | decided
    count: int


class TotalsOut(BaseModel):
    applications: int
    submitted: int
    drafts: int
    with_office: int
    waiting_on_operators: int
    idle_over_7_days: int


class IdleApplicationOut(BaseModel):
    id: uuid.UUID
    reference_no: str
    business_name: str | None
    status: str
    label: str
    tone: str
    days_idle: int
    last_activity_at: datetime


class TodayOut(BaseModel):
    day: str  # the Singapore calendar date, YYYY-MM-DD
    submissions: int
    resubmissions: int
    checklists_submitted: int
    clarification_rounds: int
    runs_today: int
    runs_per_day_quota: int


class ChecksOut(BaseModel):
    """Document checks in the last 24 hours, by outcome; latency of the runs that finished."""

    runs: int
    verified: int
    issues_found: int
    needs_review: int
    unreadable: int
    failed_or_unavailable: int
    still_running: int
    average_seconds: float | None
    p95_seconds: float | None
    provider: str
    model: str | None


class AdminOverviewOut(BaseModel):
    as_of: datetime
    totals: TotalsOut
    counts: list[StatusCountOut]
    idle: list[IdleApplicationOut]
    today: TodayOut
    checks: ChecksOut


class FeedEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    summary: str
    actor_name: str | None
    actor_role: str | None
    application_id: uuid.UUID | None
    reference_no: str | None
    created_at: datetime


class AuditFeedOut(BaseModel):
    events: list[FeedEventOut]
    # Pass back as `before` for the next page; null once the oldest event is on the page.
    next_cursor: str | None


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool
    is_protected: bool
    created_at: datetime


class AdminUsersOut(BaseModel):
    users: list[AdminUserOut]
    # The caller's own id, so the page can disable that row without comparing emails.
    self_id: uuid.UUID


class UserPatchIn(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class UserCreateIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=120)
    role: Role
    password: str = Field(min_length=12, max_length=200)


__all__ = [
    "AdminOverviewOut",
    "AdminUserOut",
    "AdminUsersOut",
    "AuditFeedOut",
    "ChecksOut",
    "FeedEventOut",
    "IdleApplicationOut",
    "StatusCountOut",
    "TodayOut",
    "TotalsOut",
    "UserCreateIn",
    "UserPatchIn",
]
