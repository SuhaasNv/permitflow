"""Build the officer-facing view of a submitted application: the current revision, its documents with full
verification detail, the revision history and the transitions available right now."""

import uuid

from sqlalchemy.orm import Session

from app.api.v1.officer_schemas import (
    ActionOut,
    ApplicantOut,
    FeedbackOut,
    OfficerApplicationOut,
    OfficerDocumentOut,
    OfficerSectionOut,
    OfficerVerificationOut,
    RevisionOut,
    VerificationSummaryOut,
)
from app.core.errors import NotFound
from app.domain import completeness as completeness_rules
from app.domain.enums import ApplicationStatus, FeedbackResolution, VerificationStatus
from app.domain.form_schema import SECTIONS
from app.domain.labels import officer_label, tone_for
from app.domain.workflow import Actor, TransitionContext, available_actions
from app.models import Application, ApplicationRevision, Document, Feedback, User, VerificationRun
from app.repositories.applications import ApplicationRepository
from app.repositories.documents import DocumentRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.revisions import RevisionRepository
from app.repositories.users import UserRepository
from app.services.feedback import target_label
from app.services.operator_view import LICENCE_TITLE

_NOTE_REQUIRED_TARGETS = {ApplicationStatus.REJECTED}

_FEEDBACK_LOCK: dict[ApplicationStatus, str] = {
    ApplicationStatus.APPLICATION_RECEIVED: "Start the review to add feedback.",
    ApplicationStatus.PRE_SITE_RESUBMITTED: "Start the review of this resubmission to add feedback.",
    ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION: (
        "Feedback is frozen while the operator responds; it reopens when they resubmit."
    ),
    ApplicationStatus.APPROVED: "This application is decided.",
    ApplicationStatus.REJECTED: "This application is decided.",
}


class OfficerViewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.documents = DocumentRepository(db)
        self.revisions = RevisionRepository(db)
        self.feedback = FeedbackRepository(db)
        self.users = UserRepository(db)

    def get(self, officer: User, application_id: uuid.UUID) -> OfficerApplicationOut:
        app = self.applications.get_for(officer, application_id)
        return self.build(app)

    def build(self, app: Application) -> OfficerApplicationOut:
        if app.status == ApplicationStatus.DRAFT:
            raise NotFound("Application not found.")
        revisions = self.revisions.list_for(app.id)
        current = revisions[-1] if revisions else None
        docs = self.documents.current_for(app.id)
        runs = self.documents.latest_runs([d.id for d in docs])
        applicant = self.users.get(app.operator_id)
        if applicant is None:
            raise NotFound("Application not found.")
        feedback = self.feedback.list_for(app.id)
        open_count = sum(1 for f in feedback if f.resolution == FeedbackResolution.OPEN)
        ctx = TransitionContext(open_feedback_count=open_count, has_note=False)
        actions = [
            ActionOut(
                target=str(a["target"].value if hasattr(a["target"], "value") else a["target"]),
                label=str(a["label"]),
                enabled=bool(a["enabled"]),
                reason=(str(a["reason"]) if a["reason"] else None),
                requires_note=a["target"] in _NOTE_REQUIRED_TARGETS,
            )
            for a in available_actions(app.status, Actor.OFFICER, ctx)
        ]
        # Reject's guard needs a note the UI collects first; show it enabled with the requirement flagged.
        for a in actions:
            if a.requires_note and not a.enabled:
                a.enabled = True
                a.reason = None
        return _assemble(app, current, revisions, docs, runs, applicant, actions, feedback, self.users)


