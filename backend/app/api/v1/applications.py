import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import AnyReader, DbSession, OperatorUser, require_role
from app.domain.enums import ApplicationStatus, DocumentType
from app.models import Application, User
from app.models.enums import Role
from app.schemas.applications import (
    ApplicationOperatorView,
    ApplicationSummaryOut,
    RevisionSummaryView,
    UploadOut,
    WithdrawIn,
)
from app.schemas.clarification import (
    ClarificationAttachOut,
    ClarificationOperatorView,
    ClarificationResponseIn,
)
from app.schemas.compare import CompareOut
from app.schemas.site_visit import SiteVisitCounterIn, SiteVisitRescheduleIn
from app.services.applications import ApplicationService
from app.services.checklist import ChecklistService
from app.services.clarification import ClarificationService
from app.services.compare import CompareService
from app.services.documents import DocumentService, content_disposition
from app.services.draft_deletion import DraftDeletionService
from app.services.licence import LicenceService, licence_view
from app.services.operator_view import document_view, operator_view, summary
from app.services.resubmission import ResubmissionService
from app.services.site_visit import SiteVisitService
from app.services.submission import SubmissionService
from app.services.uploads import storage_usage, storage_view
from app.services.verification import VerificationService, run_verification
from app.services.withdrawal import WithdrawalService

router = APIRouter(prefix="/applications")


def _view(service: ApplicationService, app: Application) -> ApplicationOperatorView:
    sections, doc_types = service.editable_for(app)
    documents = service.documents_with_runs(app)
    resub = ResubmissionService(service.db)
    return operator_view(
        app,
        documents=documents,
        editable_sections=sections,
        editable_document_types=doc_types,
        revision_count=service.revision_count(app),
        feedback=resub.released_feedback(app) if app.status != ApplicationStatus.DRAFT else [],
        resubmit=resub.readiness(app, [d for d, _ in documents]),
        revisions=[
            RevisionSummaryView(number=r.revision_number, submitted_at=r.submitted_at)
            for r in service.revisions.list_for(app.id)
        ],
        licence=licence_view(LicenceService(service.db).for_application(app.id)),
        site_visit=SiteVisitService(service.db).operator_view(app),
        open_clarifications=ChecklistService(service.db).facts(app).open_clarifications,
        clarification=ClarificationService(service.db).block(app),
        storage=storage_view(storage_usage(service.db, app.id)),
    )


@router.get("", response_model=list[ApplicationSummaryOut])
def list_applications(user: OperatorUser, db: DbSession) -> list[ApplicationSummaryOut]:
    service = ApplicationService(db)
    apps = service.list_for(user)
    present, revisions = service.list_stats(apps)
    ids = [a.id for a in apps]
    awaiting = SiteVisitService(db).awaits_operator(ids)
    open_items = ClarificationService(db).open_counts(ids)
    return [
        summary(
            a,
            present_types=present.get(a.id, set()),
            revision_count=revisions.get(a.id, 0),
            visit_awaits_operator=a.id in awaiting,
            open_clarifications=open_items.get(a.id, 0),
        )
        for a in apps
    ]


@router.post("", response_model=ApplicationOperatorView, status_code=status.HTTP_201_CREATED)
def create_application(user: OperatorUser, db: DbSession) -> ApplicationOperatorView:
    service = ApplicationService(db)
    return _view(service, service.create(user))


@router.get("/{application_id}", response_model=ApplicationOperatorView)
def get_application(application_id: uuid.UUID, user: OperatorUser, db: DbSession) -> ApplicationOperatorView:
    service = ApplicationService(db)
    return _view(service, service.get_for(user, application_id))


@router.post("/{application_id}/submit", response_model=ApplicationOperatorView)
def submit_application(
    application_id: uuid.UUID, user: OperatorUser, db: DbSession
) -> ApplicationOperatorView:
    app = SubmissionService(db).submit(user, application_id)
    return _view(ApplicationService(db), app)


@router.get("/{application_id}/compare", response_model=CompareOut)
def compare_revisions(
    application_id: uuid.UUID,
    user: AnyReader,
    db: DbSession,
    from_revision: Annotated[int, Query(alias="from", ge=1)],
    to_revision: Annotated[int, Query(alias="to", ge=1)],
) -> CompareOut:
    """Field-level and document-level diff between two revisions (FR-022). Owner or officer."""
    return CompareService(db).compare(user, application_id, from_revision, to_revision)


