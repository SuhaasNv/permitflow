"""Which site visit the case views are about (UAT run 5, F15 to F18).

A case can have several visits: after Route to approval an officer may return it to review and schedule a
second one. The views read one visit, the *active* one, and list the others as earlier visits:

- while the case is back in the pre-visit review (Application Received to Pre-Site Resubmitted) no visit
  is active: the last one is finished history, and the review panels (feedback) are what the officer uses;
- otherwise the latest visit is active: the one being arranged, recorded or clarified, and after the
  decision the one that led to it.

The guards keep their own reading of the current visit (ChecklistService, SiteVisitService); this module
only decides what a page shows."""

from sqlalchemy.orm import Session

from app.domain.enums import ApplicationStatus
from app.models import Application
from app.repositories.checklists import ChecklistRepository
from app.repositories.site_visits import SiteVisitRepository

REVIEW_STATES = frozenset(
    {
        ApplicationStatus.DRAFT,
        ApplicationStatus.APPLICATION_RECEIVED,
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION,
        ApplicationStatus.PRE_SITE_RESUBMITTED,
    }
)


def active_visit_no(db: Session, app: Application) -> int | None:
    """The visit the case is about now, or None while it is back in the pre-visit review."""
    if app.status in REVIEW_STATES:
        return None
    visit = SiteVisitRepository(db).current_for(app.id)
    if visit is not None:
        return visit.visit_no
    # A case scheduled through the API before a date was proposed: its checklist carries the number.
    latest = ChecklistRepository(db).current_for(app.id)
    return latest.visit_no if latest is not None else None


def earlier_visit_nos(db: Session, app: Application) -> list[int]:
    """Every visit on record other than the active one, latest first."""
    active = active_visit_no(db, app)
    visits = {v.visit_no for v in SiteVisitRepository(db).list_for(app.id)}
    visits |= {c.visit_no for c in ChecklistRepository(db).list_for(app.id)}
    return sorted((n for n in visits if n != active), reverse=True)
