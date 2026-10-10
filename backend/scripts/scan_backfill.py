"""One-off virus scan of every file stored before the scan existed (US-099, ADR-017). Run from backend/:

    uv run python scripts/scan_backfill.py --dry-run         # counts only, changes nothing
    uv run python scripts/scan_backfill.py --limit 20        # try a small batch first
    uv run python scripts/scan_backfill.py                   # every remaining file

Refuses to run unless SCAN_MODE=enforce. The files are the documents and clarification attachments whose
`scan_state` is NULL. Each one is read, scanned by clamd and recorded by the same code a new upload uses:
a clean file gets `scan_state = clean` and `scanned_at` and stays where it is; an infected one moves to
`quarantine/`, gets `scan_state = infected`, an audit event, a Telegram alert and the metric. A NULL file
stays openable until its own verdict lands (it is never set `scanning` first).

Each file commits on its own, so the script can be stopped and run again: it picks up the files that are
still NULL. When clamd cannot answer it stops at once, marks nothing and exits 1. A file that changed or
vanished under the scan, or whose bytes cannot be read, is skipped and counted as held; a person looks at it.
Exit code 0 when it finished (held files are listed), 1 on a scanner outage, 2 for bad configuration.
"""

import argparse
import logging
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.infra.db import session_factory  # noqa: E402
from app.infra.storage import FileStorage, get_storage  # noqa: E402
from app.models import (  # noqa: E402  # noqa: E402
    Application,
    Checklist,
    ChecklistItem,
    ClarificationAttachment,
    ClarificationRequest,
    ClarificationResponse,
    Document,
)
from app.services.scan import ScanOutcome, enforcing, scan_attachment, scan_document  # noqa: E402

logger = logging.getLogger("permitflow.scan_backfill")

BATCH = 50


@dataclass
class Summary:
    dry_run: bool
    documents_null: int = 0
    attachments_null: int = 0
    scanned: int = 0
    clean: int = 0
    infected: int = 0
    held: int = 0
    outage: bool = False
    held_ids: list[str] = field(default_factory=list)


def _null_ids(
    db: Session, model: type[Document] | type[ClarificationAttachment], skip: set[uuid.UUID], n: int
) -> list[uuid.UUID]:
    stmt = select(model.id).where(model.scan_state.is_(None), model.id.not_in(skip))
    return list(db.scalars(stmt.order_by(model.id).limit(n)))


def _count_null(db: Session, model: type[Document] | type[ClarificationAttachment]) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.scan_state.is_(None))) or 0


def _application_of(db: Session, attachment: ClarificationAttachment) -> Application | None:
    return db.scalar(
        select(Application)
        .join(Checklist, Checklist.application_id == Application.id)
        .join(ChecklistItem, ChecklistItem.checklist_id == Checklist.id)
        .join(ClarificationRequest, ClarificationRequest.item_id == ChecklistItem.id)
        .join(ClarificationResponse, ClarificationResponse.request_id == ClarificationRequest.id)
        .where(ClarificationResponse.id == attachment.response_id)
    )


def _scan_document(db: Session, id_: uuid.UUID, storage: FileStorage) -> ScanOutcome:
    doc = db.get(Document, id_)
    app = db.get(Application, doc.application_id) if doc else None
    if doc is None or app is None or doc.scan_state is not None:
        return ScanOutcome.GONE
    return scan_document(db, doc, app, storage)


def _scan_attachment(db: Session, id_: uuid.UUID, storage: FileStorage) -> ScanOutcome:
    row = db.get(ClarificationAttachment, id_)
    app = _application_of(db, row) if row else None
    if row is None or app is None or row.scan_state is not None:
        return ScanOutcome.GONE
    return scan_attachment(db, row, app, storage)


def backfill(storage: FileStorage, *, dry_run: bool = False, limit: int | None = None) -> Summary:
    summary = Summary(dry_run=dry_run)
    with session_factory()() as db:
        summary.documents_null = _count_null(db, Document)
        summary.attachments_null = _count_null(db, ClarificationAttachment)
    if dry_run:
        return summary
    steps: list[
        tuple[
            type[Document] | type[ClarificationAttachment],
            Callable[[Session, uuid.UUID, FileStorage], ScanOutcome],
        ]
    ] = [
        (Document, _scan_document),
        (ClarificationAttachment, _scan_attachment),
    ]
    for model, scan in steps:
        skipped: set[uuid.UUID] = set()  # still NULL after this run touched them: not picked up again
        while limit is None or summary.scanned < limit:
            with session_factory()() as db:
                ids = _null_ids(
                    db, model, skipped, BATCH if limit is None else min(BATCH, limit - summary.scanned)
                )
            if not ids:
                break
            for id_ in ids:
                with session_factory()() as db:
                    try:
                        outcome = scan(db, id_, storage)
                    except OSError as exc:  # the file cannot be read: leave it NULL, openable, for a person
                        logger.warning(
                            "backfill_unreadable", extra={"extra_fields": {"error": str(exc)[:200]}}
                        )
                        outcome = ScanOutcome.GONE
                if outcome is ScanOutcome.HELD:  # clamd gave no answer: stop, nothing was marked
                    summary.outage = True
                    return summary
                summary.scanned += 1
                if outcome is ScanOutcome.CLEAN:
                    summary.clean += 1
                elif outcome is ScanOutcome.INFECTED:
                    summary.infected += 1
                else:
                    summary.held += 1
                    summary.held_ids.append(f"{model.__tablename__}:{id_}")
                    skipped.add(id_)
    return summary


def print_summary(summary: Summary) -> None:
    if summary.dry_run:
        print("scan_backfill: DRY RUN (nothing was changed, nothing was scanned)")
        print(f"  documents with no scan state: {summary.documents_null}")
        print(f"  clarification attachments with no scan state: {summary.attachments_null}")
        return
    print("scan_backfill: EXECUTE")
    print(f"  scanned: {summary.scanned}")
    print(f"  clean: {summary.clean}")
    print(f"  infected: {summary.infected}")
    print(f"  held (changed, vanished or unreadable; skipped): {summary.held}")
    for item in summary.held_ids:
        print(f"    {item}")
    if summary.outage:
        print("  STOPPED: the scanner did not answer; that file was not marked. Run again when it is back.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan every file stored before the virus scan existed.")
    parser.add_argument("--dry-run", action="store_true", help="count the files, change nothing")
    parser.add_argument("--limit", type=int, help="scan at most this many files")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        print("--limit must be at least 1", file=sys.stderr)
        return 2
    if not enforcing():
        print("refusing to run: SCAN_MODE is not enforce", file=sys.stderr)
        return 2
    summary = backfill(get_storage(), dry_run=args.dry_run, limit=args.limit)
    print_summary(summary)
    return 1 if summary.outage else 0


if __name__ == "__main__":
    raise SystemExit(main())
