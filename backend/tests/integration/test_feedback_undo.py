"""US-039: resolve only what the operator saw; undo a withdraw or resolve within the grace window."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Feedback
from app.models.enums import Role
from app.services.feedback import UNDO_WINDOW
from tests.factories import login, make_user
from tests.journeys import VALID_PREMISES, add_feedback, flag_and_request, under_review


def _url(app_id: str, fid: str, action: str) -> str:
    return f"/api/v1/officer/applications/{app_id}/feedback/{fid}/{action}"


def test_unreleased_item_cannot_be_resolved_only_withdrawn(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    item = add_feedback(
        client, off, app_id, target_type="section", section_key="premises", message="Draft item."
    )
    fid = item["feedback"][0]["id"]
    r = client.post(_url(app_id, fid, "resolve"), headers=off)
    assert r.status_code == 409 and "never sent" in r.json()["error"]["message"]
    assert client.post(_url(app_id, fid, "withdraw"), headers=off).status_code == 200


def test_withdraw_then_undo_within_window(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    fid = add_feedback(client, off, app_id, target_type="section", section_key="premises", message="Oops.")[
        "feedback"
    ][0]["id"]
    body = client.post(_url(app_id, fid, "withdraw"), headers=off).json()
    item = next(f for f in body["feedback"] if f["id"] == fid)
    assert item["resolution"] == "withdrawn" and item["can_undo"] is True
    body = client.post(_url(app_id, fid, "restore"), headers=off).json()
    item = next(f for f in body["feedback"] if f["id"] == fid)
    assert item["resolution"] == "open" and item["can_undo"] is False
    assert item["resolved_at"] is None and body["open_feedback_count"] == 1
    events = db.scalars(select(AuditEvent).where(AuditEvent.application_id == uuid.UUID(app_id))).all()
    restored = [e for e in events if e.event_type == "feedback.restored"]
    assert len(restored) == 1 and restored[0].payload["from"] == "withdrawn"
    assert restored[0].payload["to"] == "open" and restored[0].actor_id is not None
    trail = client.get(f"/api/v1/officer/applications/{app_id}/audit", headers=off).json()["events"]
    assert any("restored to open (undo)" in e["summary"] for e in trail)
    # a second undo has nothing to undo
    assert client.post(_url(app_id, fid, "restore"), headers=off).status_code == 409


def test_resolve_then_undo_restores_addressed(client: TestClient, db: Session) -> None:
    app_id, op, off = flag_and_request(client, db)
    # operator changes the flagged premises section and resubmits, so the item becomes addressed
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises",
        headers=op,
        json={**VALID_PREMISES, "address_line_1": "10 Jalan Besar #01-21"},
    )
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 200
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    fid = next(f["id"] for f in case["feedback"] if f["resolution"] == "addressed")
    body = client.post(_url(app_id, fid, "resolve"), headers=off).json()
    assert next(f for f in body["feedback"] if f["id"] == fid)["can_undo"] is True
    body = client.post(_url(app_id, fid, "restore"), headers=off).json()
    item = next(f for f in body["feedback"] if f["id"] == fid)
    assert item["resolution"] == "addressed" and item["addressed_in_revision"] == 2


def test_undo_refused_after_window_by_another_officer_and_when_state_moved(
    client: TestClient, db: Session
) -> None:
    app_id, op, off, version = under_review(client, db)
    fid = add_feedback(client, off, app_id, target_type="section", section_key="premises", message="Oops.")[
        "feedback"
    ][0]["id"]
    assert client.post(_url(app_id, fid, "withdraw"), headers=off).status_code == 200

    # another officer cannot undo a colleague's decision
    make_user(db, "off2@example.sg", Role.OFFICER)
    off2 = login(client, "off2@example.sg")
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off2).json()
    assert next(f for f in case["feedback"] if f["id"] == fid)["can_undo"] is False
    assert client.post(_url(app_id, fid, "restore"), headers=off2).status_code == 409
    assert client.post(_url(app_id, fid, "restore"), headers=op).status_code == 403

    # the window closes
    row = db.get(Feedback, uuid.UUID(fid))
    assert row is not None
    row.resolved_at = datetime.now(UTC) - UNDO_WINDOW - timedelta(seconds=1)
    db.commit()
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert next(f for f in case["feedback"] if f["id"] == fid)["can_undo"] is False
    assert client.post(_url(app_id, fid, "restore"), headers=off).status_code == 409

    # a fresh withdraw, then the state moves on: undo is refused
    fid2 = add_feedback(
        client, off, app_id, target_type="section", section_key="operations", message="Keep."
    )["feedback"][-1]["id"]
    fid3 = add_feedback(
        client, off, app_id, target_type="document", document_type="floor_plan", message="Gone."
    )["feedback"][-1]["id"]
    assert client.post(_url(app_id, fid3, "withdraw"), headers=off).status_code == 200
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "pending_pre_site_resubmission", "expected_version": case["version"]},
    )
    assert r.status_code == 200, r.text
    assert client.post(_url(app_id, fid3, "restore"), headers=off).status_code == 409
    assert fid2 != fid3
