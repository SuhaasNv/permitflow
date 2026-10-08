"""Singapore-specific field rules for the application form (US-108).

Each rule is a small pure function: it returns an error message, or None when the value passes. Which rule
a field uses is declared once in `form_schema.py` (`FieldDef.rule`); the frontend mirrors these functions in
`frontend/src/lib/fieldRules.ts` and both are held to the same good/bad table
(`backend/tests/fixtures/form_rules.json`).
"""

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

# Singapore has no daylight saving: a fixed UTC+8 offset is exact and needs no tz database in the image.
SINGAPORE = timezone(timedelta(hours=8))

PHONE_MESSAGE = "Enter a Singapore number: 8 digits starting with 3, 6, 8 or 9, for example +65 9123 4567."
UEN_MESSAGE = "Enter a valid UEN, for example 202312345K."
EMAIL_MESSAGE = "Enter a valid email address, for example name@example.com."
POSTAL_FORMAT_MESSAGE = "Enter the 6-digit postal code, for example 208787."
POSTAL_SECTOR_MESSAGE = "Postal codes start with 01 to 82. Check the first two digits."
MIN_LENGTH_MESSAGE = "Enter at least {n} characters."
NAME_ALNUM_MESSAGE = "Include at least one letter or number."
PERSON_CHARS_MESSAGE = "Use letters, spaces and these marks only: ' - . , /"
PERSON_LETTER_MESSAGE = "Include at least one letter."
ADDRESS_PARTS_MESSAGE = "Include the street name and the house or unit number."
ADDRESS_UNIT_MESSAGE = "Write the unit as #05-12: a floor of 2 or 3 digits, a dash, a unit of 2 to 5 digits."
ADDRESS_POSTAL_MESSAGE = "Leave the postal code out of the address; it has its own field."
DECIMALS_MESSAGE = "Use at most {n} decimal places."

MIN_POSTAL_SECTOR = 1
MAX_POSTAL_SECTOR = 82
EARLIEST_UEN_YEAR = 1800


def singapore_today(now: datetime | None = None) -> date:
    return (now or datetime.now(SINGAPORE)).astimezone(SINGAPORE).date()


# ---------- helpers ----------


def _category(ch: str) -> str:
    return unicodedata.category(ch)


def has_letter(value: str) -> bool:
    return any(_category(c).startswith("L") for c in value)


def has_letter_or_digit(value: str) -> bool:
    return any(_category(c)[0] in ("L", "N") for c in value)


def add_months(day: date, months: int) -> date:
    """Calendar months ahead; the day is clamped to the end of a shorter month (31 Jan + 1 month = 28 Feb)."""
    index = day.year * 12 + (day.month - 1) + months
    year, month = divmod(index, 12)
    month += 1
    for d in (day.day, 30, 29, 28):
        try:
            return date(year, month, d)
        except ValueError:
            continue
    raise ValueError("unreachable")  # pragma: no cover


# ---------- phone ----------

_PHONE_ALLOWED = re.compile(r"^\+?[0-9 \-]+$")
_PHONE_FIRST_DIGITS = "3689"


def normalise_phone(value: str) -> str | None:
    """`+65 XXXX XXXX` for a valid Singapore number (optional +65 or 65, spaces, dashes), else None."""
    if not _PHONE_ALLOWED.match(value):
        return None
    digits = re.sub(r"[ \-]", "", value)
    if digits.startswith("+"):
        if not digits.startswith("+65"):
            return None
        local = digits[3:]
    elif len(digits) == 10 and digits.startswith("65"):
        local = digits[2:]
    else:
        local = digits
    if len(local) != 8 or not local.isdigit() or local[0] not in _PHONE_FIRST_DIGITS:
        return None
    return f"+65 {local[:4]} {local[4:]}"


def check_phone(value: str) -> str | None:
    return None if normalise_phone(value) is not None else PHONE_MESSAGE


# ---------- UEN ----------

