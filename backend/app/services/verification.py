"""AI verification runs (ADR-004, ADR-006, ADR-016). The only module that talks to `infra.ai`.

`execute_run(run_id)` is a plain synchronous function that opens its own database session, so it can run
in FastAPI's threadpool via BackgroundTasks after the request session is gone (`VERIFICATION_MODE=inline`),
or in a worker thread of `python -m app.worker` (`worker`). It never raises: every failure is recorded on
the run as data (REL-003). A queued run is `pending`; a claimed one is `running` and held by a lease.
"""

import logging
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import metrics
from app.core.errors import Conflict, Forbidden, NotFound
from app.core.settings import get_settings
from app.domain.ai_input import prepare_text, redact_form_section
from app.domain.enums import Role, VerificationStatus
from app.domain.verification_rules import (
    DOCUMENT_TYPE_DESCRIPTIONS,
    SECTION_FOR_DOCUMENT,
    VerificationRequest,
    VerificationResult,
    apply_rules,
)
from app.infra.ai import ProviderError, ProviderUnavailable
from app.infra.ai.factory import get_provider
from app.infra.ai.openai_provider import PROMPT_VERSION
from app.infra.db import session_factory
from app.infra.extraction import extract_text
from app.infra.storage import get_storage
from app.models import Application, Document, User, VerificationRun
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.services.applications import ApplicationService
from app.services.platform_settings import live
from app.services.quotas import AI_PAUSED_REASON, new_run

logger = logging.getLogger("permitflow.verification")

TERMINAL = {
    VerificationStatus.VERIFIED,
    VerificationStatus.ISSUES_FOUND,
    VerificationStatus.NEEDS_REVIEW,
    VerificationStatus.UNREADABLE,
    VerificationStatus.FAILED,
    VerificationStatus.UNAVAILABLE,
    VerificationStatus.DEAD,
}
MAX_ATTEMPTS = 3
REPLACED_REASON = "document_replaced"


def start_run(run_id: uuid.UUID) -> None:
    """The request's background task. Inline: run the check here. Worker: the run is already queued, so
    only wake the workers (a missed wake-up costs at most the polling interval)."""
    if get_settings().verification_mode == "inline":
        run_verification(run_id)
        return
    try:
        with session_factory()() as db:
            DocumentRepository(db).notify_queue()
            db.commit()
    except Exception:  # noqa: BLE001 - the workers poll anyway; the request has already been answered
        logger.exception("verification_notify_failed")


def run_verification(run_id: uuid.UUID) -> None:
    """Inline mode: claim the pending run (the atomic pending-to-running move: true for one caller only)
    and execute it."""
    with session_factory()() as db:
        claimed = DocumentRepository(db).claim_run(run_id, datetime.now(UTC))
        db.commit()
    if claimed:
        execute_run(run_id)


def execute_run(run_id: uuid.UUID, worker_id: str | None = None) -> None:
    """Run a claimed check. `worker_id` is the claimant (None inline); the result is written only while the
    run is still `running` and still held by it, so a duplicate execution is harmless (at-least-once)."""
    settings = get_settings()
    with session_factory()() as db:
        run = db.get(VerificationRun, run_id)
        if run is None or run.status != VerificationStatus.RUNNING or run.worker_id != worker_id:
            return
        doc = db.get(Document, run.document_id)
        app = db.get(Application, doc.application_id) if doc else None
        if doc is None or app is None:
            return
        # End the read transaction here: the session keeps the loaded rows (expire_on_commit=False) but
        # returns its pooled connection while the file is read and the model is called, so a burst of slow
        # checks cannot park every connection and starve the API. `_finish` opens a new one to write.
        db.commit()
        started = time.perf_counter()

        try:
            data = b"".join(get_storage().open(doc.stored_key))
            max_chars = live().int_value("ai_max_text_chars")
            extracted = extract_text(doc.content_type, data, max_chars=max_chars)
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

            # US-101: a check created before the administrator paused the AI is stopped here, before
            # any provider is chosen or called.
            if live().bool_value("ai_paused"):
                _finish(
                    db,
                    run,
                    app,
                    VerificationStatus.UNAVAILABLE,
                    provider="none",
                    error_reason=AI_PAUSED_REASON,
                    started=started,
                )
                return

            # The draft may have been deleted, or the file replaced, while the text was read: look again
            # before anything leaves the system. A deleted draft's text never reaches the provider.
            with db.no_autoflush:
                state = DocumentRepository(db).lifecycle(run.id)
            if state == "removed":
                db.rollback()
                return
            if state == "replaced":
                _finish(
                    db,
                    run,
                    app,
                    VerificationStatus.UNAVAILABLE,
                    provider="none",
                    error_reason=REPLACED_REASON,
                    started=started,
                )
                return
            db.commit()  # keep the extracted text, and give the connection back during the model call

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

            # Clean, check and redact before anything reaches the provider (US-102).
            # The cap is applied again after NFKC, which can expand a character many times over.
            prepared = prepare_text(extracted.text, max_chars=max_chars)
            section_key = SECTION_FOR_DOCUMENT[doc.document_type.value]
            request = VerificationRequest(
                document_type=doc.document_type.value,
                document_type_description=DOCUMENT_TYPE_DESCRIPTIONS[doc.document_type.value],
                form_section=redact_form_section(dict(app.draft_data.get(section_key) or {})),
                text=prepared.text,
                extra={"verification_run_id": run.id, "application_id": app.id, "document_id": doc.id},
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
                result,
                confidence_threshold=settings.ai_confidence_threshold,
                injection_phrases=prepared.injection,
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
            if run is not None and run.status == VerificationStatus.RUNNING and run.worker_id == worker_id:
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
    """Fixed vocabulary stored on the run and served to clients; the exception detail goes to the log only."""
    logger.warning(
        "verification_error", extra={"extra_fields": {"error": f"{type(exc).__name__}: {exc}"[:500]}}
    )
    if isinstance(exc, ProviderUnavailable):
        return "provider_unavailable"
    if isinstance(exc, ProviderError):
        return "provider_error"
    if isinstance(exc, (OSError, FileNotFoundError)):
        return "storage_error"
    return "internal_error"


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
    # Only the holder of the run writes its result, under a row lock: if the draft was deleted (the run
    # is gone) or the lease was taken over by another worker, this result is dropped.
    with db.no_autoflush:  # the lock comes first; the result is flushed under it
        held = DocumentRepository(db).lock_state(run.id) == (VerificationStatus.RUNNING, run.worker_id)
    if not held:
        db.rollback()
        logger.warning("verification_result_dropped", extra={"extra_fields": {"run_id": str(run.id)}})
        return
    run.lease_until = None
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
            "model": model,
            "prompt_version": PROMPT_VERSION if provider == "openai" else None,
            "error_reason": error_reason,
        },
    )
    db.commit()
    metrics.VERIFICATION_RUNS.labels(status.value, provider).inc()
    metrics.VERIFICATION_SECONDS.labels(provider).observe(run.latency_ms / 1000)
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


