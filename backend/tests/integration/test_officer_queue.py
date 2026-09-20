import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Application
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import complete_draft as _complete_draft
from tests.journeys import submitted


def test_queue_lists_submitted_applications_only(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    op = login(client, "op@example.sg")
    submitted = _complete_draft(client, op)
    assert client.post(f"/api/v1/applications/{submitted}/submit", headers=op).status_code == 200
    draft = client.post("/api/v1/applications", headers=op).json()["id"]

    r = client.get("/api/v1/officer/applications", headers=login(client, "off@example.sg"))
    assert r.status_code == 200
    body = r.json()
    ids = [i["id"] for i in body["items"]]
    assert submitted in ids and draft not in ids
    item = body["items"][0]
    assert item["status"] == "application_received"
    assert item["status_label"] == "Application Received"
    assert item["next_action"] == "Start review"
    assert item["officer_turn"] is True and item["decided"] is False
    assert item["revision_count"] == 1
    assert item["open_feedback_count"] == 0
    assert item["applicant_name"] == "Op"
    assert item["business_name"] == "Kopi & Kaya Toast House Pte. Ltd."
    assert item["submitted_at"] is not None
    assert item["documents_attention"] + item["documents_checking"] <= 4
    assert body["officer_turn_count"] == 1
    assert body["waiting_on_operator_count"] == 0 and body["decided_count"] == 0


def test_queue_is_officer_only(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "adm@example.sg", Role.ADMIN)
    assert (
        client.get("/api/v1/officer/applications", headers=login(client, "op@example.sg")).status_code == 403
    )
    assert (
        client.get("/api/v1/officer/applications", headers=login(client, "adm@example.sg")).status_code == 403
    )
    assert client.get("/api/v1/officer/applications").status_code == 401


def test_queue_empty(client: TestClient, db: Session) -> None:
    make_user(db, "off@example.sg", Role.OFFICER)
    r = client.get("/api/v1/officer/applications", headers=login(client, "off@example.sg"))
    assert r.status_code == 200
    assert r.json() == {
        "items": [],
        "officer_turn_count": 0,
        "waiting_on_operator_count": 0,
        "decided_count": 0,
    }


def test_queue_shows_the_submitted_form_not_the_working_copy(client: TestClient, db: Session) -> None:
    """During a resubmission round `draft_data` holds the operator's unsubmitted edits; the queue row must
    keep showing the last submitted revision, as the case page does (readiness row 23, fixed US-076)."""
    app_id, _op, off = submitted(client, db)
    app = db.get(Application, uuid.UUID(app_id))
    assert app is not None
    working = dict(app.draft_data)
    working["business"] = {**working["business"], "business_name": "Not Yet Submitted Pte. Ltd."}
    working["premises"] = {**working["premises"], "address_line_1": "1 Unsubmitted Road"}
    app.draft_data = working  # a new dict so the JSONB column is marked dirty
    db.commit()

    item = client.get("/api/v1/officer/applications", headers=off).json()["items"][0]
    assert item["business_name"] == "Kopi & Kaya Toast House Pte. Ltd."
    assert "Unsubmitted" not in (item["premises_summary"] or "")
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    business = next(s for s in case["sections"] if s["key"] == "business")
    assert business["data"]["business_name"] == item["business_name"]
