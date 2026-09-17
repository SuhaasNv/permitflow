"""Deterministic, dependency-free provider used in tests and when no API key is configured (AI-007).

Heuristics are documented in docs/ai/AI_VERIFICATION_DESIGN.md.
"""

import re
from datetime import date
from typing import Literal

from app.domain.enums import IssueCode
from app.domain.verification_rules import Issue, VerificationRequest, VerificationResult

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "business_profile": ("business profile", "acra", "uen", "registration"),
    "floor_plan": ("floor plan", "kitchen", "layout", "sqm", "square metres"),
    "tenancy_agreement": ("tenancy", "lease", "landlord", "tenant"),
    "food_hygiene_certificate": ("hygiene", "food safety", "certificate"),
}
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


class MockProvider:
    name = "mock"
    model: str | None = None

    def verify(self, request: VerificationRequest) -> VerificationResult:
        text = request.text
        lowered = text.lower()
        issues: list[Issue] = []
        missing: list[str] = []

        if not any(k in lowered for k in _KEYWORDS.get(request.document_type, ())):
            issues.append(
                Issue(
                    code=IssueCode.WRONG_DOCUMENT_TYPE,
                    severity="high",
                    message=f"This does not look like {_short(request.document_type_description)}.",
                    evidence=text[:80].strip() or None,
                )
            )

        if request.document_type == "business_profile":
            name = str(request.form_section.get("business_name") or "").lower()
            uen = str(request.form_section.get("uen") or "").lower()
            if name and name not in lowered and uen and uen not in lowered:
                issues.append(
                    Issue(
                        code=IssueCode.FIELD_MISMATCH,
                        severity="high",
                        message="Neither the business name nor the UEN from the form appears in the "
                        "document.",
                    )
                )
            if not uen and "uen" not in lowered:
                missing.append("UEN / registration number")

        if request.document_type == "tenancy_agreement":
            expiry = str(request.form_section.get("tenancy_expiry") or "")
            found = [m.group(0) for m in _DATE_RE.finditer(text)]
            if expiry and found and expiry not in found:
                issues.append(
                    Issue(
                        code=IssueCode.FIELD_MISMATCH,
                        severity="high",
                        message=f"The tenancy expiry in the document ({found[-1]}) differs from the form "
                        f"({expiry}).",
                        evidence=found[-1],
                    )
                )
            if not found:
                missing.append("tenancy expiry date")

        if "expired" in lowered or _has_past_expiry(text):
            issues.append(
                Issue(
                    code=IssueCode.EXPIRED_DOCUMENT,
                    severity="high",
                    message="The document appears to be expired.",
                )
            )

        if len(text) < 200:
            confidence = 0.4
        elif issues:
            confidence = 0.7
        else:
            confidence = 0.9
        status: Literal["issues_found", "verified"] = "issues_found" if issues else "verified"
        summary = (
            f"{len(issues)} issue(s) found in the {request.document_type.replace('_', ' ')}."
            if issues
            else f"The {request.document_type.replace('_', ' ')} is consistent with the form."
        )
        return VerificationResult(
            status=status, confidence=confidence, summary=summary, issues=issues, missing_information=missing
        )


def _short(description: str) -> str:
    return description.split(" showing")[0]


def _has_past_expiry(text: str) -> bool:
    m = re.search(r"expir(?:y|es|ed)[^0-9]{0,20}(\d{4})-(\d{2})-(\d{2})", text, re.IGNORECASE)
    if not m:
        return False
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) < date.today()
    except ValueError:
        return False