def claim_next_run(worker_id: str) -> uuid.UUID | None:
    """Worker mode: take the oldest queued run and commit the claim at once. From here the lease, not a
    transaction, says the run is being worked."""
    now = datetime.now(UTC)
    lease_until = now + timedelta(seconds=get_settings().worker_lease_seconds)
    with session_factory()() as db:
        run_id = DocumentRepository(db).claim_next(worker_id, now, lease_until)
        db.commit()
        return run_id


def release_run(run_id: uuid.UUID, worker_id: str) -> bool:
    """Worker shutdown: hand an unfinished run back to the queue."""
    with session_factory()() as db:
        released = DocumentRepository(db).release_lease(run_id, worker_id)
        db.commit()
        return released


def _interrupted_after(grace_seconds: int = 60) -> timedelta:
    """How long a lease-less `running` run may last before it counts as interrupted."""
    return timedelta(seconds=get_settings().ai_timeout_seconds * 2 + grace_seconds)


def reap_expired_runs() -> tuple[int, int]:
    """Worker mode: runs whose lease ran out (the worker died or hung) go back to the queue, or die after
    `MAX_ATTEMPTS` claims. Returns (requeued, dead). A dead run is audited like any finished check. A
    `running` run with no lease began inline before the switch to worker mode (the startup sweep is skipped
    there): once older than the sweep's cutoff it becomes `failed: interrupted`."""
    now = datetime.now(UTC)
    with session_factory()() as db:
        requeued, dead_ids = DocumentRepository(db).reap_expired(now, MAX_ATTEMPTS)
        stranded = DocumentRepository(db).fail_stranded_inline(now - _interrupted_after(), now)
        for run_id in dead_ids:
            run = db.get(VerificationRun, run_id)
            doc = db.get(Document, run.document_id) if run else None
            if run is None:
                continue
            AuditRepository(db).record(
                application_id=doc.application_id if doc else None,
                actor_id=None,
                event_type="verification.completed",
                payload={
                    "run_id": str(run.id),
                    "document_id": str(run.document_id),
                    "status": VerificationStatus.DEAD.value,
                    "provider": run.provider,
                    "error_reason": run.error_reason,
                    "attempts": run.attempts,
                },
            )
            metrics.VERIFICATION_RUNS.labels(VerificationStatus.DEAD.value, run.provider).inc()
        db.commit()
    metrics.REAPED.labels("requeued").inc(requeued)
    metrics.REAPED.labels("dead").inc(len(dead_ids))
    metrics.REAPED.labels("interrupted").inc(stranded)
    return requeued, len(dead_ids)


def mark_stale_runs_failed(grace_seconds: int = 60) -> int:
    """On startup, runs still `running` longer than timeout + grace were interrupted by a restart, and any
    `pending` run was too: background tasks live in the process that died, so nothing will ever claim it.
    Both become `failed: interrupted` so re-run is possible and the queue does not show them as checking
    forever."""
    cutoff = datetime.now(UTC) - _interrupted_after(grace_seconds)
    with session_factory()() as db:
        count = DocumentRepository(db).fail_interrupted_runs(cutoff, datetime.now(UTC))
        db.commit()
        return count


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
        # Row lock so two concurrent re-run requests cannot both insert a pending run.
        app = self.applications.get_for(user, application_id, for_update=True)
        doc = self.documents.get_in_application(app.id, document_id)
        if doc is None or not doc.is_current:
            raise NotFound("Document not found.")
        if user.role == Role.OPERATOR:
            # Same rule as replacing the file: once the document is with the officer, the operator cannot
            # keep re-running a non-deterministic check until it flips (the officer still can).
            _, editable_types = ApplicationService(self.db).editable_for(app)
            if doc.document_type not in editable_types:
                raise Forbidden("This document is with the licensing office and cannot be re-checked now.")
        latest = self.documents.latest_run(doc.id)
        if latest is not None and latest.status not in TERMINAL:
            raise Conflict("A check is already in progress for this document.")
        run = new_run(self.db, doc.id, app.operator_id)
        self.documents.add_run(run)
        self.audit.record(
            application_id=app.id,
            actor_id=user.id,
            event_type="verification.requested",
            payload={"document_id": str(doc.id), "document_type": doc.document_type.value},
        )
        self.db.commit()
        self.db.refresh(run)
        return run