def _assemble(
    app: Application,
    current: ApplicationRevision | None,
    revisions: list[ApplicationRevision],
    docs: list[Document],
    runs: dict[uuid.UUID, VerificationRun],
    applicant: User,
    actions: list[ActionOut],
    feedback: list[Feedback],
    users: UserRepository,
) -> OfficerApplicationOut:
    form = current.form_data if current else app.draft_data
    comp = completeness_rules.compute(form, {d.document_type for d in docs})
    sections = [
        OfficerSectionOut(
            key=s.key,
            title=s.title,
            description=s.description,
            data=dict(form.get(s.key) or {}),
            complete=state.complete,
        )
        for s, state in zip(SECTIONS, comp.sections, strict=True)
    ]
    labels = {d.type: d.label for d in comp.documents}
    revision_doc_ids = set(current.document_ids) if current else set()
    documents = [
        OfficerDocumentOut(
            id=d.id,
            document_type=d.document_type.value,
            label=labels.get(d.document_type, d.document_type.value),
            original_filename=d.original_filename,
            content_type=d.content_type,
            size_bytes=d.size_bytes,
            uploaded_at=d.uploaded_at,
            in_current_revision=str(d.id) in revision_doc_ids,
            verification=_verification(runs.get(d.id)),
        )
        for d in docs
    ]
    summary = VerificationSummaryOut(
        total=len(documents),
        verified=sum(1 for d in documents if d.verification and d.verification.status == "verified"),
        issues_found=sum(1 for d in documents if d.verification and d.verification.status == "issues_found"),
        needs_review=sum(1 for d in documents if d.verification and d.verification.status == "needs_review"),
        checking=sum(
            1
            for d in documents
            if d.verification
            and d.verification.status in (VerificationStatus.PENDING.value, VerificationStatus.RUNNING.value)
        ),
        other=0,
    )
    summary.other = (
        summary.total - summary.verified - summary.issues_found - summary.needs_review - summary.checking
    )
    business = (form.get("business") or {}).get("business_name")
    premises = (form.get("premises") or {}).get("address_line_1")
    names: dict[uuid.UUID, str] = {}

    def name_of(user_id: uuid.UUID) -> str:
        if user_id not in names:
            u = users.get(user_id)
            names[user_id] = u.full_name if u else ""
        return names[user_id]

    submitters = {r.submitted_by: name_of(r.submitted_by) for r in revisions}
    revision_numbers = {r.id: r.revision_number for r in revisions}
    feedback_out = [
        FeedbackOut(
            id=f.id,
            target_type=f.target_type.value,
            section_key=f.section_key,
            document_type=f.document_type.value if f.document_type else None,
            target_label=target_label(f),
            message=f.message,
            template_key=f.template_key,
            resolution=f.resolution.value,
            raised_in_revision=revision_numbers.get(f.raised_in_revision_id, 0),
            author_name=name_of(f.author_id),
            created_at=f.created_at,
            released_to_operator_at=f.released_to_operator_at,
            addressed_in_revision=(
                revision_numbers.get(f.addressed_in_revision_id) if f.addressed_in_revision_id else None
            ),
            resolved_at=f.resolved_at,
        )
        for f in feedback
    ]
    editable = app.status == ApplicationStatus.UNDER_REVIEW
    locked_reason = (
        None if editable else _FEEDBACK_LOCK.get(app.status, "Feedback is closed for this status.")
    )
    return OfficerApplicationOut(
        id=app.id,
        reference_no=app.reference_no,
        licence_title=LICENCE_TITLE,
        status=app.status.value,
        status_label=officer_label(app.status),
        status_tone=tone_for(app.status),
        applicant=ApplicantOut(id=applicant.id, full_name=applicant.full_name, email=applicant.email),
        business_name=business if isinstance(business, str) and business else None,
        premises_summary=premises if isinstance(premises, str) and premises else None,
        sections=sections,
        documents=documents,
        missing_document_types=[d.type.value for d in comp.documents if not d.present],
        verification_summary=summary,
        revisions=[
            RevisionOut(
                id=r.id,
                number=r.revision_number,
                submitted_at=r.submitted_at,
                submitted_by=submitters.get(r.submitted_by, ""),
            )
            for r in revisions
        ],
        current_revision_number=current.revision_number if current else 0,
        feedback=feedback_out,
        open_feedback_count=sum(1 for f in feedback if f.resolution == FeedbackResolution.OPEN),
        feedback_editable=editable,
        feedback_locked_reason=locked_reason,
        actions=actions,
        decision_note=app.decision_note,
        version=app.version,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def _verification(run: VerificationRun | None) -> OfficerVerificationOut | None:
    if run is None:
        return None
    return OfficerVerificationOut(
        status=run.status.value,
        summary=run.summary,
        confidence=run.confidence,
        issues=list(run.issues),
        missing_information=list(run.missing_information),
        error_reason=run.error_reason,
        provider=run.provider,
        model=run.model,
        finished_at=run.finished_at,
    )