_UEN_BUSINESS = re.compile(r"^[0-9]{8}[A-Z]$")
_UEN_COMPANY = re.compile(r"^([0-9]{4})[0-9]{5}[A-Z]$")
_UEN_OTHER = re.compile(r"^[TSR][0-9]{2}[A-Z]{2}[0-9]{4}[A-Z]$")


def check_uen(value: str, *, current_year: int) -> str | None:
    """The three ACRA formats. `value` is already uppercased and trimmed."""
    if _UEN_BUSINESS.match(value) or _UEN_OTHER.match(value):
        return None
    m = _UEN_COMPANY.match(value)
    if m and EARLIEST_UEN_YEAR <= int(m.group(1)) <= current_year:
        return None
    return UEN_MESSAGE


# ---------- email ----------

_TLD = re.compile(r"^(?:[A-Za-z]{2,}|xn--[A-Za-z0-9-]{2,})$")


def check_email(value: str) -> str | None:
    if value.count("@") != 1 or any(ch.isspace() for ch in value) or ".." in value:
        return EMAIL_MESSAGE
    local, domain = value.split("@")
    if not local or local.startswith(".") or local.endswith("."):
        return EMAIL_MESSAGE
    labels = domain.split(".")
    if len(labels) < 2 or any(not label for label in labels) or not _TLD.match(labels[-1]):
        return EMAIL_MESSAGE
    return None


# ---------- names ----------

_PERSON_MARKS = frozenset(" '’-.,/")


def check_business_name(value: str) -> str | None:
    return None if has_letter_or_digit(value) else NAME_ALNUM_MESSAGE


def check_person_name(value: str) -> str | None:
    if not all(_category(c)[0] in ("L", "M") or c in _PERSON_MARKS for c in value):
        return PERSON_CHARS_MESSAGE
    return None if has_letter(value) else PERSON_LETTER_MESSAGE


# ---------- postal code and address ----------


def check_postal_code(value: str) -> str | None:
    if not re.fullmatch(r"[0-9]{6}", value):
        return POSTAL_FORMAT_MESSAGE
    if not MIN_POSTAL_SECTOR <= int(value[:2]) <= MAX_POSTAL_SECTOR:
        return POSTAL_SECTOR_MESSAGE
    return None


_UNIT = re.compile(r"#[0-9]{2,3}-[0-9]{2,5}(?![0-9])")
_SIX_DIGITS = re.compile(r"(?<![0-9])[0-9]{6}(?![0-9])")


def check_address(value: str) -> str | None:
    if not any("0" <= c <= "9" for c in value) or not has_letter(value):
        return ADDRESS_PARTS_MESSAGE
    for i, ch in enumerate(value):
        if ch == "#" and not _UNIT.match(value, i):
            return ADDRESS_UNIT_MESSAGE
    if _SIX_DIGITS.search(value):
        return ADDRESS_POSTAL_MESSAGE
    return None


# ---------- numbers and dates ----------


def check_decimals(value: float, max_decimals: int) -> str | None:
    exponent = Decimal(repr(value)).as_tuple().exponent
    if isinstance(exponent, int) and -exponent > max_decimals:
        return DECIMALS_MESSAGE.format(n=max_decimals)
    return None


_ISO_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def parse_iso_date(value: str) -> date | None:
    """A real calendar date written YYYY-MM-DD, nothing looser (2026-02-31 and 20260131 are both refused)."""
    if not _ISO_DATE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def check_future_window(
    day: date, *, today: date, min_months_ahead: int | None, max_years_ahead: int | None
) -> str | None:
    """After today, at least `min_months_ahead` months out, at most `max_years_ahead` years out."""
    if day <= today:
        return "Enter a date after today."
    if min_months_ahead is not None and day < add_months(today, min_months_ahead):
        return f"Enter a date at least {min_months_ahead} months from today."
    if max_years_ahead is not None and day > add_months(today, 12 * max_years_ahead):
        return f"Enter a date no more than {max_years_ahead} years from today."
    return None
