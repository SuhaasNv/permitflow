"""Table-driven check of every form rule (US-108). The good/bad examples live in one JSON file that the
frontend suite reads too (`frontend/src/lib/formRules.test.ts`), so the two validators cannot drift apart."""

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.domain import field_rules
from app.domain.form_schema import normalise_section, schema_as_dict, validate_section
from app.domain.hours import summarise_hours, time_options, validate_hours
from app.domain.text_clean import clean_text

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "form_rules.json"
DATA: dict[str, Any] = json.loads(FIXTURE.read_text())
DEFAULT_TODAY = date.fromisoformat(DATA["today"])


def _id(case: dict[str, Any]) -> str:
    return f"{case['field']}:{json.dumps(case['value'], ensure_ascii=True)[:60]}"


def test_fixture_schema_is_current() -> None:
    """The frontend tests build their validators from the schema stored in the fixture: keep it in step."""
    assert DATA["schema"] == json.loads(json.dumps(schema_as_dict())), (
        "form_rules.json is out of date: regenerate its `schema` from schema_as_dict()"
    )


@pytest.mark.parametrize("case", DATA["cases"], ids=_id)
def test_rule_table(case: dict[str, Any]) -> None:
    today = date.fromisoformat(case.get("today", DATA["today"]))
    section, field, value = case["section"], case["field"], case["value"]
    errors = validate_section(section, {field: value}, allow_missing=True, today=today)
    if case["valid"]:
        assert field not in errors, errors
        assert normalise_section(section, {field: value})[field] == case["stored"]
    else:
        assert errors.get(field) == case["message"]


@pytest.mark.parametrize("case", DATA["cleaning"], ids=lambda c: repr(c["input"])[:40])
def test_clean_text_table(case: dict[str, Any]) -> None:
    assert clean_text(case["input"], multiline=case["multiline"]) == case["output"]


@pytest.mark.parametrize("case", DATA["summaries"], ids=lambda c: c["text"] or "unreadable")
def test_hours_summary_table(case: dict[str, Any]) -> None:
    assert summarise_hours(case["value"]) == case["text"]


def test_required_fields_are_reported_when_not_a_draft() -> None:
    errors = validate_section("operations", {}, today=DEFAULT_TODAY)
    assert set(errors) == {
        "cuisine_description",
        "seating_capacity",
        "operating_hours",
        "food_handlers_count",
    }
    assert set(errors.values()) == {"This field is required."}
    # text that cleans to nothing is missing, not "valid but empty"
    assert validate_section("operations", {"cuisine_description": "\u200b \u200c"}, today=DEFAULT_TODAY)[
        "cuisine_description"
    ] == ("This field is required.")


def test_legacy_hours_string_fails_a_draft_but_reads_as_written() -> None:
    legacy = {"operating_hours": "Mon-Sun 7am-9pm"}
    assert validate_section("operations", legacy, allow_missing=True)["operating_hours"] == (
        "Pick your opening days and hours."
    )
    assert "operating_hours" not in validate_section("operations", legacy, allow_missing=True, snapshot=True)
    assert summarise_hours(legacy["operating_hours"]) == "Mon-Sun 7am-9pm"
    assert validate_hours("Mon-Sun 7am-9pm", snapshot=True) is None


def test_a_snapshot_ignores_rules_that_depend_on_today() -> None:
    expired = {"tenancy_expiry": "2020-01-01"}
    assert "tenancy_expiry" in validate_section("premises", expired, allow_missing=True)
    assert "tenancy_expiry" not in validate_section("premises", expired, allow_missing=True, snapshot=True)
    # a calendar that does not exist is wrong in any record
    assert "tenancy_expiry" in validate_section(
        "premises", {"tenancy_expiry": "2026-02-31"}, allow_missing=True, snapshot=True
    )


def test_time_options_are_48_half_hours() -> None:
    options = time_options()
    assert len(options) == 48 and options[0] == "00:00" and options[1] == "00:30" and options[-1] == "23:30"


def test_add_months_clamps_to_month_end() -> None:
    assert field_rules.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert field_rules.add_months(date(2028, 2, 29), 12) == date(2029, 2, 28)
    assert field_rules.add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert field_rules.add_months(date(2026, 10, 8), 360) == date(2056, 10, 8)


def test_singapore_today_uses_the_singapore_calendar() -> None:
    from datetime import UTC, datetime

    # 17:00 UTC on the 7th is already 01:00 on the 8th in Singapore
    assert field_rules.singapore_today(datetime(2026, 10, 7, 17, 0, tzinfo=UTC)) == date(2026, 10, 8)
    assert field_rules.singapore_today(datetime(2026, 10, 7, 15, 59, tzinfo=UTC)) == date(2026, 10, 7)


def test_schema_declares_the_new_rules() -> None:
    fields = {f["key"]: f for s in schema_as_dict()["sections"] for f in s["fields"]}
    assert fields["operating_hours"]["kind"] == "hours"
    assert fields["operating_hours"]["step_minutes"] == 30
    assert [o["value"] for o in fields["operating_hours"]["options"]] == [
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
    ]
    assert fields["contact_phone"]["rule"] == "sg_phone"
    assert fields["uen"]["rule"] == "uen"
    assert (fields["tenancy_expiry"]["min_months_ahead"], fields["tenancy_expiry"]["max_years_ahead"]) == (
        3,
        30,
    )
    assert fields["floor_area_sqm"]["max_decimals"] == 2
    assert fields["food_handlers_count"]["min_value"] == 1
