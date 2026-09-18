"""Officer endpoints. Every route requires the officer role (SEC-003); operators receive 403."""

from fastapi import APIRouter

from app.api.deps import DbSession, OfficerUser
from app.api.v1.officer_schemas import QueueOut
from app.services.officer_queue import OfficerQueueService

router = APIRouter(prefix="/officer")


@router.get("/applications", response_model=QueueOut)
def review_queue(user: OfficerUser, db: DbSession) -> QueueOut:
    """Review queue: every submitted application, newest activity first (FR-015)."""
    return OfficerQueueService(db).queue()
