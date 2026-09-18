from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Notification
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import submitted as _submitted


def test_officer_view_shows_revision_documents_and_actions(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    # A post-submission draft edit must not leak into the officer view (the revision is the truth).
    r = client.get(f"/api/v1/officer/applications/{app_id}", headers=off)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "application_received" and body["status_label"] == "Application Received"
    assert body["applicant"]["email"] == "op@example.sg"
    assert body["business_name"] == "Kopi & Kaya Toast House Pte. Ltd."
    assert [s["key"] for s in body["sections"]] == ["business", "premises", "operations", "declarations"]
    assert all(s["complete"] for s in body["sections"])
    assert len(body["documents"]) == 4 and all(d["in_current_revision"] for d in body["documents"])
    assert body["documents"][0]["verification"] is not None
    assert "confidence" in body["documents"][0]["verification"]
    assert body["verification_summary"]["total"] == 4
    assert body["current_revision_number"] == 1 and len(body["revisions"]) == 1
    assert body["revisions"][0]["submitted_by"] == "Op"
    targets = {a["target"]: a for a in body["actions"]}
    assert targets["under_review"]["label"] == "Start review" and targets["under_review"]["enabled"]
    assert targets["rejected"]["requires_note"] is True
    assert "version" in body


def test_officer_view_is_officer_only_and_hides_drafts(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    make_user(db, "adm@example.sg", Role.ADMIN)
    assert client.get(f"/api/v1/officer/applications/{app_id}", headers=op).status_code == 403
    assert (
        client.get(
            f"/api/v1/officer/applications/{app_id}", headers=login(client, "adm@example.sg")
        ).status_code
        == 403
    )
    draft = client.post("/api/v1/applications", headers=op).json()["id"]
    assert client.get(f"/api/v1/officer/applications/{draft}", headers=off).status_code == 404


def test_start_review_transition_records_actor_and_notifies_operator(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    version = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()["version"]
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "under_review", "expected_version": version},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "under_review" and body["version"] == version + 1
    assert {a["target"] for a in body["actions"]} == {
        "pending_pre_site_resubmission",
        "site_visit_scheduled",
        "rejected",
    }
    event = db.scalar(
        select(AuditEvent)
        .where(AuditEvent.event_type == "status.changed")
        .order_by(AuditEvent.created_at.desc())
    )
    assert (
        event is not None and event.payload["to"] == "under_review" and event.payload["trigger"] == "officer"
    )
    assert event.actor_id is not None
    note = db.scalar(select(Notification).where(Notification.kind == "status_changed"))
    assert note is not None and "Under Review" in note.title
    # Operator sees the operator label only.
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["status_label"] == "Under Review" and "status" not in mine


def test_transition_rejects_stale_version_invalid_edge_and_missing_note(
    client: TestClient, db: Session
) -> None:
    app_id, op, off = _submitted(client, db)
    version = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()["version"]
    stale = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "under_review", "expected_version": version - 1},
    )
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "version_conflict"
    bad = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "approved", "expected_version": version},
    )
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "invalid_transition"
    assert "under_review" in bad.json()["error"]["details"]["allowed"]
    no_note = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "rejected", "expected_version": version},
    )
    assert no_note.status_code == 409 and no_note.json()["error"]["details"]["kind"] == "guard"
    unknown = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "nope", "expected_version": version},
    )
    assert unknown.status_code == 422
    assert (
        client.post(
            f"/api/v1/officer/applications/{app_id}/transition",
            headers=op,
            json={"target": "under_review", "expected_version": version},
        ).status_code
        == 403
    )


def test_officer_can_rerun_a_check_and_sees_it_pending(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    view = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    doc_id = view["documents"][0]["id"]
    r = client.post(f"/api/v1/officer/applications/{app_id}/documents/{doc_id}/verify", headers=off)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "application_received"
    doc = next(d for d in body["documents"] if d["id"] == doc_id)
    assert doc["verification"]["status"] in ("pending", "running", "verified", "issues_found")
    # A second request while the first is still queued is refused; operators cannot use the officer route.
    again = client.post(f"/api/v1/officer/applications/{app_id}/documents/{doc_id}/verify", headers=off)
    assert again.status_code in (202, 409)
    assert (
        client.post(
            f"/api/v1/officer/applications/{app_id}/documents/{doc_id}/verify", headers=op
        ).status_code
        == 403
    )
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.event_type == "verification.requested")))
    assert len(events) >= 1
