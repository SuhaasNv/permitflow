import io

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Notification
from tests.journeys import VALID_PREMISES, add_feedback, transition, under_review
from tests.journeys import flag_and_request as _flag_and_request


def test_operator_sees_released_feedback_and_only_flagged_targets_are_editable(
    client: TestClient, db: Session
) -> None:
    app_id, op, off = _flag_and_request(client, db)
    view = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert view["status_label"] == "Pending Pre-Site Resubmission" and view["needs_operator_action"] is True
    assert "status" not in view
    labels = sorted(f["target_label"] for f in view["feedback"])
    assert labels == ["Floor plan", "Premises"]
    assert all(f["resolution"] == "open" and f["round"] == 1 for f in view["feedback"])
    assert "author" not in view["feedback"][0]
    editable = {s["key"]: s["editable"] for s in view["sections"]}
    assert editable == {"business": False, "premises": True, "operations": False, "declarations": False}
    slots = {d["type"]: d["editable"] for d in view["document_slots"]}
    assert slots["floor_plan"] is True and slots["business_profile"] is False
    assert view["can_edit"] is True and view["can_submit"] is False
    assert view["resubmit"]["can_resubmit"] is False
    assert sorted(view["resubmit"]["untouched_targets"]) == ["Floor plan", "Premises"]

    # Non-flagged section: 403 with a reason; non-flagged document: 403.
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/business", headers=op, json={"business_name": "X"}
    )
    assert r.status_code == 403 and "did not ask" in r.json()["error"]["message"]
    r = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=op,
        data={"document_type": "business_profile"},
        files={"file": ("p.txt", io.BytesIO(b"new profile text " * 20), "text/plain")},
    )
    assert r.status_code == 403


def test_resubmit_requires_a_change_then_creates_revision_two(client: TestClient, db: Session) -> None:
    app_id, op, off = _flag_and_request(client, db)
    no_change = client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op)
    assert no_change.status_code == 422 and no_change.json()["error"]["details"]["reason"] == "no_change"

    # Change the flagged section only.
    premises = dict(VALID_PREMISES)
    premises["address_line_1"] = "10 Jalan Besar #01-21"
    r = client.patch(f"/api/v1/applications/{app_id}/sections/premises", headers=op, json=premises)
    assert r.status_code == 200
    ready = r.json()["resubmit"]
    assert ready["can_resubmit"] is True and ready["changed_sections"] == ["premises"]
    assert ready["untouched_targets"] == ["Floor plan"]

    r = client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op)
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["status_label"] == "Pre-Site Resubmitted" and view["revision_count"] == 2
    assert view["can_edit"] is False and view["needs_operator_action"] is False
    by_label = {f["target_label"]: f for f in view["feedback"]}
    assert (
        by_label["Premises"]["resolution"] == "addressed"
        and by_label["Premises"]["addressed_in_revision"] == 2
    )
    assert by_label["Floor plan"]["resolution"] == "open"

    events = [e.event_type for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == app_id))]
    assert events.count("revision.submitted") == 2 and "feedback.addressed" in events
    officer_note = db.scalar(select(Notification).where(Notification.kind == "resubmitted"))
    assert officer_note is not None and "1 of 2 items addressed" in officer_note.body

    # Officer sees revision 2 as current with the new address and can start the review again.
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert case["current_revision_number"] == 2 and len(case["revisions"]) == 2
    premises_section = next(s for s in case["sections"] if s["key"] == "premises")
    assert premises_section["data"]["address_line_1"] == "10 Jalan Besar #01-21"
    assert {a["target"] for a in case["actions"]} >= {"under_review"}
    # A second resubmit is refused: the state moved on.
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 409


def test_replacing_a_flagged_document_counts_as_a_change(client: TestClient, db: Session) -> None:
    app_id, op, off = _flag_and_request(client, db)
    r = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=op,
        data={"document_type": "floor_plan"},
        files={
            "file": (
                "plan2.txt",
                io.BytesIO(b"Floor plan kitchen preparation area storage " * 10),
                "text/plain",
            )
        },
    )
    assert r.status_code == 201, r.text
    ready = r.json()["application"]["resubmit"]
    assert ready["can_resubmit"] is True and ready["changed_document_types"] == ["floor_plan"]
    r = client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op)
    assert r.status_code == 200
    by_label = {f["target_label"]: f for f in r.json()["feedback"]}
    assert (
        by_label["Floor plan"]["resolution"] == "addressed" and by_label["Premises"]["resolution"] == "open"
    )


def test_reconfirming_declarations_counts_as_the_change(client: TestClient, db: Session) -> None:
    """Feedback on Declarations can only be answered by confirming again (the values cannot differ)."""
    app_id, op, off, _ = under_review(client, db)
    add_feedback(
        client, off, app_id, target_type="section", section_key="declarations", message="Please re-confirm."
    )
    transition(client, off, app_id, "pending_pre_site_resubmission")
    before = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert before["resubmit"]["can_resubmit"] is False
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/declarations",
        headers=op,
        json={"information_accurate": True, "consent_to_inspection": True},
    )
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["resubmit"]["can_resubmit"] is True and "declarations" in view["resubmit"]["changed_sections"]
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 200
    compare = client.get(f"/api/v1/applications/{app_id}/compare?from=1&to=2", headers=op).json()
    decl = next(s for s in compare["sections"] if s["key"] == "declarations")
    assert decl["changed"] is True and decl["fields"][0]["label"] == "Confirmed on"