@router.post("/{application_id}/resubmit", response_model=ApplicationOperatorView)
def resubmit_application(
    application_id: uuid.UUID, user: OperatorUser, db: DbSession
) -> ApplicationOperatorView:
    """Resubmit after feedback: Revision N+1, flagged items that changed become addressed, officers notified.
    422 `no_change` when nothing flagged changed; 409 when the status does not allow it."""
    app = ResubmissionService(db).resubmit(user, application_id)
    return _view(ApplicationService(db), app)


@router.get("/{application_id}/licence")
def download_licence(
    application_id: uuid.UUID,
    user: AnyReader,
    db: DbSession,
) -> StreamingResponse:
    """The issued licence certificate as a PDF (US-051). Owner or officer; 404 before approval."""
    licence, chunks = LicenceService(db).open_for_download(user, application_id)
    return StreamingResponse(
        chunks,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition(f"{licence.licence_no}.pdf")},
    )


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(application_id: uuid.UUID, user: OperatorUser, db: DbSession) -> None:
    """Delete a draft outright, files included (US-045). 409 once submitted: withdraw instead."""
    DraftDeletionService(db).delete(user, application_id)


@router.post("/{application_id}/withdraw", response_model=ApplicationOperatorView)
def withdraw_application(
    application_id: uuid.UUID, user: OperatorUser, db: DbSession, body: WithdrawIn
) -> ApplicationOperatorView:
    """Withdraw a submitted application (US-038): terminal, owner only, optional reason, officers notified.
    409 for drafts and decided applications."""
    app = WithdrawalService(db).withdraw(user, application_id, body.reason)
    return _view(ApplicationService(db), app)


@router.post("/{application_id}/site-visit/accept", response_model=ApplicationOperatorView)
def accept_site_visit(
    application_id: uuid.UUID, user: OperatorUser, db: DbSession
) -> ApplicationOperatorView:
    """Accept the date and slot the officer proposed (US-084); officers are told."""
    SiteVisitService(db).accept(user, application_id)
    service = ApplicationService(db)
    return _view(service, service.get_for(user, application_id))


@router.post("/{application_id}/site-visit/counter", response_model=ApplicationOperatorView)
def counter_site_visit(
    application_id: uuid.UUID, user: OperatorUser, db: DbSession, body: SiteVisitCounterIn
) -> ApplicationOperatorView:
    """Propose another date and slot with a reason; the officer decides."""
    SiteVisitService(db).counter(
        user, application_id, visit_date=body.date, slot=body.slot, reason=body.reason
    )
    service = ApplicationService(db)
    return _view(service, service.get_for(user, application_id))


@router.post("/{application_id}/site-visit/reschedule", response_model=ApplicationOperatorView)
def reschedule_site_visit(
    application_id: uuid.UUID, user: OperatorUser, db: DbSession, body: SiteVisitRescheduleIn
) -> ApplicationOperatorView:
    """Ask to move a confirmed visit before its date (reason required); the officer decides."""
    SiteVisitService(db).reschedule(
        user, application_id, visit_date=body.date, slot=body.slot, reason=body.reason
    )
    service = ApplicationService(db)
    return _view(service, service.get_for(user, application_id))


@router.get("/{application_id}/clarifications", response_model=ClarificationOperatorView)
def clarifications(application_id: uuid.UUID, user: OperatorUser, db: DbSession) -> ClarificationOperatorView:
    """Only the flagged items with a released question, in operator words (US-064)."""
    return ClarificationService(db).operator_view(user, application_id)


@router.post(
    "/{application_id}/clarifications/{item_id}/responses",
    response_model=ClarificationOperatorView,
)
def respond_to_clarification(
    application_id: uuid.UUID,
    item_id: uuid.UUID,
    body: ClarificationResponseIn,
    user: OperatorUser,
    db: DbSession,
) -> ClarificationOperatorView:
    """Draft or rewrite the answer to the open question on one item (US-065)."""
    return ClarificationService(db).respond(user, application_id, item_id, body.message)


