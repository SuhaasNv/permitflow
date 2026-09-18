import io

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Notification
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import VALID_PREMISES
from tests.journeys import flag_and_request as _flag_and_request


def _resubmitted(client: TestClient, db: Session) -> tuple[str, dict[str, str], dict[str, str]]:
    app_id, op, off = _flag_and_request(client, db)
    premises = dict(VALID_PREMISES)
    premises["address_line_1"] = "10 Jalan Besar #01-21"
    assert (
        client.patch(
            f"/api/v1/applications/{app_id}/sections/premises", headers=op, json=premises
        ).status_code
        == 200
    )
    r = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=op,
        data={"document_type": "floor_plan"},
        files={"file": ("plan2.txt", io.BytesIO(b"Floor plan kitchen preparation area " * 10), "text/plain")},
    )
    assert r.status_code == 201
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 200
    return app_id, op, off


def test_officers_are_notified_on_resubmission(client: TestClient, db: Session) -> None:
    app_id, op, off = _resubmitted(client, db)
    notes = client.get("/api/v1/notifications", headers=off).json()
    assert notes["items"][0]["kind"] == "resubmitted" and notes["items"][0]["application_id"] == app_id
    queue = client.get("/api/v1/officer/applications", headers=off).json()
    item = next(i for i in queue["items"] if i["id"] == app_id)
    assert item["status"] == "pre_site_resubmitted" and item["next_action"] == "Review resubmission"
    assert item["officer_turn"] is True and item["revision_count"] == 2


def test_compare_endpoint_and_changed_markers(client: TestClient, db: Session) -> None:
    app_id, op, off = _resubmitted(client, db)
    r = client.get(f"/api/v1/applications/{app_id}/compare", headers=off, params={"from": 1, "to": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["from_revision"] == 1 and body["to_revision"] == 2
    premises = next(s for s in body["sections"] if s["key"] == "premises")
    assert premises["changed"] and premises["fields"] == [
        {
            "key": "address_line_1",
            "label": "Premises address",
            "old": "10 Jalan Besar #01-12",
            "new": "10 Jalan Besar #01-21",
        }
    ]
    assert not next(s for s in body["sections"] if s["key"] == "business")["changed"]
    docs = {d["type"]: d for d in body["documents"]}
    assert docs["floor_plan"]["change"] == "replaced" and docs["floor_plan"]["new"]["filename"] == "plan2.txt"
    assert docs["business_profile"]["change"] == "unchanged"
    assert body["changed_section_count"] == 1 and body["changed_document_count"] == 1
    # The operator may compare their own revisions; a stranger cannot; unknown revision is 404.
    assert (
        client.get(
            f"/api/v1/applications/{app_id}/compare", headers=op, params={"from": 1, "to": 2}
        ).status_code
        == 200
    )
    make_user(db, "other@example.sg", Role.OPERATOR)
    assert (
        client.get(
            f"/api/v1/applications/{app_id}/compare",
            headers=login(client, "other@example.sg"),
            params={"from": 1, "to": 2},
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/applications/{app_id}/compare", headers=off, params={"from": 1, "to": 9}
        ).status_code
        == 404
    )

    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert case["previous_revision_number"] == 1 and case["changed_sections"] == ["premises"]
    assert case["changed_document_types"] == ["floor_plan"]
    assert case["addressed_unresolved_count"] == 2


def test_resolve_feedback_lifecycle(client: TestClient, db: Session) -> None:
    app_id, op, off = _resubmitted(client, db)
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert all(f["resolution"] == "addressed" and f["addressed_in_revision"] == 2 for f in case["feedback"])
    fid = case["feedback"][0]["id"]
    r = client.post(f"/api/v1/officer/applications/{app_id}/feedback/{fid}/resolve", headers=off)
    assert r.status_code == 200, r.text
    body = r.json()
    resolved = next(f for f in body["feedback"] if f["id"] == fid)
    assert resolved["resolution"] == "resolved" and resolved["resolved_at"] is not None
    assert body["addressed_unresolved_count"] == 1
    assert (
        client.post(f"/api/v1/officer/applications/{app_id}/feedback/{fid}/resolve", headers=off).status_code
        == 409
    )
    assert (
        client.post(f"/api/v1/officer/applications/{app_id}/feedback/{fid}/resolve", headers=op).status_code
        == 403
    )
    assert any(
        e.event_type == "feedback.resolved"
        for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == app_id))
    )
    # Both roles see the state.
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert {f["resolution"] for f in mine["feedback"]} == {"resolved", "addressed"}
    assert db.scalar(select(Notification).where(Notification.kind == "resubmitted")) is not None
