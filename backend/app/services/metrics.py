"""Gauges that are read from the database at scrape time (US-077). Counters are updated where the
events happen; only the state of the world needs a query."""

from sqlalchemy.orm import Session

from app.core import metrics
from app.domain.enums import ApplicationStatus
from app.infra.storage import get_storage
from app.repositories.applications import ApplicationRepository
from app.repositories.checklists import ChecklistRepository
from app.repositories.documents import DocumentRepository
from app.services.auth import AuthService


def refresh_gauges(db: Session) -> None:
    counts = ApplicationRepository(db).count_by_status()
    for status in ApplicationStatus:
        metrics.APPLICATIONS.labels(status.value).set(counts.get(status, 0))
    # US-093: accounts signed in right now (not revoked, not idle, token not expired).
    metrics.SESSIONS_ACTIVE.set(AuthService(db).live_count())
    # US-089: what the volume holds, as the database counts it and as the filesystem reports it.
    metrics.STORAGE_BYTES.labels("documents").set(DocumentRepository(db).total_bytes())
    metrics.STORAGE_BYTES.labels("attachments").set(ChecklistRepository(db).attachment_bytes())
    used, total = get_storage().disk_usage()
    metrics.STORAGE_BYTES.labels("volume_used").set(used)
    metrics.STORAGE_BYTES.labels("volume_total").set(total)
