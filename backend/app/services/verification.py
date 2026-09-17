"""AI verification runs (ADR-004, ADR-006). The only module that talks to `infra.ai`.

`run_verification(run_id)` is a plain synchronous function that opens its own database session, so it
can run in FastAPI's threadpool via BackgroundTasks after the request session is gone. It never raises:
every failure is recorded on the run as data (REL-003).
"""

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.core.settings import get_settings
from app.domain.enums import Role, VerificationStatus
from app.domain.verification_rules import (
    DOCUMENT_TYPE_DESCRIPTIONS,
    SECTION_FOR_DOCUMENT,
    VerificationRequest,
    VerificationResult,
    apply_rules,
    find_injection_phrases,
)
from app.infra.ai import ProviderError, ProviderUnavailable
from app.infra.ai.factory import get_provider
from app.infra.db import session_factory
from app.infra.extraction import extract_text
from app.infra.storage import get_storage
from app.models import Application, Document, User, VerificationRun
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository

logger = logging.getLogger("permitflow.verification")

TERMINAL = {
    VerificationStatus.VERIFIED,
    VerificationStatus.ISSUES_FOUND,
    VerificationStatus.NEEDS_REVIEW,
    VerificationStatus.UNREADABLE,
    VerificationStatus.FAILED,
    VerificationStatus.UNAVAILABLE,
}


def run_verification(run_id: uuid.UUID) -> None:
    settings = get_settings()
    with session_factory()() as db:
        run = db.get(VerificationRun, run_id)
        if run is None or run.status != VerificationStatus.PENDING:
            return
        doc = db.get(Document, run.document_id)
        app = db.get(Application, doc.application_id) if doc else None
        if doc is None or app is None:
            return
        run.status = VerificationStatus.RUNNING
        run.started_at = datetime.now(UTC)
        db.commit()
        started = time.perf_counter()

        try:
            data = b"".join(get_storage().open(doc.stored_key))
            extracted = extract_text(doc.content_type, data, max_chars=settings.ai_max_text_chars)
            doc.extracted_text = extracted.text or None
            if extracted.reason:
                _finish(
                    db,
                    run,
                    app,
                    VerificationStatus.UNREADABLE,
                    provider="none",
                    error_reason=extracted.reason,
                    started=started,
                )
                return

            provider = get_provider()
            if provider is None:
                _finish(
                    db,
                    run,
                    app,
                    VerificationStatus.UNAVAILABLE,
                    provider="none",
                    error_reason="provider_not_configured",
                    started=started,
                )
                return

            injection = find_injection_phrases(extracted.text)
            section_key = SECTION_FOR_DOCUMENT[doc.document_type.value]
            request = VerificationRequest(
                document_type=doc.document_type.value,
                document_type_description=DOCUMENT_TYPE_DESCRIPTIONS[doc.document_type.value],
                form_section=dict(app.draft_data.get(section_key) or {}),
                text=extracted.text,
            )
            try:
                result: VerificationResult = provider.verify(request)
            except ProviderUnavailable as exc:
                _finish(
                    db,
                    run,
                    app,
                    VerificationStatus.UNAVAILABLE,
                    provider=provider.name,
                    model=provider.model,
                    error_reason=_reason(exc),
                    started=started,
                )
                return
            except ProviderError as exc:
                _finish(
                    db,
                    run,
                    app,
                    VerificationStatus.FAILED,
                    provider=provider.name,
                    model=provider.model,
                    error_reason=_reason(exc),
                    raw_output_valid=False,
                    started=started,
                )
                return

            outcome = apply_rules(
                result, confidence_threshold=settings.ai_confidence_threshold, injection_phrases=injection
            )
            run.confidence = result.confidence
            run.summary = result.summary
            run.issues = outcome.issues
            run.missing_information = list(result.missing_information)
            _finish(
                db,
                run,
                app,
                outcome.status,
                provider=provider.name,
                model=provider.model,
                raw_output_valid=True,
                started=started,
            )
        except Exception as exc:  # noqa: BLE001 - last line of defence: the task must never raise
            logger.exception("verification_crashed", extra={"extra_fields": {"run_id": str(run_id)}})
            db.rollback()
            run = db.get(VerificationRun, run_id)
            if run is not None:
                _finish(
                    db,
                    run,
                    app,
                    VerificationStatus.FAILED,
                    provider="none",
                    error_reason=_reason(exc),
                    started=started,
                )


def _reason(exc: Exception) -> str:
    return (type(exc).__name__ + ": " + str(exc))[:64]


def _finish(
    db: Session,
    run: VerificationRun,
    app: Application | None,
    status: VerificationStatus,
    *,
    provider: str,
    model: str | None = None,
    error_reason: str | None = None,
    raw_output_valid: bool | None = None,
    started: float,
) -> None:
    run.status = status
    run.provider = provider
    run.model = model
    run.error_reason = error_reason
    run.raw_output_valid = raw_output_valid
    run.finished_at = datetime.now(UTC)
    run.latency_ms = int((time.perf_counter() - started) * 1000)
    AuditRepository(db).record(
        application_id=app.id if app else None,
        actor_id=None,
        event_type="verification.completed",
        payload={
            "run_id": str(run.id),
            "document_id": str(run.document_id),
            "status": status.value,
            "provider": provider,
            "error_reason": error_reason,
        },
    )
    db.commit()
    logger.info(
        "verification_completed",
        extra={
            "extra_fields": {
                "run_id": str(run.id),
                "status": status.value,
                "provider": provider,
                "model": model,
                "latency_ms": run.latency_ms,
                "raw_output_valid": raw_output_valid,
            }
        },
    )


def mark_stale_runs_failed(grace_seconds: int = 60) -> int:
    """On startup, runs still `running` longer than timeout + grace were interrupted by a restart."""
    settings = get_settings()
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.ai_timeout_seconds * 2 + grace_seconds)
    with session_factory()() as db:
        result = db.execute(
            update(VerificationRun)
            .where(VerificationRun.status == VerificationStatus.RUNNING, VerificationRun.started_at < cutoff)
            .values(
                status=VerificationStatus.FAILED, error_reason="interrupted", finished_at=datetime.now(UTC)
            )
        )
        db.commit()
        return int(getattr(result, "rowcount", 0) or 0)


class VerificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.documents = DocumentRepository(db)
        self.audit = AuditRepository(db)

    def rerun(self, user: User, application_id: uuid.UUID, document_id: uuid.UUID) -> VerificationRun:
        """Owner or officer may re-run once the latest run is terminal (AI-009, SCOPE S2)."""
        if user.role not in (Role.OPERATOR, Role.OFFICER):
            raise NotFound("Document not found.")
        app = self.applications.get_for(user, application_id)
        doc = self.documents.get_in_application(app.id, document_id)
        if doc is None or not doc.is_current:
            raise NotFound("Document not found.")
        latest = self.documents.latest_run(doc.id)
        if latest is not None and latest.status not in TERMINAL:
            raise Conflict("A check is already in progress for this document.")
        run = VerificationRun(document_id=doc.id, status=VerificationStatus.PENDING, provider="none")
        self.documents.add_run(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def pending_runs(self) -> list[uuid.UUID]:
        return list(
            self.db.scalars(
                select(VerificationRun.id).where(VerificationRun.status == VerificationStatus.PENDING)
            )
        )
