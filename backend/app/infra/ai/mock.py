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
# "3 January 2025", "31 Oct 2027": the way the demo documents and most scanned paperwork write dates.
_LONG_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})\b", re.IGNORECASE
)
_MONTH_NAMES = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
_MONTHS = {m: i for i, m in enumerate(_MONTH_NAMES, 1)}
_EXPIRY_WORDS = re.compile(r"(expir(?:y|es|ed|ation)|valid (?:until|till|to|through))", re.IGNORECASE)


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
            if not found and not _LONG_DATE_RE.search(text):
                missing.append("tenancy expiry date")
                issues.append(
                    Issue(
                        code=IssueCode.MISSING_FIELD,
                        severity="medium",
                        message="No tenancy term or expiry date could be found in the document.",
                    )
                )

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
    """A date that follows an expiry phrase ("expiry", "valid until") and lies in the past."""
    for m in _EXPIRY_WORDS.finditer(text):
        window = text[m.end() : m.end() + 40]
        found = _parse_date(window)
        if found is not None:
            return found < date.today()
    return False


def _parse_date(text: str) -> date | None:
    iso = _DATE_RE.search(text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    long = _LONG_DATE_RE.search(text)
    if long:
        try:
            return date(int(long.group(3)), _MONTHS[long.group(2).lower()[:3]], int(long.group(1)))
        except (ValueError, KeyError):
            return None
    return None
