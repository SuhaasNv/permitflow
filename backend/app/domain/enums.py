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
