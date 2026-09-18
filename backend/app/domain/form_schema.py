"""Food Establishment Licence form definition (DOMAIN_MODEL.md, "Form definition").

Single source for both the server-side validation and the client (served at GET /form-schema, from
which the frontend builds its Zod validators).
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.domain.enums import DocumentType


@dataclass(frozen=True)
class FieldDef:
    key: str
    label: str
    kind: str  # text | email | tel | number | integer | date | select | textarea | checkbox
    required: bool = True
    max_length: int | None = None
    pattern: str | None = None
    pattern_message: str | None = None
    options: tuple[tuple[str, str], ...] = ()  # (value, label)
    min_value: float | None = None
    max_value: float | None = None
    help: str | None = None
    must_be_true: bool = False


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
            FieldDef("business_name", "Business name", "text", max_length=120),
            FieldDef(
                "uen",
                "UEN",
                "text",
                pattern=r"^[0-9]{8,9}[A-Z]$",
                pattern_message="Enter a valid UEN, for example 202312345K.",
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
            FieldDef("contact_name", "Contact person", "text", max_length=120),
            FieldDef("contact_email", "Contact email", "email", max_length=254),
            FieldDef(
                "contact_phone",
                "Contact phone",
                "tel",
                pattern=r"^\+?[0-9 ]{8,15}$",
                pattern_message="Enter 8 to 15 digits.",
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
                max_length=200,
                help="Include the unit number as shown on the tenancy agreement.",
            ),
            FieldDef(
                "postal_code",
                "Postal code",
                "text",
                pattern=r"^[0-9]{6}$",
                pattern_message="Enter the 6-digit postal code, for example 208787.",
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
                help="Total area under the tenancy, including kitchen and seating.",
            ),
            FieldDef(
                "tenancy_expiry", "Tenancy expiry date", "date", help="Must be after the licence start date."
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
                max_length=1000,
                help="Up to 1000 characters.",
            ),
            FieldDef("seating_capacity", "Seating capacity", "integer", min_value=0, max_value=2000),
            FieldDef("operating_hours", "Operating hours", "text", max_length=100),
            FieldDef(
                "food_handlers_count",
                "Number of food handlers",
                "integer",
                min_value=0,
                max_value=500,
                help="Each handler must hold a valid food hygiene certificate.",
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


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_field(f: FieldDef, value: Any) -> str | None:  # noqa: PLR0911 - one return per rule
    missing = value is None or (isinstance(value, str) and value.strip() == "")
    if f.kind == "checkbox":
        if f.must_be_true and value is not True:
            return "You must confirm this declaration."
        return None if isinstance(value, bool) or value is None else "Must be true or false."
    if missing:
        return "This field is required." if f.required else None
    if f.kind in ("text", "textarea", "email", "tel"):
        if not isinstance(value, str):
            return "Must be text."
        if f.max_length is not None and len(value) > f.max_length:
            return f"Must be {f.max_length} characters or fewer."
        if f.kind == "email" and not _EMAIL_RE.match(value):
            return "Enter a valid email address."
        if f.pattern and not re.match(f.pattern, value.strip()):
            return f.pattern_message or "Invalid format."
        return None
    if f.kind == "select":
        if value not in {v for v, _ in f.options}:
            return "Choose one of the options."
        return None
    if f.kind in ("number", "integer"):
        if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
            return "Must be a number."
        if f.kind == "integer" and int(value) != value:
            return "Must be a whole number."
        if f.min_value is not None and value < f.min_value:
            return f"Must be at least {f.min_value:g}."
        if f.max_value is not None and value > f.max_value:
            return f"Must be at most {f.max_value:g}."
        return None
    if f.kind == "date":
        if not isinstance(value, str):
            return "Enter a date."
        try:
            date.fromisoformat(value)
        except ValueError:
            return "Enter a date as YYYY-MM-DD."
        return None
    return None


REQUIRED_MESSAGES = frozenset({"This field is required.", "You must confirm this declaration."})


def validate_section(key: str, data: dict[str, Any], *, allow_missing: bool = False) -> dict[str, str]:
    """Return {field_key: message} for every failing field; empty dict means valid.

    With `allow_missing=True` (saving a draft), absent or empty required fields are not errors:
    only format and type problems are reported, so an operator can save and return later.
    """
    section = get_section(key)
    if section is None:
        raise KeyError(key)
    errors: dict[str, str] = {}
    known = {f.key for f in section.fields} | {k for k, _ in STAMPED_FIELDS.get(key, ())}
    for extra in set(data) - known:
        errors[extra] = "Unknown field."
    for f in section.fields:
        msg = _validate_field(f, data.get(f.key))
        if msg and not (allow_missing and msg in REQUIRED_MESSAGES):
            errors[f.key] = msg
    return errors


def is_section_complete(key: str, data: dict[str, Any] | None) -> bool:
    return data is not None and bool(data) and not validate_section(key, data)


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
                        "max_length": f.max_length,
                        "pattern": f.pattern,
                        "pattern_message": f.pattern_message,
                        "options": [{"value": v, "label": lbl} for v, lbl in f.options],
                        "min_value": f.min_value,
                        "max_value": f.max_value,
                        "help": f.help,
                        "must_be_true": f.must_be_true,
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
