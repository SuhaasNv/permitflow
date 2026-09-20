import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SiteVisit, SiteVisitProposal


class SiteVisitRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def current_for(self, application_id: uuid.UUID) -> SiteVisit | None:
        """The latest visit of the application (highest visit number), or None before any is proposed."""
        stmt = (
            select(SiteVisit)
            .where(SiteVisit.application_id == application_id)
            .order_by(SiteVisit.visit_no.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def current_for_many(self, application_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, SiteVisit]:
        """The latest visit per application, for the queue and the operator list, in one query."""
        ids = list(application_ids)
        if not ids:
            return {}
        stmt = (
            select(SiteVisit)
            .where(SiteVisit.application_id.in_(ids))
            .order_by(SiteVisit.application_id, SiteVisit.visit_no.desc())
        )
        out: dict[uuid.UUID, SiteVisit] = {}
        for visit in self.db.scalars(stmt):
            out.setdefault(visit.application_id, visit)
        return out

    def proposals_for(self, site_visit_id: uuid.UUID) -> list[SiteVisitProposal]:
        stmt = (
            select(SiteVisitProposal)
            .where(SiteVisitProposal.site_visit_id == site_visit_id)
            .order_by(SiteVisitProposal.round_no.asc(), SiteVisitProposal.created_at.asc())
        )
        return list(self.db.scalars(stmt))

    def add(self, row: SiteVisit | SiteVisitProposal) -> None:
        self.db.add(row)
