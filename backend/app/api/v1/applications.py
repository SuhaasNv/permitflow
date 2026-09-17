import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, status

from app.api.deps import DbSession, OperatorUser
from app.api.v1.applications_schemas import ApplicationOperatorView, ApplicationSummaryOut
from app.domain.editability import editable_targets
from app.services.applications import ApplicationService
from app.services.operator_view import operator_view, summary

router = APIRouter(prefix="/applications")


@router.get("", response_model=list[ApplicationSummaryOut])
def list_applications(user: OperatorUser, db: DbSession) -> list[ApplicationSummaryOut]:
    return [summary(a) for a in ApplicationService(db).list_for(user)]


@router.post("", response_model=ApplicationOperatorView, status_code=status.HTTP_201_CREATED)
def create_application(user: OperatorUser, db: DbSession) -> ApplicationOperatorView:
    app = ApplicationService(db).create(user)
    sections, doc_types = editable_targets(app.status, set(), set())
    return operator_view(app, editable_sections=sections, editable_document_types=doc_types)


@router.get("/{application_id}", response_model=ApplicationOperatorView)
def get_application(application_id: uuid.UUID, user: OperatorUser, db: DbSession) -> ApplicationOperatorView:
    app = ApplicationService(db).get_for(user, application_id)
    sections, doc_types = editable_targets(app.status, set(), set())
    return operator_view(app, editable_sections=sections, editable_document_types=doc_types)


@router.patch("/{application_id}/sections/{key}", response_model=ApplicationOperatorView)
def update_section(
    application_id: uuid.UUID,
    key: str,
    user: OperatorUser,
    db: DbSession,
    data: Annotated[dict[str, Any], Body()],
) -> ApplicationOperatorView:
    app = ApplicationService(db).update_section(user, application_id, key, data)
    sections, doc_types = editable_targets(app.status, set(), set())
    return operator_view(app, editable_sections=sections, editable_document_types=doc_types)
