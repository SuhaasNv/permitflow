from app.domain.enums import IssueCode
from app.domain.verification_rules import VerificationRequest
from app.infra.ai.mock import MockProvider

FORM = {"business_name": "Kopi & Kaya Toast House Pte. Ltd.", "uen": "202312345K"}


def _req(dtype: str, text: str, section: dict[str, object] | None = None) -> VerificationRequest:
    return VerificationRequest(
        document_type=dtype,
        document_type_description="a test document",
        form_section=section or FORM,
        text=text,
    )


def test_valid_profile_is_verified() -> None:
    text = "ACRA Business Profile. Entity name: Kopi & Kaya Toast House Pte. Ltd. UEN: 202312345K. " * 4
    r = MockProvider().verify(_req("business_profile", text))
    assert r.status == "verified" and r.confidence == 0.9 and r.issues == []


def test_wrong_type_and_mismatch() -> None:
    text = "Lease agreement between landlord and tenant. Premises at 10 Jalan Besar. " * 4
    r = MockProvider().verify(_req("business_profile", text))
    codes = {i.code for i in r.issues}
    assert IssueCode.WRONG_DOCUMENT_TYPE in codes and IssueCode.FIELD_MISMATCH in codes
    assert r.status == "issues_found"


def test_short_text_low_confidence() -> None:
    r = MockProvider().verify(_req("floor_plan", "floor plan kitchen"))
    assert r.confidence == 0.4


def test_tenancy_expiry_mismatch() -> None:
    text = "Tenancy agreement. Term from 2024-11-01 to 2026-10-31. Landlord and tenant sign. " * 3
    r = MockProvider().verify(_req("tenancy_agreement", text, {"tenancy_expiry": "2027-10-31"}))
    assert any(i.code == IssueCode.FIELD_MISMATCH for i in r.issues)
