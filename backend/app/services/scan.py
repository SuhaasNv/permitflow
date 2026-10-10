"""The virus scan (US-099, ADR-017): quarantine, the ClamAV verdict, release, and the download gate.

With `SCAN_MODE=off` nothing here runs and every file is served as before. With `enforce`:

- an upload is stored under `quarantine/<key>` with `scan_state = scanning`;
- the scan is the first step of the document's check (inline or in the worker), before any text is read
  or any model is called: a clean file is copied to its normal key and the quarantine copy removed, an
  infected one stays where it is;
- a clarification attachment is scanned inside its upload request (small, three per answer);
- a download is refused unless the state is `clean` (or NULL: stored before the scan existed or with it off);
- when clamd cannot answer, the file is never marked clean. It stays `scanning`; what happens next is the
  administrator's `scanner_fail_mode` (see `retry_scanner_held`).
"""

import enum
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import metrics
from app.core.errors import FileBlocked, FileScanning
from app.core.settings import get_settings
from app.domain.enums import Role
from app.domain.scan import (
    CLEAN,
    INFECTED,
    INFECTED_MESSAGE,
    OFFICER_INFECTED_MESSAGE,
    SCANNING_MESSAGE,
    pdf_active_content,
    released_key,
    servable,
)
from app.infra import notifier
from app.infra.clamd import ScannerError, client_from_settings
from app.infra.storage import FileStorage, get_storage
from app.models import Application, Document, User
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.services.platform_settings import live

logger = logging.getLogger("permitflow.scan")

PDF = "application/pdf"


class ScanOutcome(enum.Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    HELD = "held"  # the scanner could not answer: not clean, not infected
    GONE = "gone"  # the document was deleted or replaced while it was being scanned


@dataclass(frozen=True)
class Verdict:
    infected: bool
    signature: str | None
    active_content: bool
    data: bytes


def enforcing() -> bool:
    return get_settings().scan_mode == "enforce"


def inspect(storage: FileStorage, key: str, content_type: str) -> Verdict:
    """Read the stored file, ask clamd, and look for PDF active content. Raises `ScannerError` when the
    scanner gives no verdict (counted as `error`)."""
    data = b"".join(storage.open(key))
    try:
        result = client_from_settings().scan(data)
    except ScannerError:
        metrics.SCANS.labels("error").inc()
        raise
    metrics.SCANS.labels("infected" if result.infected else "clean").inc()
    return Verdict(result.infected, result.signature, content_type == PDF and pdf_active_content(data), data)


def release(storage: FileStorage, key: str, data: bytes) -> str:
    """Copy a clean file from quarantine to its normal key and remove the quarantine copy; returns the
    normal key. The old copy is removed by `drop_quarantined` once the database points at the new one."""
    new_key = released_key(key)
    if new_key != key:
        storage.put(new_key, iter([data]))
    return new_key


def drop_quarantined(storage: FileStorage, key: str) -> None:
    try:
        storage.delete(key)
    except OSError:
        # An orphan under quarantine/ is harmless (never served); the next sweep of the prefix removes it.
        logger.warning("quarantine_delete_failed")


def alert_infected(reference_no: str, signature: str | None) -> None:
    """Telegram: no file name, no person, no business; only the case reference and the signature."""
    notifier.notify(
        f"PermitFlow: an uploaded file was blocked by the virus scan.\n"
        f"Case: {reference_no}\nSignature: {signature or 'unknown'}"
    )


def alert_scanner_down() -> None:
    notifier.notify("PermitFlow: the virus scanner could not be reached. Uploaded files wait, unopened.")


def scan_document(
    db: Session, doc: Document, app: Application, storage: FileStorage | None = None
) -> ScanOutcome:
    """The first step of a document's check. Commits its own result. A file already `infected` stays so."""
    storage = storage or get_storage()
    if doc.scan_state == INFECTED:
        return ScanOutcome.INFECTED
    key = doc.stored_key
    try:
        verdict = inspect(storage, key, doc.content_type)
    except ScannerError as exc:
        logger.warning("scan_unavailable", extra={"extra_fields": {"error": str(exc)[:200]}})
        return ScanOutcome.HELD
    documents = DocumentRepository(db)
    if verdict.infected:
        documents.record_scan(
            doc.id, key, state=INFECTED, signature=verdict.signature, active_content=verdict.active_content
        )
        AuditRepository(db).record(
            application_id=app.id,
            actor_id=None,
            event_type="document.infected",
            payload={
                "document_id": str(doc.id),
                "document_type": doc.document_type.value,
                "signature": verdict.signature,
                "sha256": doc.sha256[:12],
            },
        )
        db.commit()
        _remember(doc, INFECTED, verdict, key)
        alert_infected(app.reference_no, verdict.signature)
        return ScanOutcome.INFECTED
    new_key = release(storage, key, verdict.data)
    if not documents.record_scan(
        doc.id, key, state=CLEAN, signature=None, active_content=verdict.active_content, new_key=new_key
    ):
        if new_key != key:
            drop_quarantined(storage, new_key)
        db.rollback()
        return ScanOutcome.GONE
    db.commit()
    if new_key != key:
        drop_quarantined(storage, key)
    _remember(doc, CLEAN, verdict, new_key)
    return ScanOutcome.CLEAN


def _remember(doc: Document, state: str, verdict: Verdict, key: str) -> None:
    """Mirror the committed row on the loaded object (the next flush writes the same values)."""
    doc.scan_state = state
    doc.scan_signature = verdict.signature if state == INFECTED else None
    doc.active_content = verdict.active_content
    doc.stored_key = key


def will_retry(attempts: int) -> bool:
    """True when a worker will try this held file again by itself: fail mode `closed`, in worker mode, and
    attempts left. In `open` mode (never in production) the file is held until a person re-runs the check."""
    from app.services.verification import MAX_ATTEMPTS  # noqa: PLC0415 - verification imports this module

    return live().value("scanner_fail_mode") == "closed" and 0 < attempts < MAX_ATTEMPTS


def ensure_servable(scan_state: str | None, user: User) -> None:
    """Refuse a download of a file the scan has not cleared."""
    if servable(scan_state):
        return
    if scan_state == INFECTED:
        officer_side = user.role in (Role.OFFICER, Role.ADMIN)
        raise FileBlocked(OFFICER_INFECTED_MESSAGE if officer_side else INFECTED_MESSAGE)
    raise FileScanning(SCANNING_MESSAGE)
