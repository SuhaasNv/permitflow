import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession, OperatorUser, require_role
from app.core.errors import BadRequest
from app.core.settings import get_settings
from app.domain.enums import ApplicationStatus, DocumentType
from app.domain.uploads import too_large_message
from app.models import Application, User
from app.models.enums import Role
from app.schemas.applications import (
    ApplicationOperatorView,
    ApplicationSummaryOut,
    RevisionSummaryView,
    UploadOut,
)
from app.schemas.compare import CompareOut
from app.services.applications import ApplicationService
from app.services.compare import CompareService
from app.services.documents import DocumentService, content_disposition
from app.services.operator_view import document_view, operator_view, summary
from app.services.resubmission import ResubmissionService
from app.services.submission import SubmissionService
from app.services.verification import VerificationService, run_verification

router = APIRouter(prefix="/applications")

# Multipart framing plus the document_type field; anything beyond the file itself.
_MULTIPART_OVERHEAD = 16 * 1024


def _reject_oversized_body(request: Request) -> None:
    """Refuse an upload from its Content-Length before Starlette buffers the multipart body (T7)."""
    limit = get_settings().upload_max_bytes
    raw = request.headers.get("content-length")
    if raw and raw.isdigit() and int(raw) > limit + _MULTIPART_OVERHEAD:
        raise BadRequest(too_large_message(limit), details={"reason": "too_large"})


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
    )


@router.get("", response_model=list[ApplicationSummaryOut])
def list_applications(user: OperatorUser, db: DbSession) -> list[ApplicationSummaryOut]:
    service = ApplicationService(db)
    apps = service.list_for(user)
    present, revisions = service.list_stats(apps)
    return [
        summary(a, present_types=present.get(a.id, set()), revision_count=revisions.get(a.id, 0))
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
    user: Annotated[User, Depends(require_role(Role.OPERATOR, Role.OFFICER))],
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
    dependencies=[Depends(_reject_oversized_body)],
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
    user: Annotated[User, Depends(require_role(Role.OPERATOR, Role.OFFICER))],
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
    user: CurrentUser,
    db: DbSession,
    background: BackgroundTasks,
) -> UploadOut:
    run = VerificationService(db).rerun(user, application_id, document_id)
    background.add_task(run_verification, run.id)
    service = ApplicationService(db)
    app = service.get_for(user, application_id)
    doc = next(d for d, _ in service.documents_with_runs(app) if d.id == document_id)
    return UploadOut(application=_view(service, app), document=document_view(doc, run), unchanged=False)
