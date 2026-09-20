import uuid
from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Checklist,
    ChecklistItem,
    ClarificationAttachment,
    ClarificationRequest,
    ClarificationResponse,
)


class ChecklistRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def current_for(self, application_id: uuid.UUID) -> Checklist | None:
        """The checklist of the latest visit (highest visit number), or None before any is created."""
        stmt = (
            select(Checklist)
            .where(Checklist.application_id == application_id)
            .order_by(Checklist.visit_no.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get(self, application_id: uuid.UUID, visit_no: int) -> Checklist | None:
        stmt = select(Checklist).where(
            Checklist.application_id == application_id, Checklist.visit_no == visit_no
        )
        return self.db.scalar(stmt)

    def list_for(self, application_id: uuid.UUID) -> list[Checklist]:
        stmt = (
            select(Checklist).where(Checklist.application_id == application_id).order_by(Checklist.visit_no)
        )
        return list(self.db.scalars(stmt))

    def current_for_many(self, application_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Checklist]:
        ids = list(application_ids)
        if not ids:
            return {}
        stmt = (
            select(Checklist)
            .where(Checklist.application_id.in_(ids))
            .order_by(Checklist.application_id, Checklist.visit_no.desc())
        )
        out: dict[uuid.UUID, Checklist] = {}
        for row in self.db.scalars(stmt):
            out.setdefault(row.application_id, row)
        return out

    def items_for(self, checklist_id: uuid.UUID) -> list[ChecklistItem]:
        stmt = (
            select(ChecklistItem)
            .where(ChecklistItem.checklist_id == checklist_id)
            .order_by(ChecklistItem.position)
        )
        return list(self.db.scalars(stmt))

    def requests_for_items(self, item_ids: Iterable[uuid.UUID]) -> list[ClarificationRequest]:
        ids = list(item_ids)
        if not ids:
            return []
        stmt = (
            select(ClarificationRequest)
            .where(ClarificationRequest.item_id.in_(ids))
            .order_by(ClarificationRequest.item_id, ClarificationRequest.round_no)
        )
        return list(self.db.scalars(stmt))

    def responses_for_requests(
        self, request_ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, ClarificationResponse]:
        ids = list(request_ids)
        if not ids:
            return {}
        stmt = select(ClarificationResponse).where(ClarificationResponse.request_id.in_(ids))
        return {r.request_id: r for r in self.db.scalars(stmt)}

    def attachments_for_responses(
        self, response_ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, list[ClarificationAttachment]]:
        ids = list(response_ids)
        if not ids:
            return {}
        stmt = (
            select(ClarificationAttachment)
            .where(ClarificationAttachment.response_id.in_(ids))
            .order_by(ClarificationAttachment.uploaded_at)
        )
        out: dict[uuid.UUID, list[ClarificationAttachment]] = {}
        for a in self.db.scalars(stmt):
            out.setdefault(a.response_id, []).append(a)
        return out

    def attachment_bytes(self, application_id: uuid.UUID | None = None) -> int:
        """Clarification evidence on disk, across every visit and round (US-085); one application, or
        all of them for the storage gauge (US-089)."""
        stmt = select(func.coalesce(func.sum(ClarificationAttachment.size_bytes), 0))
        if application_id is not None:
            stmt = (
                stmt.join(
                    ClarificationResponse, ClarificationResponse.id == ClarificationAttachment.response_id
                )
                .join(ClarificationRequest, ClarificationRequest.id == ClarificationResponse.request_id)
                .join(ChecklistItem, ChecklistItem.id == ClarificationRequest.item_id)
                .join(Checklist, Checklist.id == ChecklistItem.checklist_id)
                .where(Checklist.application_id == application_id)
            )
        return int(self.db.scalar(stmt) or 0)

    def item(self, item_id: uuid.UUID) -> ChecklistItem | None:
        return self.db.get(ChecklistItem, item_id)

    def checklist(self, checklist_id: uuid.UUID) -> Checklist | None:
        return self.db.get(Checklist, checklist_id)

    def request(self, request_id: uuid.UUID) -> ClarificationRequest | None:
        return self.db.get(ClarificationRequest, request_id)

    def response(self, response_id: uuid.UUID) -> ClarificationResponse | None:
        return self.db.get(ClarificationResponse, response_id)

    def attachment(self, attachment_id: uuid.UUID) -> ClarificationAttachment | None:
        return self.db.get(ClarificationAttachment, attachment_id)

    def delete(self, row: ClarificationAttachment) -> None:
        self.db.delete(row)

    def add(
        self,
        row: Checklist
        | ChecklistItem
        | ClarificationRequest
        | ClarificationResponse
        | ClarificationAttachment,
    ) -> None:
        self.db.add(row)
