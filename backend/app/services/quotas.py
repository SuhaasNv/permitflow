"""Abuse ceilings kept in the database (US-058).

Two quotas answer the "hit my most expensive endpoint until the bill explodes" scenario and its cousin,
"fill my database with garbage": an operator may hold a bounded number of open drafts, and verification
runs (each one a model call when the live provider is on) are counted per applicant and per platform over
a rolling day. Counting in the database, not in memory, means the ceiling survives restarts and applies
across workers. A run over quota is stored as `unavailable` with a reason the officer can read; the
document stays and the application can still be submitted (AI-006: the check is advisory).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.core.settings import get_settings
from app.domain.enums import VerificationStatus
from app.models import VerificationRun
from app.repositories.applications import ApplicationRepository
from app.repositories.documents import DocumentRepository
from app.repositories.users import UserRepository

DAILY_LIMIT_REASON = "daily_limit_reached"


def ensure_draft_capacity(db: Session, operator_id: uuid.UUID) -> None:
    """Refuse a new draft once the operator holds `MAX_DRAFTS_PER_USER` open ones (0 disables)."""
    limit = get_settings().max_drafts_per_user
    if limit <= 0:
        return
    # Lock the operator's user row for the rest of the transaction, so the count and the insert that
    # follows it are serialised per operator; a second create waits here and then sees the new draft.
    UserRepository(db).lock(operator_id)
    if ApplicationRepository(db).count_drafts(operator_id) >= limit:
        raise Conflict(
            f"You already have {limit} draft applications. Submit or delete one before starting another.",
            details={"code": "draft_limit", "limit": limit},
        )


def verification_over_quota(db: Session, operator_id: uuid.UUID) -> str | None:
    """The reason to skip the model call, or None when the run may proceed."""
    settings = get_settings()
    since = datetime.now(UTC) - timedelta(days=1)
    repo = DocumentRepository(db)
    if settings.ai_runs_per_user_per_day > 0:
        used = repo.count_runs_since(since, operator_id=operator_id, exclude_reason=DAILY_LIMIT_REASON)
        if used >= settings.ai_runs_per_user_per_day:
            return DAILY_LIMIT_REASON
    if settings.ai_runs_per_day > 0:
        if repo.count_runs_since(since, exclude_reason=DAILY_LIMIT_REASON) >= settings.ai_runs_per_day:
            return DAILY_LIMIT_REASON
    return None


def new_run(db: Session, document_id: uuid.UUID, operator_id: uuid.UUID) -> VerificationRun:
    """A pending run, or an already-finished `unavailable` one when the applicant or the platform is over
    the daily quota. The background task only picks up pending runs, so nothing is sent to the model."""
    reason = verification_over_quota(db, operator_id)
    if reason is None:
        return VerificationRun(document_id=document_id, status=VerificationStatus.PENDING, provider="none")
    now = datetime.now(UTC)
    return VerificationRun(
        document_id=document_id,
        status=VerificationStatus.UNAVAILABLE,
        provider="none",
        error_reason=reason,
        started_at=now,
        finished_at=now,
        latency_ms=0,
    )
