from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Feedback
from tests.integration.test_officer_case import _submitted


def _under_review(client: TestClient, db: Session) -> tuple[str, dict[str, str], dict[str, str], int]:
    app_id, op, off = _submitted(client, db)
    version = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()["version"]
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "under_review", "expected_version": version},
    )
    assert r.status_code == 200
    return app_id, op, off, r.json()["version"]


def test_feedback_is_locked_until_the_review_starts(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    view = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert view["feedback_editable"] is False and "Start the review" in view["feedback_locked_reason"]
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/feedback",
        headers=off,
        json={"target_type": "section", "section_key": "premises", "message": "Please confirm the address."},
    )
    assert r.status_code == 409


def test_create_list_withdraw_feedback(client: TestClient, db: Session) -> None:
    app_id, op, off, version = _under_review(client, db)
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/feedback",
        headers=off,
        json={
            "target_type": "section",
            "section_key": "premises",
            "message": "Please confirm the premises address.",
            "template_key": "address_mismatch",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["open_feedback_count"] == 1 and body["feedback_editable"] is True
    item = body["feedback"][0]
    assert item["target_label"] == "Premises" and item["resolution"] == "open"
    assert item["raised_in_revision"] == 1 and item["author_name"] == "Off"
    assert item["released_to_operator_at"] is None
    assert body["version"] == version + 1
    # Request resubmission is now enabled; site visit is blocked by the open item.
    actions = {a["target"]: a for a in body["actions"]}
    assert actions["pending_pre_site_resubmission"]["enabled"] is True
    assert actions["site_visit_scheduled"]["enabled"] is False

    r = client.post(
        f"/api/v1/officer/applications/{app_id}/feedback",
        headers=off,
        json={"target_type": "document", "document_type": "floor_plan", "message": "Upload a clearer plan."},
    )
    assert r.status_code == 201 and r.json()["open_feedback_count"] == 2
    doc_item = next(f for f in r.json()["feedback"] if f["target_type"] == "document")
    assert doc_item["target_label"] == "Floor plan"

    w = client.post(f"/api/v1/officer/applications/{app_id}/feedback/{doc_item['id']}/withdraw", headers=off)
    assert w.status_code == 200 and w.json()["open_feedback_count"] == 1
    withdrawn = next(f for f in w.json()["feedback"] if f["id"] == doc_item["id"])
    assert withdrawn["resolution"] == "withdrawn"
    again = client.post(
        f"/api/v1/officer/applications/{app_id}/feedback/{doc_item['id']}/withdraw", headers=off
    )
    assert again.status_code == 409
    events = [e.event_type for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == app_id))]
    assert events.count("feedback.created") == 2 and events.count("feedback.withdrawn") == 1


def test_feedback_validation_and_authorization(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = _under_review(client, db)
    url = f"/api/v1/officer/applications/{app_id}/feedback"
    r = client.post(url, headers=off, json={"target_type": "section", "section_key": "nope", "message": "x"})
    assert r.status_code == 422 and "section_key" in r.json()["error"]["details"]["fields"]
    r = client.post(
        url, headers=off, json={"target_type": "document", "document_type": "nope", "message": "x"}
    )
    assert r.status_code == 422 and "document_type" in r.json()["error"]["details"]["fields"]
    r = client.post(
        url, headers=off, json={"target_type": "section", "section_key": "premises", "message": "  "}
    )
    assert r.status_code == 422 and "message" in r.json()["error"]["details"]["fields"]
    r = client.post(
        url, headers=op, json={"target_type": "section", "section_key": "premises", "message": "x"}
    )
    assert r.status_code == 403
    assert client.get("/api/v1/officer/feedback-templates", headers=op).status_code == 403
    templates = client.get("/api/v1/officer/feedback-templates", headers=off).json()
    assert any(t["key"] == "address_mismatch" and t["section_key"] == "premises" for t in templates)


def test_request_resubmission_releases_and_freezes_feedback(client: TestClient, db: Session) -> None:
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
    assert t.status_code == 200, t.text
    body = t.json()
    assert body["status"] == "pending_pre_site_resubmission"
    assert body["feedback"][0]["released_to_operator_at"] is not None
    assert body["feedback_editable"] is False and "frozen" in body["feedback_locked_reason"]
    released = db.scalar(select(Feedback))
    assert released is not None and released.released_to_operator_at is not None
    assert any(
        e.event_type == "feedback.released"
        for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == app_id))
    )
    # Frozen: no new items, no withdrawals.
    locked = client.post(
        f"/api/v1/officer/applications/{app_id}/feedback",
        headers=off,
        json={"target_type": "section", "section_key": "business", "message": "More."},
    )
    assert locked.status_code == 409
    assert (
        client.post(
            f"/api/v1/officer/applications/{app_id}/feedback/{released.id}/withdraw", headers=off
        ).status_code
        == 409
    )
