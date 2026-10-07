"""Enumerations are defined in the pure domain layer; re-exported here for the persistence layer."""

from app.domain.enums import (
    ApplicationStatus,
    ChecklistResult,
    ChecklistStatus,
    ClarificationStatus,
    DocumentType,
    FeedbackResolution,
    FeedbackTargetType,
    IssueCode,
    LicenceType,
    NotificationKind,
    Role,
    SiteVisitProposalOutcome,
    SiteVisitSlot,
    SiteVisitStatus,
    VerificationStatus,
)

__all__ = [
    "ApplicationStatus",
    "DocumentType",
    "FeedbackResolution",
    "FeedbackTargetType",
    "IssueCode",
    "LicenceType",
    "NotificationKind",
    "Role",
    "ChecklistResult",
    "ChecklistStatus",
    "ClarificationStatus",
    "SiteVisitProposalOutcome",
    "SiteVisitSlot",
    "SiteVisitStatus",
    "VerificationStatus",
]
