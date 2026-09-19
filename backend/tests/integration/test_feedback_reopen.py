"""US-049: an addressed item can be marked not fixed, reopening it for the next round with the same text."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent
from tests.journeys import VALID_PREMISES, flag_and_request, transition


def _url(app_id: str, fid: str, action: str) -> str:
    return f"/api/v1/officer/applications/{app_id}/feedback/{fid}/{action}"


def _resubmitted(client: TestClient, db: Session) -> tuple[str, dict[str, str], dict[str, str], str]:
    """Round 1: premises flagged, operator changes it, resubmits; the item is addressed."""
    app_id, op, off = flag_and_request(client, db)
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises",
        headers=op,
        json={**VALID_PREMISES, "address_line_1": "10 Jalan Besar #01-21"},
    )
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 200
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    fid = next(f["id"] for f in case["feedback"] if f["section_key"] == "premises")
    assert next(f for f in case["feedback"] if f["id"] == fid)["resolution"] == "addressed"
    return app_id, op, off, fid


def test_not_fixed_reopens_the_item_and_a_second_round_follows(client: TestClient, db: Session) -> None:
    app_id, op, off, fid = _resubmitted(client, db)
    # only while under review
    assert client.post(_url(app_id, fid, "reopen"), headers=off).status_code == 409
    transition(client, off, app_id, "under_review")

    body = client.post(_url(app_id, fid, "reopen"), headers=off).json()
    item = next(f for f in body["feedback"] if f["id"] == fid)
    assert item["resolution"] == "open" and item["released_to_operator_at"] is None
    assert item["message"] == "Confirm the address." and item["can_undo"] is True
    assert body["open_feedback_count"] >= 1
    assert any(a["target"] == "pending_pre_site_resubmission" and a["enabled"] for a in body["actions"])

    # the operator does not see the draft until the next round is requested
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert all(f["id"] != fid or f["resolution"] != "open" for f in mine["feedback"])

    transition(client, off, app_id, "pending_pre_site_resubmission")
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    again = next(f for f in mine["feedback"] if f["id"] == fid)
    assert again["resolution"] == "open" and again["message"] == "Confirm the address."
    assert "premises" in mine["resubmit"]["untouched_targets"] or mine["resubmit"]["can_resubmit"] is False

    events = db.scalars(select(AuditEvent).where(AuditEvent.application_id == uuid.UUID(app_id))).all()
    assert sum(1 for e in events if e.event_type == "feedback.reopened") == 1
    assert sum(1 for e in events if e.event_type == "feedback.released") == 2
    trail = client.get(f"/api/v1/officer/applications/{app_id}/audit", headers=off).json()["events"]
    assert any("not fixed" in e["summary"] for e in trail)


def test_not_fixed_can_be_undone_and_rejects_other_states(client: TestClient, db: Session) -> None:
    app_id, op, off, fid = _resubmitted(client, db)
    transition(client, off, app_id, "under_review")
    assert client.post(_url(app_id, fid, "reopen"), headers=off).status_code == 200
    body = client.post(_url(app_id, fid, "restore"), headers=off).json()
    item = next(f for f in body["feedback"] if f["id"] == fid)
    assert item["resolution"] == "addressed" and item["released_to_operator_at"] is not None
    assert item["addressed_in_revision"] == 2 and item["can_undo"] is False
    # an open item that was never addressed cannot be "not fixed"
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    other = next(f["id"] for f in case["feedback"] if f["id"] != fid)
    assert client.post(_url(app_id, other, "reopen"), headers=off).status_code == 409
    assert client.post(_url(app_id, fid, "reopen"), headers=op).status_code == 403
