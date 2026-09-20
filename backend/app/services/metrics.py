"""Gauges that are read from the database at scrape time (US-077). Counters are updated where the
events happen; only the state of the world needs a query."""

from sqlalchemy.orm import Session

from app.core import metrics
from app.domain.enums import ApplicationStatus
from app.repositories.applications import ApplicationRepository
from app.services.auth import AuthService


def refresh_gauges(db: Session) -> None:
    counts = ApplicationRepository(db).count_by_status()
    for status in ApplicationStatus:
        metrics.APPLICATIONS.labels(status.value).set(counts.get(status, 0))
    # US-093: accounts signed in right now (not revoked, not idle, token not expired).
    metrics.SESSIONS_ACTIVE.set(AuthService(db).live_count())
