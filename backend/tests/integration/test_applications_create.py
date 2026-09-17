from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.models.enums import Role
from tests.factories import login, make_user


def test_create_draft_with_reference_and_audit(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    r = client.post("/api/v1/applications", headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reference_no"].startswith("PF-")
    assert body["status_label"] == "Draft"
    assert "status" not in body  # internal code never reaches operators
    assert body["can_submit"] is False
    assert [s["key"] for s in body["sections"]] == ["business", "premises", "operations", "declarations"]
    assert all(s["editable"] for s in body["sections"])
    assert len(body["document_slots"]) == 4
    assert body["completeness"]["percent"] == 0
    events = list(db.scalars(select(AuditEvent)))
    assert [e.event_type for e in events] == ["application.created"]


def test_list_only_own_and_get_other_is_404(client: TestClient, db: Session) -> None:
    make_user(db, "a@example.sg", Role.OPERATOR)
    make_user(db, "b@example.sg", Role.OPERATOR)
    ha, hb = login(client, "a@example.sg"), login(client, "b@example.sg")
    created = client.post("/api/v1/applications", headers=ha).json()
    client.post("/api/v1/applications", headers=hb)
    assert [a["id"] for a in client.get("/api/v1/applications", headers=ha).json()] == [created["id"]]
    r = client.get(f"/api/v1/applications/{created['id']}", headers=hb)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    assert client.get(f"/api/v1/applications/{created['id']}", headers=ha).status_code == 200


def test_officer_cannot_create_or_list_operator_applications(client: TestClient, db: Session) -> None:
    make_user(db, "off@example.sg", Role.OFFICER)
    h = login(client, "off@example.sg")
    assert client.post("/api/v1/applications", headers=h).status_code == 403
    assert client.get("/api/v1/applications", headers=h).status_code == 403
    assert client.post("/api/v1/applications").status_code == 401


def test_reference_numbers_are_unique_and_sequential(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    refs = [client.post("/api/v1/applications", headers=h).json()["reference_no"] for _ in range(3)]
    assert len(set(refs)) == 3
    nums = [int(r.split("-")[-1]) for r in refs]
    assert nums == sorted(nums)


def test_form_schema_requires_auth_and_lists_sections(client: TestClient, db: Session) -> None:
    assert client.get("/api/v1/form-schema").status_code == 401
    make_user(db, "op@example.sg", Role.OPERATOR)
    r = client.get("/api/v1/form-schema", headers=login(client, "op@example.sg"))
    assert r.status_code == 200
    assert [s["key"] for s in r.json()["sections"]] == ["business", "premises", "operations", "declarations"]
    assert len(r.json()["required_documents"]) == 4
