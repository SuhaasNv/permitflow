from app.domain.completeness import compute
from app.domain.enums import DocumentType
from app.domain.form_schema import SECTION_KEYS, is_section_complete, validate_section

VALID_BUSINESS = {
    "business_name": "Kopi & Kaya Toast House Pte. Ltd.",
    "uen": "202312345K",
    "entity_type": "private_limited",
    "contact_name": "Tan Wei Ling",
    "contact_email": "weiling.tan@kopikaya.sg",
    "contact_phone": "+65 9123 4567",
}
VALID_PREMISES = {
    "address_line_1": "10 Jalan Besar #01-12",
    "postal_code": "208787",
    "premises_type": "shophouse",
    "floor_area_sqm": 48,
    "tenancy_expiry": "2027-10-31",
}
VALID_OPERATIONS = {
    "cuisine_description": "Kaya toast, soft-boiled eggs, kopi and teh.",
    "seating_capacity": 24,
    "operating_hours": "Mon-Sun 7am-9pm",
    "food_handlers_count": 4,
}
VALID_DECLARATIONS = {"information_accurate": True, "consent_to_inspection": True}


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
