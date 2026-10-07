"""The site visit checklist (US-060): the template for officers and admins, the officer's draft."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DbSession, OfficerOrAdmin, OfficerUser
from app.schemas.checklist import ChecklistOut, ChecklistSaveIn, ChecklistSchemaOut
from app.services.checklist import ChecklistService, schema_out

router = APIRouter()


@router.get("/checklist-schema", response_model=ChecklistSchemaOut)
def checklist_schema(_: OfficerOrAdmin) -> ChecklistSchemaOut:
    return schema_out()


@router.post(
    "/officer/applications/{application_id}/checklist",
    response_model=ChecklistOut,
    status_code=status.HTTP_201_CREATED,
)
def open_checklist(
    application_id: uuid.UUID, user: OfficerUser, db: DbSession, response: Response
) -> ChecklistOut:
    """Create the current visit's draft (201) or return the one that exists (200)."""
    service = ChecklistService(db)
    row, created = service.create_or_get(user, application_id)
    if not created:
        response.status_code = status.HTTP_200_OK
    return service.get(user, application_id, visit_no=row.visit_no)


@router.get("/officer/applications/{application_id}/checklist", response_model=ChecklistOut)
def read_checklist(
    application_id: uuid.UUID,
    user: OfficerOrAdmin,
    db: DbSession,
    visit: Annotated[int | None, Query(ge=1)] = None,
) -> ChecklistOut:
    return ChecklistService(db).get(user, application_id, visit_no=visit)


@router.put("/officer/applications/{application_id}/checklist", response_model=ChecklistOut)
def save_checklist(
    application_id: uuid.UUID, body: ChecklistSaveIn, user: OfficerUser, db: DbSession
) -> ChecklistOut:
    return ChecklistService(db).save(user, application_id, body)


@router.post("/officer/applications/{application_id}/checklist/submit", response_model=ChecklistOut)
def submit_checklist(application_id: uuid.UUID, user: OfficerUser, db: DbSession) -> ChecklistOut:
    """Freeze the findings and move the case to Awaiting Post-Site Clarification (US-063)."""
    return ChecklistService(db).submit(user, application_id)
