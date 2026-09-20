"""Officer endpoints. Every route requires the officer role (SEC-003); operators receive 403."""

import uuid

from fastapi import APIRouter, BackgroundTasks, Response, status

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
from app.schemas.site_visit import SiteVisitDecideIn, SiteVisitProposeIn, SiteVisitRescheduleIn
from app.services.audit_trail import AuditTrailService
from app.services.feedback import FeedbackService
from app.services.licence import LicenceService
from app.services.officer_queue import OfficerQueueService
from app.services.officer_view import OfficerViewService
from app.services.site_visit import SiteVisitService
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
    "/applications/{application_id}/feedback/{feedback_id}/reopen", response_model=OfficerApplicationOut
)
def reopen_feedback(
    application_id: uuid.UUID, feedback_id: uuid.UUID, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Not fixed (US-049): an addressed item is open again for the next round. 409 unless Under Review."""
    FeedbackService(db).reopen(user, application_id, feedback_id)
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


@router.get("/applications/{application_id}/licence/preview")
def preview_licence(application_id: uuid.UUID, user: OfficerUser, db: DbSession) -> Response:
    """What the certificate will say if the officer approves now (US-051). Watermarked; nothing is stored."""
    pdf = LicenceService(db).preview(user, application_id)
    return Response(content=pdf, media_type="application/pdf", headers={"Cache-Control": "no-store"})


@router.post("/applications/{application_id}/site-visit", response_model=OfficerApplicationOut)
def propose_site_visit(
    application_id: uuid.UUID, body: SiteVisitProposeIn, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Propose the visit's date and slot (US-084). From Under Review the case moves to Site Visit
    Scheduled in the same transaction; the operator is told and can accept or propose another date."""
    SiteVisitService(db).propose(
        user,
        application_id,
        visit_date=body.date,
        slot=body.slot,
        note=body.note,
        expected_version=body.expected_version,
    )
    return OfficerViewService(db).get(user, application_id)


@router.post("/applications/{application_id}/site-visit/decide", response_model=OfficerApplicationOut)
def decide_site_visit(
    application_id: uuid.UUID, body: SiteVisitDecideIn, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """On the operator's counter-proposal: accept their date, keep the original, or propose a third."""
    SiteVisitService(db).decide(
        user, application_id, action=body.action, visit_date=body.date, slot=body.slot, note=body.note
    )
    return OfficerViewService(db).get(user, application_id)


@router.post("/applications/{application_id}/site-visit/confirm", response_model=OfficerApplicationOut)
def confirm_site_visit(application_id: uuid.UUID, user: OfficerUser, db: DbSession) -> OfficerApplicationOut:
    """Confirm a proposal the operator left unanswered for three working days."""
    SiteVisitService(db).confirm_without_reply(user, application_id)
    return OfficerViewService(db).get(user, application_id)


@router.post("/applications/{application_id}/site-visit/reschedule", response_model=OfficerApplicationOut)
def reschedule_site_visit(
    application_id: uuid.UUID, body: SiteVisitRescheduleIn, user: OfficerUser, db: DbSession
) -> OfficerApplicationOut:
    """Move a confirmed visit before its date (reason required); the operator answers the new proposal."""
    SiteVisitService(db).reschedule(
        user, application_id, visit_date=body.date, slot=body.slot, reason=body.reason
    )
    return OfficerViewService(db).get(user, application_id)


@router.get("/applications/{application_id}/audit", response_model=AuditTrailOut)
def audit_trail(application_id: uuid.UUID, user: OfficerUser, db: DbSession) -> AuditTrailOut:
    """Append-only history of everything that happened to the application (FR-025, SEC-009)."""
    return AuditTrailService(db).for_application(user, application_id)
