"""Licence certificate data (US-051). Pure: what the certificate says, derived from the approved revision.

The platform is fictional; the issuing body and the format are inventions for the assessment. The
certificate is a record of the decision, not a legal instrument.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

ISSUER = "Food Establishments Unit (fictional)"
LICENCE_TITLE = "Food Establishment Licence"
VALIDITY_DAYS = 365


@dataclass(frozen=True)
class LicenceData:
    licence_no: str
    reference_no: str
    business_name: str
    uen: str
    entity_type: str
    premises_address: str
    postal_code: str
    holder_name: str
    valid_from: date
    valid_to: date
    approved_by: str
    verification_code: str
    preview: bool = False


def licence_number(year: int, sequence: int) -> str:
    """FEL-<year>-<six digits>: the same shape as application references, a different prefix."""
    return f"FEL-{year}-{sequence:06d}"


def validity(issued_on: date) -> tuple[date, date]:
    return issued_on, issued_on + timedelta(days=VALIDITY_DAYS) - timedelta(days=1)


def verification_code(licence_no: str, reference_no: str, issued_on: date) -> str:
    """Short, human-readable code printed on the certificate so an officer can match it to the record.
    Deterministic on the record's own facts; not a signature."""
    import hashlib

    digest = hashlib.sha256(f"{licence_no}|{reference_no}|{issued_on.isoformat()}".encode()).hexdigest()
    return f"{digest[:4]}-{digest[4:8]}-{digest[8:12]}".upper()


def build_licence_data(
    *,
    licence_no: str,
    reference_no: str,
    form_data: dict[str, Any],
    holder_name: str,
    approved_by: str,
    issued_on: date,
    preview: bool = False,
) -> LicenceData:
    business = dict(form_data.get("business") or {})
    premises = dict(form_data.get("premises") or {})
    entity = str(business.get("entity_type") or "").replace("_", " ")
    valid_from, valid_to = validity(issued_on)
    return LicenceData(
        licence_no=licence_no,
        reference_no=reference_no,
        business_name=str(business.get("business_name") or ""),
        uen=str(business.get("uen") or ""),
        entity_type=entity.capitalize() if entity else "",
        premises_address=str(premises.get("address_line_1") or ""),
        postal_code=str(premises.get("postal_code") or ""),
        holder_name=holder_name,
        valid_from=valid_from,
        valid_to=valid_to,
        approved_by=approved_by,
        verification_code=verification_code(licence_no, reference_no, issued_on),
        preview=preview,
    )
