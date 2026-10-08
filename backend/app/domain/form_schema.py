"""Food Establishment Licence form definition (DOMAIN_MODEL.md, "Form definition").

Single source for both the server-side validation and the client (served at GET /form-schema, from
which the frontend builds its Zod validators).
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.domain import field_rules, hours
from app.domain.enums import DocumentType
from app.domain.text_clean import clean_text


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str
    # text | email | tel | number | integer | date | select | textarea | checkbox | hours
    kind: str
    required: bool = True
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    pattern_message: str | None = None
    options: tuple[tuple[str, str], ...] = ()  # (value, label)
    min_value: float | None = None
    max_value: float | None = None
    help: str | None = None
    must_be_true: bool = False
    # Named rule from `field_rules`: sg_phone, uen, business_name, person_name, sg_postal, sg_address.
    rule: str | None = None
    max_decimals: int | None = None  # number: digits allowed after the point
    min_months_ahead: int | None = None  # date: at least this many calendar months after today (Singapore)
    max_years_ahead: int | None = None  # date: at most this many calendar years after today
    step_minutes: int | None = None  # hours: the time list runs in steps of this many minutes


@dataclass(frozen=True)
class SectionDef:
    key: str
    title: str
    description: str
    fields: tuple[FieldDef, ...] = field(default_factory=tuple)


SECTIONS: tuple[SectionDef, ...] = (
    SectionDef(
        "business",
        "Business details",
        "The registered business applying for the licence",
        (
            FieldDef(
                "business_name",
                "Business name",
                "text",
                min_length=2,
                max_length=120,
                rule="business_name",
            ),
            FieldDef(
                "uen",
                "UEN",
                "text",
                rule="uen",
                help="Unique Entity Number as registered with ACRA.",
            ),
            FieldDef(
                "entity_type",
                "Entity type",
                "select",
                options=(
                    ("sole_proprietorship", "Sole proprietorship"),
                    ("partnership", "Partnership"),
                    ("private_limited", "Private limited company"),
                    ("other", "Other"),
                ),
            ),
            FieldDef(
                "contact_name", "Contact person", "text", min_length=2, max_length=120, rule="person_name"
            ),
            FieldDef("contact_email", "Contact email", "email", max_length=254),
            FieldDef(
                "contact_phone",
                "Contact phone",
                "tel",
                rule="sg_phone",
                help="A Singapore number, for example +65 9123 4567.",
            ),
        ),
    ),
    SectionDef(
        "premises",
        "Premises",
        "Where the food will be prepared and sold",
        (
            FieldDef(
                "address_line_1",
                "Premises address",
                "text",
                min_length=5,
                max_length=200,
                rule="sg_address",
                help="Include the unit number as shown on the tenancy agreement, for example #01-12.",
            ),
            FieldDef(
                "postal_code",
                "Postal code",
                "text",
                rule="sg_postal",
            ),
            FieldDef(
                "premises_type",
                "Premises type",
                "select",
                options=(
                    ("shophouse", "Shophouse"),
                    ("mall_unit", "Mall unit"),
                    ("hawker_stall", "Hawker stall"),
                    ("standalone", "Standalone building"),
                ),
            ),
            FieldDef(
                "floor_area_sqm",
                "Floor area (sqm)",
                "number",
                min_value=1,
                max_value=10000,
                max_decimals=2,
                help="Total area under the tenancy, including kitchen and seating.",
            ),
            FieldDef(
                "tenancy_expiry",
                "Tenancy expiry date",
                "date",
                min_months_ahead=3,
                max_years_ahead=30,
                help="Must be at least 3 months from today.",
            ),
        ),
    ),
    SectionDef(
        "operations",
        "Operations",
        "What you serve and how you operate",
        (
            FieldDef(
                "cuisine_description",
                "Description of food and cuisine",
                "textarea",
                min_length=10,
                max_length=1000,
                help="10 to 1000 characters.",
            ),
            FieldDef("seating_capacity", "Seating capacity", "integer", min_value=0, max_value=2000),
            FieldDef(
                "food_handlers_count",
                "Number of food handlers",
                "integer",
                min_value=1,
                max_value=500,
                help="Each handler must hold a valid food hygiene certificate.",
            ),
            FieldDef(
                "operating_hours",
                "Operating hours",
                "hours",
                options=hours.DAYS,
                step_minutes=hours.STEP_MINUTES,
                help="Pick the days you open, then the times. The same hours apply to every day you pick.",
            ),
        ),
    ),
    SectionDef(
        "declarations",
        "Declarations",
        "Confirm before you submit",
        (
            FieldDef(
                "information_accurate",
                "I confirm that the information provided is accurate and complete "
                "to the best of my knowledge.",
                "checkbox",
                must_be_true=True,
            ),
            FieldDef(
                "consent_to_inspection",
                "I consent to an inspection of the premises by a licensing officer "
                "at a mutually arranged time.",
                "checkbox",
                must_be_true=True,
            ),
        ),
    ),
)

SECTION_KEYS: tuple[str, ...] = tuple(s.key for s in SECTIONS)

# Server-stamped values stored beside the form fields. Not entered by the operator, tolerated by the
# validator, compared by the diff: re-confirming the declarations is a change (US-041 follow-up).
STAMPED_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {"declarations": (("confirmed_at", "Confirmed on"),)}
_SECTION_INDEX: dict[str, SectionDef] = {s.key: s for s in SECTIONS}

REQUIRED_DOCUMENT_TYPES: tuple[DocumentType, ...] = (
    DocumentType.BUSINESS_PROFILE,
    DocumentType.FLOOR_PLAN,
    DocumentType.TENANCY_AGREEMENT,
    DocumentType.FOOD_HYGIENE_CERTIFICATE,
)

DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.BUSINESS_PROFILE: "Business profile (ACRA)",
    DocumentType.FLOOR_PLAN: "Floor plan",
    DocumentType.TENANCY_AGREEMENT: "Tenancy agreement",
    DocumentType.FOOD_HYGIENE_CERTIFICATE: "Food hygiene certificate",
}


def get_section(key: str) -> SectionDef | None:
    return _SECTION_INDEX.get(key)


TEXT_KINDS = ("text", "textarea", "email", "tel")
_TEXT_RULES = {
    "business_name": field_rules.check_business_name,
    "person_name": field_rules.check_person_name,
    "sg_phone": field_rules.check_phone,
    "sg_postal": field_rules.check_postal_code,
    "sg_address": field_rules.check_address,
}


def normalise_value(f: FieldDef, value: Any) -> Any:
    """What the server stores: cleaned text (and the lower, upper or +65 forms), hours in week order."""
    if f.kind in TEXT_KINDS and isinstance(value, str):
        text = clean_text(value, multiline=f.kind == "textarea")
        if f.kind == "email":
            text = text.lower()
        elif f.rule == "uen":
            text = text.upper()
        elif f.rule == "sg_phone":
            text = field_rules.normalise_phone(text) or text
        return text
    if f.kind == "hours" and isinstance(value, dict):
        return hours.normalise_hours(value)
    return value


def normalise_section(key: str, data: dict[str, Any]) -> dict[str, Any]:
    """The section as it is stored. Unknown keys pass through untouched so the validator can name them."""
    section = get_section(key)
    if section is None:
        raise KeyError(key)
    by_key = {f.key: f for f in section.fields}
    return {k: (normalise_value(by_key[k], v) if k in by_key else v) for k, v in data.items()}


def _text_error(f: FieldDef, value: str, today: date) -> str | None:
    if f.min_length is not None and len(value) < f.min_length:
        return field_rules.MIN_LENGTH_MESSAGE.format(n=f.min_length)
    if f.max_length is not None and len(value) > f.max_length:
        return f"Must be {f.max_length} characters or fewer."
    if f.kind == "email":
        return field_rules.check_email(value)
    if f.rule == "uen":
        return field_rules.check_uen(value, current_year=today.year)
    check = _TEXT_RULES.get(f.rule or "")
    if check:
        return check(value)
    if f.pattern and not re.match(f.pattern, value):
        return f.pattern_message or "Invalid format."
    return None


def _validate_field(  # noqa: PLR0911, PLR0912 - one return per rule
    f: FieldDef, value: Any, *, today: date, snapshot: bool
) -> str | None:
    """`value` is already normalised. `snapshot` is a submitted, immutable record being read: the rules that
    depend on today's date are skipped and a pre-v0.4.1 free-text `operating_hours` is accepted."""
    missing = value is None or (isinstance(value, str) and value.strip() == "") or value == {}
    if f.kind == "checkbox":
        if f.must_be_true and value is not True:
            return "You must confirm this declaration."
        return None if isinstance(value, bool) or value is None else "Must be true or false."
    if missing:
        return "This field is required." if f.required else None
    if f.kind in TEXT_KINDS:
        if not isinstance(value, str):
            return "Must be text."
        return _text_error(f, value, today)
    if f.kind == "select":
        if value not in {v for v, _ in f.options}:
            return "Choose one of the options."
        return None
    if f.kind in ("number", "integer"):
        # math.isfinite converts to float and raises OverflowError for an int beyond ~1.8e308.
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or (isinstance(value, float) and not math.isfinite(value))
        ):
            return "Must be a number."
        if f.kind == "integer" and int(value) != value:
            return "Must be a whole number."
        if f.min_value is not None and value < f.min_value:
            return f"Must be at least {f.min_value:g}."
        if f.max_value is not None and value > f.max_value:
            return f"Must be at most {f.max_value:g}."
        if f.max_decimals is not None:
            return field_rules.check_decimals(value, f.max_decimals)
        return None
    if f.kind == "date":
        if not isinstance(value, str):
            return "Enter a date."
        day = field_rules.parse_iso_date(value)
        if day is None:
            return "Enter a real date as YYYY-MM-DD."
        if snapshot or (f.min_months_ahead is None and f.max_years_ahead is None):
            return None
        return field_rules.check_future_window(
            day, today=today, min_months_ahead=f.min_months_ahead, max_years_ahead=f.max_years_ahead
        )
    if f.kind == "hours":
        return hours.validate_hours(value, snapshot=snapshot)
    return None


