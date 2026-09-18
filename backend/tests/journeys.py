"""Shared, public test journeys and fixtures. Integration tests compose these instead of importing each
other's private helpers, so a test file can be renamed or deleted without breaking its neighbours."""

import io
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import Role
from tests.factories import login, make_user

VALID_BUSINESS: dict[str, Any] = {
    "business_name": "Kopi & Kaya Toast House Pte. Ltd.",
    "uen": "202312345K",
    "entity_type": "private_limited",
    "contact_name": "Tan Wei Ling",
    "contact_email": "weiling.tan@kopikaya.sg",
    "contact_phone": "+65 9123 4567",
}
VALID_PREMISES: dict[str, Any] = {
    "address_line_1": "10 Jalan Besar #01-12",
    "postal_code": "208787",
    "premises_type": "shophouse",
    "floor_area_sqm": 48,
    "tenancy_expiry": "2027-10-31",
}
VALID_OPERATIONS: dict[str, Any] = {
    "cuisine_description": "Kaya toast, soft-boiled eggs, kopi and teh.",
    "seating_capacity": 24,
    "operating_hours": "Mon-Sun 7am-9pm",
    "food_handlers_count": 4,
}
VALID_DECLARATIONS: dict[str, Any] = {"information_accurate": True, "consent_to_inspection": True}
VALID_SECTIONS: list[tuple[str, dict[str, Any]]] = [
    ("business", VALID_BUSINESS),
    ("premises", VALID_PREMISES),
    ("operations", VALID_OPERATIONS),
    ("declarations", VALID_DECLARATIONS),
]

PDF = b"%PDF-1.4\n%fake\n1 0 obj << >> endobj\n%%EOF\n"
_SENTENCE = (
    "Tenancy agreement between landlord and tenant. Business profile ACRA UEN. Floor plan kitchen. "
    "Food hygiene certificate. "
)
TXT = (_SENTENCE * 3).encode()
DOCUMENT_TYPES = ("business_profile", "floor_plan", "tenancy_agreement", "food_hygiene_certificate")

Headers = dict[str, str]


def draft(client: TestClient, h: Headers) -> str:
    return str(client.post("/api/v1/applications", headers=h).json()["id"])


def upload(
    client: TestClient,
    h: Headers,
    app_id: str,
    dtype: str,
    name: str,
    data: bytes,
    mime: str = "application/pdf",
):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=h,
        data={"document_type": dtype},
        files={"file": (name, io.BytesIO(data), mime)},
    )


def complete_draft(client: TestClient, h: Headers) -> str:
    """A draft with every section valid and every required document attached (TXT, mock-verified)."""
    app_id = draft(client, h)
    for key, data in VALID_SECTIONS:
        r = client.patch(f"/api/v1/applications/{app_id}/sections/{key}", headers=h, json=data)
        assert r.status_code == 200, r.text
    for dtype in DOCUMENT_TYPES:
        r = upload(client, h, app_id, dtype, f"{dtype}.txt", TXT, "text/plain")
        assert r.status_code == 201, r.text
    return app_id


def submitted(client: TestClient, db: Session) -> tuple[str, Headers, Headers]:
    """Operator `op@example.sg` and officer `off@example.sg`; one application at `application_received`."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    op = login(client, "op@example.sg")
    app_id = complete_draft(client, op)
    assert client.post(f"/api/v1/applications/{app_id}/submit", headers=op).status_code == 200
    return app_id, op, login(client, "off@example.sg")


def transition(client: TestClient, off: Headers, app_id: str, target: str, note: str | None = None) -> dict:  # type: ignore[type-arg]
    version = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()["version"]
    body: dict[str, Any] = {"target": target, "expected_version": version}
    if note:
        body["note"] = note
    r = client.post(f"/api/v1/officer/applications/{app_id}/transition", headers=off, json=body)
    assert r.status_code == 200, r.text
    return r.json()


def under_review(client: TestClient, db: Session) -> tuple[str, Headers, Headers, int]:
    app_id, op, off = submitted(client, db)
    view = transition(client, off, app_id, "under_review")
    return app_id, op, off, view["version"]


def add_feedback(client: TestClient, off: Headers, app_id: str, **item: Any) -> dict:  # type: ignore[type-arg]
    r = client.post(f"/api/v1/officer/applications/{app_id}/feedback", headers=off, json=item)
    assert r.status_code == 201, r.text
    return r.json()


def flag_and_request(client: TestClient, db: Session) -> tuple[str, Headers, Headers]:
    """Under review → premises section item + floor plan document item → resubmission requested."""
    app_id, op, off, _ = under_review(client, db)
    add_feedback(
        client, off, app_id, target_type="section", section_key="premises", message="Confirm the address."
    )
    add_feedback(
        client,
        off,
        app_id,
        target_type="document",
        document_type="floor_plan",
        message="Upload a clearer plan.",
    )
    transition(client, off, app_id, "pending_pre_site_resubmission")
    return app_id, op, off
