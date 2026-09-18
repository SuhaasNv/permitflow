"""Deterministic rules around the AI verifier (AI-004, SEC-008). Pure Python."""

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import IssueCode, VerificationStatus

# ---------- provider contract ----------


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: IssueCode
    severity: Literal["low", "medium", "high"]
    message: str = Field(min_length=1, max_length=500)
    evidence: str | None = Field(default=None, max_length=300)


class VerificationResult(BaseModel):
    """Domain model: strict. Anything the provider returns is validated into this (AI-003)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["verified", "issues_found", "unreadable"]
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=2000)
    issues: list[Issue] = Field(default_factory=list, max_length=20)
    missing_information: list[str] = Field(default_factory=list, max_length=20)


@dataclass(frozen=True)
class VerificationRequest:
    document_type: str
    document_type_description: str
    form_section: dict[str, Any]
    text: str
    extra: dict[str, Any] = field(default_factory=dict)


# ---------- prompt-injection heuristic ----------

_INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"disregard (the|all|any) (previous|prior|above)",
    r"mark (this|the document) as (verified|approved|valid)",
    r"you are now",
    r"system prompt",
    r"respond with (only )?(\"|')?verified",
    r"set (the )?(status|confidence) to",
    r"approve this (application|document)",
]
_INJECTION_RE = re.compile("|".join(f"({p})" for p in _INJECTION_PATTERNS), re.IGNORECASE)


def find_injection_phrases(text: str) -> list[str]:
    return [m.group(0) for m in _INJECTION_RE.finditer(text)][:5]


# ---------- post-processing ----------


@dataclass(frozen=True)
class FinalOutcome:
    status: VerificationStatus
    issues: list[dict[str, Any]]


def apply_rules(
    result: VerificationResult, *, confidence_threshold: float, injection_phrases: list[str]
) -> FinalOutcome:
    """Map the validated model output to the stored status (AI-004)."""
    issues: list[dict[str, Any]] = [i.model_dump(mode="json") for i in result.issues]
    # Injection first: a document that tells the checker to call itself unreadable must still reach a person.
    if injection_phrases:
        issues.append(
            {
                "code": IssueCode.POSSIBLE_PROMPT_INJECTION.value,
                "severity": "high",
                "message": "The document contains text that looks like instructions to the checker.",
                "evidence": injection_phrases[0][:300],
            }
        )
        return FinalOutcome(VerificationStatus.NEEDS_REVIEW, issues)
    if result.status == "unreadable":
        return FinalOutcome(VerificationStatus.UNREADABLE, issues)
    if result.status == "issues_found":
        return FinalOutcome(VerificationStatus.ISSUES_FOUND, issues)
    if result.confidence < confidence_threshold:
        return FinalOutcome(VerificationStatus.NEEDS_REVIEW, issues)
    return FinalOutcome(VerificationStatus.VERIFIED, issues)


DOCUMENT_TYPE_DESCRIPTIONS: dict[str, str] = {
    "business_profile": "a company or business registration profile (ACRA business profile) showing the "
    "business name, UEN / registration number and the date it was issued",
    "floor_plan": "a floor plan of the premises showing the kitchen or food preparation area and the unit "
    "or address",
    "tenancy_agreement": "a tenancy or lease agreement for the premises showing the address, the term with "
    "its expiry date, and signatures",
    "food_hygiene_certificate": "a food hygiene or food safety certificate in the name of the business or a "
    "food handler, with an issue or expiry date",
}

# Which form section is relevant to each document type (THREAT_MODEL T18: send only what is needed).
SECTION_FOR_DOCUMENT: dict[str, str] = {
    "business_profile": "business",
    "floor_plan": "premises",
    "tenancy_agreement": "premises",
    "food_hygiene_certificate": "business",
}
