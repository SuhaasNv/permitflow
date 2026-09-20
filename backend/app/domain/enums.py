"""Enumerations shared by models and API schemas. String values are stable API contracts."""

import enum


class Role(enum.StrEnum):
    OPERATOR = "operator"
    OFFICER = "officer"
    ADMIN = "admin"


class LicenceType(enum.StrEnum):
    FOOD_ESTABLISHMENT = "food_establishment"


class ApplicationStatus(enum.StrEnum):
    DRAFT = "draft"
    APPLICATION_RECEIVED = "application_received"
    UNDER_REVIEW = "under_review"
    PENDING_PRE_SITE_RESUBMISSION = "pending_pre_site_resubmission"
    PRE_SITE_RESUBMITTED = "pre_site_resubmitted"
    SITE_VISIT_SCHEDULED = "site_visit_scheduled"
    SITE_VISIT_DONE = "site_visit_done"
    AWAITING_POST_SITE_CLARIFICATION = "awaiting_post_site_clarification"
    PENDING_POST_SITE_RESUBMISSION = "pending_post_site_resubmission"
    POST_SITE_CLARIFICATION_RESUBMITTED = "post_site_clarification_resubmitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class DocumentType(enum.StrEnum):
    BUSINESS_PROFILE = "business_profile"
    FLOOR_PLAN = "floor_plan"
    TENANCY_AGREEMENT = "tenancy_agreement"
    FOOD_HYGIENE_CERTIFICATE = "food_hygiene_certificate"


class VerificationStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    VERIFIED = "verified"
    ISSUES_FOUND = "issues_found"
    NEEDS_REVIEW = "needs_review"
    UNREADABLE = "unreadable"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class IssueCode(enum.StrEnum):
    WRONG_DOCUMENT_TYPE = "wrong_document_type"
    MISSING_FIELD = "missing_field"
    FIELD_MISMATCH = "field_mismatch"
    EXPIRED_DOCUMENT = "expired_document"
    ILLEGIBLE_CONTENT = "illegible_content"
    POSSIBLE_PROMPT_INJECTION = "possible_prompt_injection"
    OTHER = "other"


class FeedbackTargetType(enum.StrEnum):
    SECTION = "section"
    DOCUMENT = "document"


class FeedbackResolution(enum.StrEnum):
    OPEN = "open"
    ADDRESSED = "addressed"
    RESOLVED = "resolved"
    WITHDRAWN = "withdrawn"


class NotificationKind(enum.StrEnum):
    SUBMITTED = "submitted"
    RESUBMITTED = "resubmitted"
    STATUS_CHANGED = "status_changed"


class SiteVisitStatus(enum.StrEnum):
    """The appointment inside Site Visit Scheduled (US-084): who it waits on, or that it is fixed."""

    PROPOSED = "proposed"  # waiting on the operator
    COUNTER_PROPOSED = "counter_proposed"  # waiting on the officer
    CONFIRMED = "confirmed"
    DONE = "done"


class SiteVisitSlot(enum.StrEnum):
    MORNING = "morning"  # 09:00 to 12:00
    AFTERNOON = "afternoon"  # 14:00 to 17:00


class SiteVisitProposalOutcome(enum.StrEnum):
    PENDING = "pending"  # waiting for the other side
    ACCEPTED = "accepted"  # became the confirmed date
    KEPT = "kept"  # the officer kept this date over the operator's counter-proposal
    DECLINED = "declined"  # the other side chose a different date
    SUPERSEDED = "superseded"  # replaced by a later proposal from the same side


class ChecklistStatus(enum.StrEnum):
    """The site visit checklist (US-060): a draft while the officer works, submitted once frozen."""

    DRAFT = "draft"
    SUBMITTED = "submitted"


class ChecklistResult(enum.StrEnum):
    NOT_ASSESSED = "not_assessed"
    SATISFACTORY = "satisfactory"
    UNSATISFACTORY = "unsatisfactory"
    NOT_APPLICABLE = "not_applicable"


class ClarificationStatus(enum.StrEnum):
    """An item's clarification thread (US-062 to US-066): none until flagged and submitted."""

    NONE = "none"
    OPEN = "open"
    ANSWERED = "answered"
    RESOLVED = "resolved"
    WITHDRAWN = "withdrawn"
