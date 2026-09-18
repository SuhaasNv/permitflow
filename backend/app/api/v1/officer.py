"""Officer endpoints. Every route requires the officer role (SEC-003); operators receive 403."""

import uuid

from fastapi import APIRouter

from app.api.deps import DbSession, OfficerUser
from app.api.v1.officer_schemas import OfficerApplicationOut, QueueOut, TransitionIn
from app.services.officer_queue import OfficerQueueService
from app.services.officer_view import OfficerViewService
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
    return OfficerViewService(db).build(app)
