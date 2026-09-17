from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Application
from app.models.enums import ApplicationStatus, Role
from tests.factories import login, make_user
from tests.unit.test_form_schema import VALID_BUSINESS, VALID_PREMISES


def _draft(client: TestClient, headers: dict[str, str]) -> str:
    return str(client.post("/api/v1/applications", headers=headers).json()["id"])


def test_save_valid_section_persists_and_marks_complete(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = client.patch(f"/api/v1/applications/{app_id}/sections/business", headers=h, json=VALID_BUSINESS)
    assert r.status_code == 200, r.text
    business = next(s for s in r.json()["sections"] if s["key"] == "business")
    assert business["complete"] is True and business["data"]["uen"] == "202312345K"
    assert r.json()["completeness"]["sections_complete"] == 1
    # reload shows the saved values
    again = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    assert next(s for s in again["sections"] if s["key"] == "business")["data"] == VALID_BUSINESS


def test_partial_draft_save_is_allowed_but_incomplete(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises",
        headers=h,
        json={"address_line_1": "10 Jalan Besar"},
    )
    assert r.status_code == 200
    premises = next(s for s in r.json()["sections"] if s["key"] == "premises")
    assert premises["started"] is True and premises["complete"] is False
    assert "postal_code" in premises["errors"]


def test_format_errors_are_422_with_field_details(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises",
        headers=h,
        json={**VALID_PREMISES, "postal_code": "12", "floor_area_sqm": "big", "bogus": 1},
    )
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation_failed"
    assert set(body["details"]["fields"]) == {"postal_code", "floor_area_sqm", "bogus"}


def test_unknown_section_404_and_other_owner_404_and_officer_403(client: TestClient, db: Session) -> None:
    make_user(db, "a@example.sg", Role.OPERATOR)
    make_user(db, "b@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    ha, hb, ho = login(client, "a@example.sg"), login(client, "b@example.sg"), login(client, "off@example.sg")
    app_id = _draft(client, ha)
    assert (
        client.patch(f"/api/v1/applications/{app_id}/sections/nope", headers=ha, json={}).status_code == 404
    )
    assert (
        client.patch(f"/api/v1/applications/{app_id}/sections/business", headers=hb, json={}).status_code
        == 404
    )
    assert (
        client.patch(f"/api/v1/applications/{app_id}/sections/business", headers=ho, json={}).status_code
        == 403
    )


def test_section_not_editable_outside_draft(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    app = db.get(Application, __import__("uuid").UUID(app_id))
    assert app is not None
    app.status = ApplicationStatus.UNDER_REVIEW
    db.commit()
    r = client.patch(f"/api/v1/applications/{app_id}/sections/business", headers=h, json=VALID_BUSINESS)
    assert r.status_code == 403
    assert r.json()["error"]["message"] == "This section is not open for changes."
