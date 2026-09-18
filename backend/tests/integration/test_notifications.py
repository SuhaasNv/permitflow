from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import Role
from tests.factories import login, make_user
from tests.integration.test_feedback import _under_review


def test_operator_lists_and_reads_own_notifications(client: TestClient, db: Session) -> None:
    app_id, op, off, version = _under_review(client, db)
    r = client.get("/api/v1/notifications", headers=op)
    assert r.status_code == 200
    body = r.json()
    assert body["unread_count"] == 1
    item = body["items"][0]
    assert item["kind"] == "status_changed" and "Under Review" in item["title"]
    assert item["application_id"] == app_id and item["read_at"] is None
    # Operator label only, never the internal code.
    assert "under_review" not in item["title"] and "under_review" not in item["body"]

    read = client.post(f"/api/v1/notifications/{item['id']}/read", headers=op)
    assert read.status_code == 200 and read.json()["read_at"] is not None
    assert client.get("/api/v1/notifications", headers=op).json()["unread_count"] == 0

    # The officer got the submission notification and cannot read the operator's.
    mine = client.get("/api/v1/notifications", headers=off).json()
    assert mine["unread_count"] == 1 and mine["items"][0]["kind"] == "submitted"
    assert client.post(f"/api/v1/notifications/{item['id']}/read", headers=off).status_code == 404
    assert client.get("/api/v1/notifications").status_code == 401


def test_request_resubmission_notifies_operator_and_flags_action(client: TestClient, db: Session) -> None:
    app_id, op, off, version = _under_review(client, db)
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/feedback",
        headers=off,
        json={"target_type": "section", "section_key": "premises", "message": "Confirm the address."},
    )
    version = r.json()["version"]
    t = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "pending_pre_site_resubmission", "expected_version": version},
    )
    assert t.status_code == 200
    notes = client.get("/api/v1/notifications", headers=op).json()
    assert notes["unread_count"] == 2
    assert "Pending Pre-Site Resubmission" in notes["items"][0]["title"]
    summary = client.get("/api/v1/applications", headers=op).json()[0]
    assert summary["needs_operator_action"] is True and summary["status_tone"] == "warning"
    view = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert view["needs_operator_action"] is True
    all_read = client.post("/api/v1/notifications/read-all", headers=op)
    assert all_read.status_code == 200 and all_read.json()["unread_count"] == 0


def test_notification_is_not_sent_for_drafts(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    client.post("/api/v1/applications", headers=op)
    summary = client.get("/api/v1/applications", headers=op).json()[0]
    assert summary["needs_operator_action"] is False
    assert client.get("/api/v1/notifications", headers=op).json() == {"items": [], "unread_count": 0}