REQUIRED_MESSAGES = frozenset({"This field is required.", "You must confirm this declaration."})


def validate_section(
    key: str,
    data: dict[str, Any],
    *,
    allow_missing: bool = False,
    today: date | None = None,
    snapshot: bool = False,
) -> dict[str, str]:
    """Return {field_key: message} for every failing field; empty dict means valid.

    Values are normalised first (the checks run on what would be stored). With `allow_missing=True` (saving
    a draft), absent or empty required fields are not errors: only format and type problems are reported,
    so an operator can save and return later. `today` is the Singapore date (default: now) for the rules
    that look ahead; `snapshot=True` is for reading a submitted revision (see `_validate_field`).
    """
    section = get_section(key)
    if section is None:
        raise KeyError(key)
    errors: dict[str, str] = {}
    known = {f.key for f in section.fields} | {k for k, _ in STAMPED_FIELDS.get(key, ())}
    for extra in set(data) - known:
        errors[extra] = "Unknown field."
    data = normalise_section(key, data)
    today = today or field_rules.singapore_today()
    for f in section.fields:
        msg = _validate_field(f, data.get(f.key), today=today, snapshot=snapshot)
        if msg and not (allow_missing and msg in REQUIRED_MESSAGES):
            errors[f.key] = msg
    return errors


