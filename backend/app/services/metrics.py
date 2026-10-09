"""Gauges that are read from the database at scrape time (US-077). Counters are updated where the
events happen; only the state of the world needs a query."""

from sqlalchemy.orm import Session

from app.core import metrics
from app.core.settings import get_settings
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
    documents = DocumentRepository(db).total_bytes()
    attachments = ChecklistRepository(db).attachment_bytes()
    metrics.STORAGE_BYTES.labels("documents").set(documents)
    metrics.STORAGE_BYTES.labels("attachments").set(attachments)
    # US-098: stored bytes against the platform ceiling, on either backend. No `limit` series without a
    # ceiling, so the 80 % alert has nothing to divide by.
    metrics.STORAGE_BYTES.labels("stored").set(documents + attachments)
    if (cap := get_settings().storage_total_max_bytes) > 0:
        metrics.STORAGE_BYTES.labels("limit").set(cap)
    used, total = get_storage().disk_usage()
    metrics.STORAGE_BYTES.labels("volume_used").set(used)
    metrics.STORAGE_BYTES.labels("volume_total").set(total)
