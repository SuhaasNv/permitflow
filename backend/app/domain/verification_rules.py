"""Deterministic rules around the AI verifier (AI-004, SEC-008). Pure Python."""

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.ai_prompt import leaks_prompt
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

    @model_validator(mode="after")
    def _status_matches_issues(self) -> "VerificationResult":
        """The status and the issue list must agree, whatever the model said: issues present means
        issues_found; issues_found with nothing listed is a verified document."""
        if self.status == "verified" and self.issues:
            self.status = "issues_found"
        elif self.status == "issues_found" and not self.issues:
            self.status = "verified"
        return self


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
    summary: str
    missing_information: list[str]


_LEAK_NOTICE = (
    "The document contains instructions aimed at the automatic check; a licensing officer will review it."
)


def _redact(text: str) -> str:
    return _LEAK_NOTICE if leaks_prompt(text) else text


def apply_rules(
    result: VerificationResult, *, confidence_threshold: float, injection_phrases: list[str]
) -> FinalOutcome:
    """Map the validated model output to the stored status (AI-004). Also the last point that sees the text
    shown to people: an answer that repeats the system prompt is replaced and flagged."""
    issues: list[dict[str, Any]] = [i.model_dump(mode="json") for i in result.issues]
    shown = [result.summary, *result.missing_information]
    shown += [t for i in issues for t in (i["message"], i["evidence"]) if t]
    if leaks_prompt(" ".join(shown)):
        summary = _redact(result.summary)
        missing = [_redact(m) for m in result.missing_information]
        for i in issues:
            i["message"] = _redact(i["message"])
            i["evidence"] = _redact(i["evidence"]) if i["evidence"] else None
        injection_phrases = injection_phrases or ["the answer repeated the checker's instructions"]
    else:
        summary, missing = result.summary, list(result.missing_information)
    # Injection first: a document that tells the checker to call itself unreadable must still reach a person.
    if injection_phrases:
        issues.append(
            {
                "code": IssueCode.POSSIBLE_PROMPT_INJECTION.value,
                "severity": "high",
                "message": "The document contains hidden characters or text that looks like instructions "
                "to the checker.",
                "evidence": injection_phrases[0][:300],
            }
        )
        return FinalOutcome(VerificationStatus.NEEDS_REVIEW, issues, summary, missing)
    if result.status == "unreadable":
        return FinalOutcome(VerificationStatus.UNREADABLE, issues, summary, missing)
    if result.status == "issues_found":
        return FinalOutcome(VerificationStatus.ISSUES_FOUND, issues, summary, missing)
    if result.confidence < confidence_threshold:
        return FinalOutcome(VerificationStatus.NEEDS_REVIEW, issues, summary, missing)
    return FinalOutcome(VerificationStatus.VERIFIED, issues, summary, missing)


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