def is_section_complete(key: str, data: dict[str, Any] | None, *, today: date | None = None) -> bool:
    return data is not None and bool(data) and not validate_section(key, data, today=today)


def schema_as_dict() -> dict[str, Any]:
    """JSON form of the definition for GET /form-schema."""
    return {
        "licence_type": "food_establishment",
        "licence_title": "Food Establishment Licence",
        "sections": [
            {
                "key": s.key,
                "title": s.title,
                "description": s.description,
                "fields": [
                    {
                        "key": f.key,
                        "label": f.label,
                        "kind": f.kind,
                        "required": f.required,
                        "min_length": f.min_length,
                        "max_length": f.max_length,
                        "pattern": f.pattern,
                        "pattern_message": f.pattern_message,
                        "options": [{"value": v, "label": lbl} for v, lbl in f.options],
                        "min_value": f.min_value,
                        "max_value": f.max_value,
                        "help": f.help,
                        "must_be_true": f.must_be_true,
                        "rule": f.rule,
                        "max_decimals": f.max_decimals,
                        "min_months_ahead": f.min_months_ahead,
                        "max_years_ahead": f.max_years_ahead,
                        "step_minutes": f.step_minutes,
                    }
                    for f in s.fields
                ],
            }
            for s in SECTIONS
        ],
        "required_documents": [
            {"type": t.value, "label": DOCUMENT_TYPE_LABELS[t]} for t in REQUIRED_DOCUMENT_TYPES
        ],
    }
