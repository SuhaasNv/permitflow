"""Abuse case 7 (US-105; THREAT_MODEL T34 formula injection, US-100): a cell of the AI usage export that
starts like a formula must reach the spreadsheet as text.

Already asserted elsewhere and not repeated: all six leading characters in the one cell the administrator
controls, the user's name
(tests/integration/test_ai_usage.py::test_csv_cells_that_look_like_formulas_are_quoted), and the cell
function itself (tests/unit/test_ai_usage_domain.py). The cell an *operator* controls is a different
door: the business name typed into the form travels to the administrator's export unchanged, and that
is what is attacked here.
"""

import csv
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.ai_usage import CSV_COLUMNS
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import TXT, VALID_BUSINESS, upload

API = "/api/v1"
LEADS = ("=", "+", "-", "@", "\t", "\r")


def _export(client: TestClient, db: Session, business_name: str) -> tuple[list[list[str]], int]:
    """An operator files a check under `business_name`; the administrator exports. Returns the rows and the
    status of the form save."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "adm@example.sg", Role.ADMIN)
    op = login(client, "op@example.sg")
    app_id = str(client.post(f"{API}/applications", headers=op).json()["id"])
    saved = client.patch(
        f"{API}/applications/{app_id}/sections/business",
        headers=op,
        json={**VALID_BUSINESS, "business_name": business_name},
    )
    assert upload(client, op, app_id, "business_profile", "profile.txt", TXT, "text/plain").status_code == 201
    adm = login(client, "adm@example.sg")
    r = client.get(f"{API}/admin/ai-usage.csv", headers=adm)
    assert r.status_code == 200
    return list(csv.reader(io.StringIO(r.text, newline=""))), saved.status_code


@pytest.mark.parametrize("lead", LEADS)
def test_a_business_name_that_starts_like_a_formula_is_exported_as_text(
    client: TestClient, db: Session, lead: str
) -> None:
    evil = f'{lead}cmd|"/c calc"!A1'
    rows, saved = _export(client, db, evil)
    assert rows[0] == list(CSV_COLUMNS) and len(rows) == 2
    cell = rows[1][CSV_COLUMNS.index("business_name")]
    if saved == 200:
        # Either the form already cleaned the lead away, or the export put a single quote in front.
        assert cell == "'" + evil or not cell.startswith(LEADS), (lead, cell)
    else:
        assert saved in (400, 422)  # refused at the form: nothing hostile ever reaches the export
    assert not any(c.startswith(LEADS) for row in rows for c in row), "a cell would run as a formula"


def test_a_formula_in_the_middle_of_a_name_is_left_alone(client: TestClient, db: Session) -> None:
    """Only the first character matters to a spreadsheet; the export does not mangle ordinary names."""
    rows, saved = _export(client, db, "Kopi =Kaya + Toast @ Home")
    assert saved == 200
    assert rows[1][CSV_COLUMNS.index("business_name")] == "Kopi =Kaya + Toast @ Home"
