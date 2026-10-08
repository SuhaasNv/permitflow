"""US-108: format rules on the application form, end to end through the API (422 shape, what is stored,
legacy free-text hours)."""

import copy
import uuid
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.field_rules import singapore_today
from app.models import Application, ApplicationRevision
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import VALID_BUSINESS, VALID_OPERATIONS, VALID_PREMISES
from tests.journeys import draft as _draft
from tests.journeys import submitted as _submitted

PHONE_MESSAGE = "Enter a Singapore number: 8 digits starting with 3, 6, 8 or 9, for example +65 9123 4567."


def _patch(client: TestClient, h: dict[str, str], app_id: str, key: str, body: dict[str, Any]) -> Any:
    return client.patch(f"/api/v1/applications/{app_id}/sections/{key}", headers=h, json=body)


def _operator(client: TestClient, db: Session) -> tuple[dict[str, str], str]:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    return h, _draft(client, h)


def test_bad_values_are_422_in_the_standard_shape_with_the_field_message(
    client: TestClient, db: Session
) -> None:
    h, app_id = _operator(client, db)
    r = _patch(
        client,
        h,
        app_id,
        "business",
        {**VALID_BUSINESS, "contact_phone": "+60 9123 4567", "uen": "12345", "contact_email": "a@b"},
    )
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "validation_failed" and error["message"] == "Some fields need attention."
    assert error["details"]["fields"] == {
        "contact_phone": PHONE_MESSAGE,
        "uen": "Enter a valid UEN, for example 202312345K.",
        "contact_email": "Enter a valid email address, for example name@example.com.",
    }

    r = _patch(
        client,
        h,
        app_id,
        "premises",
        {
            **VALID_PREMISES,
            "postal_code": "831234",
            "address_line_1": "10 Jalan Besar #1-12",
            "floor_area_sqm": 48.123,
            "tenancy_expiry": (singapore_today() + timedelta(days=30)).isoformat(),
        },
    )
    assert r.status_code == 422
    fields = r.json()["error"]["details"]["fields"]
    assert fields["postal_code"] == "Postal codes start with 01 to 82. Check the first two digits."
    assert fields["address_line_1"].startswith("Write the unit as #05-12")
    assert fields["floor_area_sqm"] == "Use at most 2 decimal places."
    assert fields["tenancy_expiry"] == "Enter a date at least 3 months from today."

    r = _patch(client, h, app_id, "premises", {**VALID_PREMISES, "tenancy_expiry": "2027-02-30"})
    assert r.json()["error"]["details"]["fields"] == {"tenancy_expiry": "Enter a real date as YYYY-MM-DD."}


def test_hours_rules_over_the_api(client: TestClient, db: Session) -> None:
    h, app_id = _operator(client, db)
    base = VALID_OPERATIONS["operating_hours"]
    cases = [
        ({**base, "days": []}, "Choose at least one day you open."),
        ({**base, "opens": "09:00", "closes": "09:00"}, "Opening and closing time cannot be the same."),
        ({**base, "opens": "07:10"}, "Choose a time on the half hour, from 00:00 to 23:30."),
        ({**base, "closes": None}, "Choose an opening and a closing time."),
        ("Mon-Sun 7am-9pm", "Pick your opening days and hours."),
    ]
    for hours, message in cases:
        r = _patch(client, h, app_id, "operations", {**VALID_OPERATIONS, "operating_hours": hours})
        assert r.status_code == 422, hours
        assert r.json()["error"]["details"]["fields"] == {"operating_hours": message}


