import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Checklist, ChecklistItem


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

    def add(self, row: Checklist | ChecklistItem) -> None:
        self.db.add(row)
