from app.domain.completeness import compute
from app.domain.enums import DocumentType
from app.domain.form_schema import SECTION_KEYS, is_section_complete, validate_section
from tests.journeys import VALID_BUSINESS, VALID_DECLARATIONS, VALID_OPERATIONS, VALID_PREMISES


def test_valid_sections() -> None:
    assert validate_section("business", VALID_BUSINESS) == {}
    assert validate_section("premises", VALID_PREMISES) == {}
    assert validate_section("operations", VALID_OPERATIONS) == {}
    assert validate_section("declarations", VALID_DECLARATIONS) == {}


def test_field_rules() -> None:
    e = validate_section("business", {**VALID_BUSINESS, "uen": "abc", "contact_email": "nope"})
    assert "UEN" in e["uen"] and "email" in e["contact_email"]
    e = validate_section("premises", {**VALID_PREMISES, "postal_code": "12", "floor_area_sqm": 0})
    assert set(e) == {"postal_code", "floor_area_sqm"}
    e = validate_section("operations", {**VALID_OPERATIONS, "seating_capacity": 2.5, "unknown": 1})
    assert "whole" in e["seating_capacity"] and e["unknown"] == "Unknown field."
    e = validate_section("declarations", {"information_accurate": False, "consent_to_inspection": True})
    assert set(e) == {"information_accurate"}
    assert validate_section("business", {}) and all(
        v == "This field is required." for v in validate_section("business", {}).values()
    )
    assert (
        "date"
        in validate_section("premises", {**VALID_PREMISES, "tenancy_expiry": "31/10/2027"})["tenancy_expiry"]
    )


def test_completeness_percent_and_missing() -> None:
    c = compute({}, set())
    assert c.percent == 0 and not c.is_complete and len(c.missing) == 8
    c = compute({"business": VALID_BUSINESS, "premises": VALID_PREMISES}, {DocumentType.FLOOR_PLAN})
    assert c.percent == round(100 * 3 / 8)
    assert "Section: Operations" in c.missing and "Document: Floor plan" not in c.missing
    c = compute(
        {
            "business": VALID_BUSINESS,
            "premises": VALID_PREMISES,
            "operations": VALID_OPERATIONS,
            "declarations": VALID_DECLARATIONS,
        },
        set(DocumentType),
    )
    assert c.is_complete and c.percent == 100 and c.missing == ()


def test_is_section_complete_and_keys() -> None:
    assert SECTION_KEYS == ("business", "premises", "operations", "declarations")
    assert is_section_complete("business", VALID_BUSINESS)
    assert not is_section_complete("business", None)
    assert not is_section_complete("business", {**VALID_BUSINESS, "uen": ""})


ODD_VALUES: list[object] = [None, True, False, 0, 1.5, 10**400, ["x"], {"a": 1}, [], {}, "yes", "a\x00b", ""]
NOT_BOOLEAN: list[object] = [["x"], {"a": 1}, [], {}, 1, 0, 1.5, "yes", "", "a\x00b"]


def test_a_select_given_a_list_or_object_is_a_message_not_a_crash() -> None:
    for bad in (["x"], {"a": 1}, [["x"]], 1, True, 1.5, "a\x00b"):
        e = validate_section("business", {**VALID_BUSINESS, "entity_type": bad})
        assert e == {"entity_type": "Choose one of the options."}, bad
    assert validate_section("premises", {**VALID_PREMISES, "premises_type": ["x"]}) == {
        "premises_type": "Choose one of the options."
    }


def test_no_field_crashes_on_any_json_shape() -> None:
    sections = {
        "business": VALID_BUSINESS,
        "premises": VALID_PREMISES,
        "operations": VALID_OPERATIONS,
        "declarations": VALID_DECLARATIONS,
    }
    for key, valid in sections.items():
        for field_key in valid:
            for odd in ODD_VALUES:
                for allow_missing in (False, True):
                    errors = validate_section(key, {**valid, field_key: odd}, allow_missing=allow_missing)
                    assert isinstance(errors, dict), (key, field_key, odd)


def test_a_non_boolean_declaration_is_never_a_confirm_prompt() -> None:
    for bad in NOT_BOOLEAN:
        data = {"information_accurate": bad, "consent_to_inspection": True}
        assert validate_section("declarations", data) == {"information_accurate": "Must be true or false."}
        # a draft must not store it either
        assert validate_section("declarations", data, allow_missing=True) == {
            "information_accurate": "Must be true or false."
        }


def test_an_unticked_or_missing_declaration_still_asks_to_confirm_and_a_draft_tolerates_it() -> None:
    confirm = "You must confirm this declaration."
    for unticked in (False, None):
        data = {"information_accurate": unticked, "consent_to_inspection": True}
        assert validate_section("declarations", data) == {"information_accurate": confirm}
        assert validate_section("declarations", data, allow_missing=True) == {}
    assert validate_section("declarations", {}, allow_missing=True) == {}
    assert set(validate_section("declarations", {})) == {"information_accurate", "consent_to_inspection"}