@router.post(
    "/{application_id}/clarifications/responses/{response_id}/attachments",
    response_model=ClarificationAttachOut,
    status_code=status.HTTP_201_CREATED,
)
def attach_to_response(
    application_id: uuid.UUID,
    response_id: uuid.UUID,
    user: OperatorUser,
    db: DbSession,
    file: Annotated[UploadFile, File()],
) -> ClarificationAttachOut:
    view, unchanged = ClarificationService(db).attach(
        user, application_id, response_id, file.filename or "", file.content_type, file.file
    )
    return ClarificationAttachOut(view=view, unchanged=unchanged)


@router.delete(
    "/{application_id}/clarifications/responses/{response_id}/attachments/{attachment_id}",
    response_model=ClarificationOperatorView,
)
def remove_attachment(
    application_id: uuid.UUID,
    response_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: OperatorUser,
    db: DbSession,
) -> ClarificationOperatorView:
    return ClarificationService(db).remove_attachment(user, application_id, response_id, attachment_id)


@router.post("/{application_id}/clarifications/send", response_model=ClarificationOperatorView)
def send_clarifications(
    application_id: uuid.UUID, user: OperatorUser, db: DbSession
) -> ClarificationOperatorView:
    """Send every drafted answer of the round; the case moves to Post-Site Clarification Resubmitted."""
    return ClarificationService(db).send(user, application_id)


@router.get("/{application_id}/clarifications/attachments/{attachment_id}/download")
def download_attachment(
    application_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: Annotated[User, Depends(require_role(Role.OPERATOR, Role.OFFICER, Role.ADMIN))],
    db: DbSession,
) -> StreamingResponse:
    row, chunks = ClarificationService(db).open_attachment(user, application_id, attachment_id)
    return StreamingResponse(
        chunks,
        media_type=row.content_type,
        headers={
            "Content-Disposition": content_disposition(row.original_filename),
            "Content-Length": str(row.size_bytes),
        },
    )


@router.patch("/{application_id}/sections/{key}", response_model=ApplicationOperatorView)
def update_section(
    application_id: uuid.UUID,
    key: str,
    user: OperatorUser,
    db: DbSession,
    data: Annotated[dict[str, Any], Body()],
) -> ApplicationOperatorView:
    service = ApplicationService(db)
    return _view(service, service.update_section(user, application_id, key, data))


@router.post(
    "/{application_id}/documents",
    response_model=UploadOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    application_id: uuid.UUID,
    user: OperatorUser,
    db: DbSession,
    document_type: Annotated[DocumentType, Form()],
    file: Annotated[UploadFile, File()],
    background: BackgroundTasks,
) -> UploadOut:
    result = DocumentService(db).upload(
        user, application_id, document_type, file.filename or "", file.content_type, file.file
    )
    if result.run is not None and not result.unchanged:
        background.add_task(run_verification, result.run.id)
    service = ApplicationService(db)
    return UploadOut(
        application=_view(service, result.application),
        document=document_view(result.document, result.run),
        unchanged=result.unchanged,
    )


@router.delete("/{application_id}/documents/{document_id}", response_model=ApplicationOperatorView)
def delete_document(
    application_id: uuid.UUID, document_id: uuid.UUID, user: OperatorUser, db: DbSession
) -> ApplicationOperatorView:
    app = DocumentService(db).delete(user, application_id, document_id)
    return _view(ApplicationService(db), app)


@router.get("/{application_id}/documents/{document_id}/download")
def download_document(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    user: AnyReader,
    db: DbSession,
) -> StreamingResponse:
    doc, chunks = DocumentService(db).open_for_download(user, application_id, document_id)
    return StreamingResponse(
        chunks,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": content_disposition(doc.original_filename),
            "Content-Length": str(doc.size_bytes),
        },
    )


@router.post(
    "/{application_id}/documents/{document_id}/verify",
    response_model=UploadOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def rerun_verification(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    user: Annotated[User, Depends(require_role(Role.OPERATOR, Role.OFFICER))],
    db: DbSession,
    background: BackgroundTasks,
) -> UploadOut:
    """Re-run the check on a current document (SCOPE S2). Owner or officer; 409 while one is running."""
    run = VerificationService(db).rerun(user, application_id, document_id)
    background.add_task(run_verification, run.id)
    service = ApplicationService(db)
    app = service.get_for(user, application_id)
    doc = next(d for d, _ in service.documents_with_runs(app) if d.id == document_id)
    return UploadOut(application=_view(service, app), document=document_view(doc, run), unchanged=False)
