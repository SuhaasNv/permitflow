import io

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, ApplicationRevision, AuditEvent, Notification
from app.models.enums import ApplicationStatus, Role
from tests.factories import login, make_user
from tests.unit.test_form_schema import VALID_BUSINESS, VALID_DECLARATIONS, VALID_OPERATIONS, VALID_PREMISES

_SENTENCE = (
    "Tenancy agreement between landlord and tenant. Business profile ACRA UEN. Floor plan kitchen. "
    "Food hygiene certificate. "
)
TXT = (_SENTENCE * 3).encode()


def _complete_draft(client: TestClient, h: dict[str, str]) -> str:
    app_id = str(client.post("/api/v1/applications", headers=h).json()["id"])
    for key, data in [
        ("business", VALID_BUSINESS),
        ("premises", VALID_PREMISES),
        ("operations", VALID_OPERATIONS),
        ("declarations", VALID_DECLARATIONS),
    ]:
        assert (
            client.patch(f"/api/v1/applications/{app_id}/sections/{key}", headers=h, json=data).status_code
            == 200
        )
    for dtype in ("business_profile", "floor_plan", "tenancy_agreement", "food_hygiene_certificate"):
        r = client.post(
            f"/api/v1/applications/{app_id}/documents",
            headers=h,
            data={"document_type": dtype},
            files={"file": (f"{dtype}.txt", io.BytesIO(TXT), "text/plain")},
        )
        assert r.status_code == 201
    return app_id


def test_submit_creates_revision_status_audit_and_notifications(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "off1@example.sg", Role.OFFICER)
    make_user(db, "off2@example.sg", Role.OFFICER)
    make_user(db, "old@example.sg", Role.OFFICER, active=False)
    h = login(client, "op@example.sg")
    app_id = _complete_draft(client, h)
    before = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    assert before["can_submit"] is True and before["completeness"]["percent"] == 100

    r = client.post(f"/api/v1/applications/{app_id}/submit", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status_label"] == "Submitted"
    assert body["can_edit"] is False and body["can_submit"] is False
    assert all(not s["editable"] for s in body["sections"]) and all(
        not d["editable"] for d in body["document_slots"]
    )
    assert body["revision_count"] == 1

    rev = db.scalar(select(ApplicationRevision))
    assert (
        rev is not None
        and rev.revision_number == 1
        and rev.form_data["business"] == VALID_BUSINESS
        and len(rev.document_ids) == 4
    )
    app = db.get(Application, rev.application_id)
    assert (
        app is not None
        and app.status == ApplicationStatus.APPLICATION_RECEIVED
        and app.current_revision_id == rev.id
    )
    events = [e.event_type for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == app.id))]
    assert events[-2:] == ["revision.submitted", "status.changed"]
    notes = list(db.scalars(select(Notification)))
    assert len(notes) == 2 and {str(n.kind) for n in notes} == {"submitted"}

    # locked after submission
    assert (
        client.patch(
            f"/api/v1/applications/{app_id}/sections/business", headers=h, json=VALID_BUSINESS
        ).status_code
        == 403
    )
    assert client.post(f"/api/v1/applications/{app_id}/submit", headers=h).status_code == 409


def test_submit_incomplete_is_422_with_gaps_and_nothing_persisted(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = str(client.post("/api/v1/applications", headers=h).json()["id"])
    client.patch(f"/api/v1/applications/{app_id}/sections/business", headers=h, json=VALID_BUSINESS)
    r = client.post(f"/api/v1/applications/{app_id}/submit", headers=h)
    assert r.status_code == 422
    missing = r.json()["error"]["details"]["missing"]
    assert (
        "Section: Premises" in missing
        and "Document: Floor plan" in missing
        and "Section: Business details" not in missing
    )
    assert db.scalar(select(ApplicationRevision)) is None
    assert client.get(f"/api/v1/applications/{app_id}", headers=h).json()["status_label"] == "Draft"


def test_submit_wrong_owner_and_role(client: TestClient, db: Session) -> None:
    make_user(db, "a@example.sg", Role.OPERATOR)
    make_user(db, "b@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    ha, hb, ho = login(client, "a@example.sg"), login(client, "b@example.sg"), login(client, "off@example.sg")
    app_id = _complete_draft(client, ha)
    assert client.post(f"/api/v1/applications/{app_id}/submit", headers=hb).status_code == 404
    assert client.post(f"/api/v1/applications/{app_id}/submit", headers=ho).status_code == 403
