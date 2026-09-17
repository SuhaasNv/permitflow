import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, File, Form, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DbSession, OperatorUser
from app.api.v1.applications_schemas import ApplicationOperatorView, ApplicationSummaryOut, UploadOut
from app.domain.editability import editable_targets
from app.domain.enums import DocumentType
from app.models import Application
from app.services.applications import ApplicationService
from app.services.documents import DocumentService
from app.services.operator_view import document_view, operator_view, summary

router = APIRouter(prefix="/applications")


def _view(service: ApplicationService, app: Application) -> ApplicationOperatorView:
    sections, doc_types = editable_targets(app.status, set(), set())
    return operator_view(
        app,
        documents=service.documents_with_runs(app),
        editable_sections=sections,
        editable_document_types=doc_types,
    )


@router.get("", response_model=list[ApplicationSummaryOut])
def list_applications(user: OperatorUser, db: DbSession) -> list[ApplicationSummaryOut]:
    service = ApplicationService(db)
    return [
        summary(a, present_types={d.document_type for d, _ in service.documents_with_runs(a)})
        for a in service.list_for(user)
    ]


@router.post("", response_model=ApplicationOperatorView, status_code=status.HTTP_201_CREATED)
def create_application(user: OperatorUser, db: DbSession) -> ApplicationOperatorView:
    service = ApplicationService(db)
    return _view(service, service.create(user))


@router.get("/{application_id}", response_model=ApplicationOperatorView)
def get_application(application_id: uuid.UUID, user: OperatorUser, db: DbSession) -> ApplicationOperatorView:
    service = ApplicationService(db)
    return _view(service, service.get_for(user, application_id))


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


@router.post("/{application_id}/documents", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    application_id: uuid.UUID,
    user: OperatorUser,
    db: DbSession,
    document_type: Annotated[DocumentType, Form()],
    file: Annotated[UploadFile, File()],
) -> UploadOut:
    result = DocumentService(db).upload(
        user, application_id, document_type, file.filename or "", file.content_type, file.file
    )
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
    application_id: uuid.UUID, document_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> StreamingResponse:
    doc, chunks = DocumentService(db).open_for_download(user, application_id, document_id)
    safe_name = doc.original_filename.replace('"', "")
    return StreamingResponse(
        chunks,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Length": str(doc.size_bytes),
        },
    )
