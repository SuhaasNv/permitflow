"""Officer endpoints. Every route requires the officer role (SEC-003); operators receive 403."""

import uuid

from fastapi import APIRouter, BackgroundTasks, status

from app.api.deps import DbSession, OfficerUser
from app.domain.feedback_templates import TEMPLATES
from app.schemas.officer import (
    AuditTrailOut,
    FeedbackIn,
    FeedbackTemplateOut,
    OfficerApplicationOut,
    QueueOut,
    TransitionIn,
)
from app.services.audit_trail import AuditTrailService
from app.services.feedback import FeedbackService
from app.services.officer_queue import OfficerQueueService
from app.services.officer_view import OfficerViewService
from app.services.verification import VerificationService, run_verification
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/officer")


@router.get("/applications", response_model=QueueOut)
def review_queue(user: OfficerUser, db: DbSession) -> QueueOut:
    """Review queue: every submitted application, newest activity first (FR-015)."""
    return OfficerQueueService(db).queue()


@router.get("/applications/{application_id}", response_model=OfficerApplicationOut)
def officer_application(application_id: uuid.UUID, user: OfficerUser, db: DbSession) -> OfficerApplicationOut:
    """Full submission: current revision, documents with verification detail, history, actions (FR-016)."""
    return OfficerViewService(db).get(user, application_id)


@router.post("/applications/{application_id}/transition", response_model=OfficerApplicationOut)
def transition_application(
    application_id: uuid.UUID, payload: TransitionIn, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Move the application along the state machine (FR-019). 409 on an invalid edge or a stale version."""
    app = WorkflowService(db).transition(
        user, application_id, payload.target, note=payload.note, expected_version=payload.expected_version
    )
    return OfficerViewService(db).build(app, viewer=user)


@router.post(
    "/applications/{application_id}/documents/{document_id}/verify",
    response_model=OfficerApplicationOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def officer_rerun_check(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    user: OfficerUser,
    db: DbSession,
    background: BackgroundTasks,
) -> OfficerApplicationOut:
    """Re-run the AI check on a document (AI-009). Same rules as the operator re-run: only when the latest run
    is terminal; audited as `verification.requested` with the officer as actor."""
    run = VerificationService(db).rerun(user, application_id, document_id)
    background.add_task(run_verification, run.id)
    service = OfficerViewService(db)
    return service.get(user, application_id)


@router.get("/feedback-templates", response_model=list[FeedbackTemplateOut])
def feedback_templates(user: OfficerUser) -> list[FeedbackTemplateOut]:
    """Predefined comment templates (FR-018, US-024). The officer edits the text before sending."""
    return [
        FeedbackTemplateOut(
            key=t.key,
            title=t.title,
            target_type=t.target_type.value,
            section_key=t.section_key,
            document_type=t.document_type.value if t.document_type else None,
            message=t.message,
        )
        for t in TEMPLATES
    ]


@router.post(
    "/applications/{application_id}/feedback",
    response_model=OfficerApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(
    application_id: uuid.UUID, payload: FeedbackIn, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Add a feedback item tied to a section or a document type; only while Under Review (409 otherwise)."""
    FeedbackService(db).create(
        user,
        application_id,
        target_type=payload.target_type,
        section_key=payload.section_key,
        document_type=payload.document_type,
        message=payload.message,
        template_key=payload.template_key,
    )
    return OfficerViewService(db).get(user, application_id)


@router.post(
    "/applications/{application_id}/feedback/{feedback_id}/withdraw", response_model=OfficerApplicationOut
)
def withdraw_feedback(
    application_id: uuid.UUID, feedback_id: uuid.UUID, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Withdraw an open item; only while Under Review (409 otherwise)."""
    FeedbackService(db).withdraw(user, application_id, feedback_id)
    return OfficerViewService(db).get(user, application_id)


@router.post(
    "/applications/{application_id}/feedback/{feedback_id}/resolve", response_model=OfficerApplicationOut
)
def resolve_feedback(
    application_id: uuid.UUID, feedback_id: uuid.UUID, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Mark an open or addressed item resolved (FR-024). Audited; 409 outside the officer's states."""
    FeedbackService(db).resolve(user, application_id, feedback_id)
    return OfficerViewService(db).get(user, application_id)


@router.post(
    "/applications/{application_id}/feedback/{feedback_id}/restore", response_model=OfficerApplicationOut
)
def restore_feedback(
    application_id: uuid.UUID, feedback_id: uuid.UUID, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Undo the caller's own withdraw or resolve within the grace window (US-039). 409 once it has closed."""
    FeedbackService(db).restore(user, application_id, feedback_id)
    return OfficerViewService(db).get(user, application_id)


@router.get("/applications/{application_id}/audit", response_model=AuditTrailOut)
def audit_trail(application_id: uuid.UUID, user: OfficerUser, db: DbSession) -> AuditTrailOut:
    """Append-only history of everything that happened to the application (FR-025, SEC-009)."""
    return AuditTrailService(db).for_application(user, application_id)
