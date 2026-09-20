"""The post-site clarification rounds (US-064 to US-066). This module serves the operator's view
(US-064): the items with a released request, in operator words, and the block the application view
carries. Responses, attachments and the send arrive with US-065; the officer's decisions with US-066."""

import uuid

from sqlalchemy.orm import Session

from app.domain.checklist_schema import ITEM_BY_KEY
from app.domain.enums import ApplicationStatus, ClarificationStatus
from app.models import Application, ChecklistItem, ClarificationRequest, User
from app.repositories.applications import ApplicationRepository
from app.repositories.checklists import ChecklistRepository
from app.schemas.clarification import (
    ClarificationBlock,
    ClarificationItemOut,
    ClarificationOperatorView,
    ClarificationRequestOut,
)

OPERATOR_TURN_STATES = (
    ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION,
    ApplicationStatus.PENDING_POST_SITE_RESUBMISSION,
)

OPERATOR_WORDS: dict[ClarificationStatus, str] = {
    ClarificationStatus.OPEN: "Waiting for your response",
    ClarificationStatus.ANSWERED: "Sent",
    ClarificationStatus.RESOLVED: "Clarified",
    ClarificationStatus.WITHDRAWN: "No longer needed",
    ClarificationStatus.NONE: "",
}


class ClarificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.checklists = ChecklistRepository(db)

    def operator_view(self, operator: User, application_id: uuid.UUID) -> ClarificationOperatorView:
        app = self.applications.get_for(operator, application_id)
        return self.build(app)

    def build(self, app: Application) -> ClarificationOperatorView:
        checklist = self.checklists.current_for(app.id)
        if checklist is None:
            return ClarificationOperatorView(
                application_id=app.id,
                visit_no=None,
                items=[],
                open_count=0,
                answered_count=0,
                resolved_count=0,
                round=0,
                can_respond=False,
                can_send=False,
            )
        items = self.checklists.items_for(checklist.id)
        requests = self.checklists.requests_for_items([i.id for i in items])
        by_item: dict[uuid.UUID, list[ClarificationRequest]] = {}
        for q in requests:
            by_item.setdefault(q.item_id, []).append(q)
        out: list[ClarificationItemOut] = []
        for item in items:
            released = [
                q for q in by_item.get(item.id, []) if q.released_at is not None and q.withdrawn_at is None
            ]
            if not released:
                continue  # unflagged, or only unreleased questions: not the operator's business yet
            out.append(self._item_out(app, item, released))
        open_count = sum(1 for i in out if i.status == OPERATOR_WORDS[ClarificationStatus.OPEN])
        answered = sum(1 for i in out if i.status == OPERATOR_WORDS[ClarificationStatus.ANSWERED])
        resolved = sum(1 for i in out if i.status == OPERATOR_WORDS[ClarificationStatus.RESOLVED])
        operator_turn = app.status in OPERATOR_TURN_STATES
        return ClarificationOperatorView(
            application_id=app.id,
            visit_no=checklist.visit_no,
            items=out,
            open_count=open_count,
            answered_count=answered,
            resolved_count=resolved,
            round=max((i.round_no for i in out), default=0),
            can_respond=operator_turn and open_count > 0,
            can_send=False,  # US-065: true once every open item carries a response
        )

    def block(self, app: Application) -> ClarificationBlock | None:
        """The application view's block; None before any item was released to the operator."""
        view = self.build(app)
        if not view.items:
            return None
        return ClarificationBlock(
            can_respond=view.can_respond,
            open_count=view.open_count,
            answered_count=view.answered_count,
            round=view.round,
        )

    def open_counts(self, app_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Items waiting for the operator per application (the list and the dashboard)."""
        checklists = self.checklists.current_for_many(app_ids)
        out: dict[uuid.UUID, int] = {}
        for app_id, checklist in checklists.items():
            items = self.checklists.items_for(checklist.id)
            out[app_id] = sum(1 for i in items if i.clarification_status == ClarificationStatus.OPEN)
        return out

    def _item_out(
        self, app: Application, item: ChecklistItem, released: list[ClarificationRequest]
    ) -> ClarificationItemOut:
        current_round = max(q.round_no for q in released)
        definition = ITEM_BY_KEY.get(item.item_key)
        status = item.clarification_status
        return ClarificationItemOut(
            item_id=item.id,
            key=item.item_key,
            title=definition.title if definition else item.item_key,
            guidance=definition.guidance if definition else "",
            status=OPERATOR_WORDS.get(status, ""),
            round_no=current_round,
            requests=[
                ClarificationRequestOut(
                    id=q.id,
                    round_no=q.round_no,
                    message=q.message,
                    released_at=q.released_at,  # type: ignore[arg-type]
                )
                for q in released
            ],
            responses=[],  # US-065
            can_respond=app.status in OPERATOR_TURN_STATES and status == ClarificationStatus.OPEN,
        )
