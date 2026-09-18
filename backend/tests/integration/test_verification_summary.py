"""The officer's Document checks card and the queue's Document checks column read the same facts."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, VerificationRun
from app.models.enums import VerificationStatus
from tests.journeys import submitted as _submitted


def _set_latest_statuses(db: Session, app_id: str, statuses: list[VerificationStatus]) -> None:
    docs = db.scalars(
        select(Document).where(Document.application_id == app_id, Document.is_current.is_(True))
    ).all()
    assert len(docs) == len(statuses)
    for doc, status in zip(sorted(docs, key=lambda d: d.document_type.value), statuses, strict=True):
        run = db.scalars(
            select(VerificationRun)
            .where(VerificationRun.document_id == doc.id)
            .order_by(VerificationRun.created_at.desc())
        ).first()
        assert run is not None
        run.status = status
    db.commit()


def _queue_item(client: TestClient, off: dict[str, str], app_id: str) -> dict[str, int]:
    items = client.get("/api/v1/officer/applications", headers=off).json()["items"]
    return next(i for i in items if i["id"] == app_id)


def test_summary_buckets_and_queue_agree_on_a_mixed_case(client: TestClient, db: Session) -> None:
    app_id, _op, off = _submitted(client, db)
    _set_latest_statuses(
        db,
        app_id,
        [
            VerificationStatus.ISSUES_FOUND,
            VerificationStatus.NEEDS_REVIEW,
            VerificationStatus.UNREADABLE,
            VerificationStatus.PENDING,
        ],
    )

    s = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()["verification_summary"]
    assert s == {
        "total": 4,
        "verified": 0,
        "issues_found": 1,
        "needs_review": 1,
        "checking": 1,
        "other": 1,
    }
    assert s["verified"] + s["issues_found"] + s["needs_review"] + s["checking"] + s["other"] == s["total"]

    item = _queue_item(client, off, app_id)
    # Everything that is not clean and not still running is "to check" in the queue: the unreadable
    # document counts, because the operator was told an officer would look at it.
    assert item["documents_attention"] == s["issues_found"] + s["needs_review"] + s["other"] == 3
    assert item["documents_checking"] == s["checking"] == 1


def test_summary_all_verified_reads_clear(client: TestClient, db: Session) -> None:
    app_id, _op, off = _submitted(client, db)
    _set_latest_statuses(db, app_id, [VerificationStatus.VERIFIED] * 4)
    s = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()["verification_summary"]
    assert s["verified"] == 4 and s["other"] == 0 and s["checking"] == 0
    item = _queue_item(client, off, app_id)
    assert item["documents_attention"] == 0 and item["documents_checking"] == 0