def test_values_are_stored_normalised(client: TestClient, db: Session) -> None:
    h, app_id = _operator(client, db)
    r = _patch(
        client,
        h,
        app_id,
        "business",
        {
            **VALID_BUSINESS,
            "business_name": "  Kopi\u200b   &  Kaya\u202e  ",
            "uen": " 202312345k ",
            "contact_email": "  Wei.Ling@KopiKaya.SG ",
            "contact_phone": "9123-4567",
            "contact_name": "Tan\u200b  Wei Ling",
        },
    )
    assert r.status_code == 200, r.text
    data = next(s for s in r.json()["sections"] if s["key"] == "business")["data"]
    assert data["business_name"] == "Kopi & Kaya"
    assert data["uen"] == "202312345K"
    assert data["contact_email"] == "wei.ling@kopikaya.sg"
    assert data["contact_phone"] == "+65 9123 4567"
    assert data["contact_name"] == "Tan Wei Ling"
    app = db.get(Application, uuid.UUID(app_id))
    assert app is not None and app.draft_data["business"]["contact_phone"] == "+65 9123 4567"

    r = _patch(
        client,
        h,
        app_id,
        "operations",
        {
            **VALID_OPERATIONS,
            "cuisine_description": "Kaya  toast,\r\nkopi.\n\n\n\nTeh.\u200b",
            "operating_hours": {
                "days": ["fri", "mon", "mon"],
                "opens": "18:00",
                "closes": "02:00",
                "open_24h": False,
            },
        },
    )
    assert r.status_code == 200, r.text
    ops = next(s for s in r.json()["sections"] if s["key"] == "operations")
    assert ops["data"]["cuisine_description"] == "Kaya toast,\nkopi.\n\nTeh."
    assert ops["data"]["operating_hours"] == {
        "days": ["mon", "fri"],
        "opens": "18:00",
        "closes": "02:00",
        "open_24h": False,
    }
    assert ops["complete"] is True


def test_open_24_hours_stores_no_times(client: TestClient, db: Session) -> None:
    h, app_id = _operator(client, db)
    hours = {"days": ["sat", "sun"], "opens": "07:00", "closes": "21:00", "open_24h": True}
    r = _patch(client, h, app_id, "operations", {**VALID_OPERATIONS, "operating_hours": hours})
    assert r.status_code == 200, r.text
    ops = next(s for s in r.json()["sections"] if s["key"] == "operations")
    assert ops["data"]["operating_hours"] == {
        "days": ["sat", "sun"],
        "opens": None,
        "closes": None,
        "open_24h": True,
    }


def test_the_draft_keeps_a_legacy_string_but_asks_for_a_new_pick(client: TestClient, db: Session) -> None:
    h, app_id = _operator(client, db)
    assert _patch(client, h, app_id, "operations", VALID_OPERATIONS).status_code == 200
    app = db.get(Application, uuid.UUID(app_id))
    assert app is not None
    draft = copy.deepcopy(app.draft_data)
    draft["operations"]["operating_hours"] = "Mon-Sun 7am-9pm"
    app.draft_data = draft
    db.commit()

    view = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    ops = next(s for s in view["sections"] if s["key"] == "operations")
    assert ops["data"]["operating_hours"] == "Mon-Sun 7am-9pm"  # shown as written
    assert ops["complete"] is False
    assert ops["errors"] == {"operating_hours": "Pick your opening days and hours."}


def test_a_submitted_revision_with_legacy_hours_still_reads_and_stays_complete(
    client: TestClient, db: Session
) -> None:
    app_id, _op, off = _submitted(client, db)
    rev = db.scalar(select(ApplicationRevision))
    assert rev is not None
    form = copy.deepcopy(rev.form_data)
    form["operations"]["operating_hours"] = "Mon-Sun 7am-9pm"
    # and a tenancy that has since passed the three-month mark: a snapshot is not re-judged against today
    form["premises"]["tenancy_expiry"] = (singapore_today() + timedelta(days=10)).isoformat()
    rev.form_data = form
    db.commit()

    body = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    ops = next(s for s in body["sections"] if s["key"] == "operations")
    assert ops["data"]["operating_hours"] == "Mon-Sun 7am-9pm"
    assert all(s["complete"] for s in body["sections"])


def test_the_new_hours_object_reaches_the_officer_unchanged(client: TestClient, db: Session) -> None:
    app_id, _op, off = _submitted(client, db)
    body = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    ops = next(s for s in body["sections"] if s["key"] == "operations")
    assert ops["data"]["operating_hours"] == VALID_OPERATIONS["operating_hours"]


def test_the_form_schema_declares_the_rules(client: TestClient, db: Session) -> None:
    h, _ = _operator(client, db)
    body = client.get("/api/v1/form-schema", headers=h).json()
    fields = {f["key"]: f for s in body["sections"] for f in s["fields"]}
    assert fields["operating_hours"]["kind"] == "hours"
    assert fields["contact_phone"]["rule"] == "sg_phone"
    assert fields["tenancy_expiry"]["min_months_ahead"] == 3
