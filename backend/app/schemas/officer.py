"""Officer-facing schemas. These carry the internal status code, officer labels, confidence and evidence;
they are never served to operators (ADR-005)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.applications import LicenceView
from app.schemas.checklist import ChecklistSummaryOut
from app.schemas.clarification import ClarificationOfficerView
from app.schemas.site_visit import SiteVisitOut


class QueueItemOut(BaseModel):
    id: uuid.UUID
    reference_no: str
    licence_title: str
    business_name: str | None
    premises_summary: str | None
    applicant_name: str
    status: str
    status_label: str
    status_tone: str
    next_action: str
    officer_turn: bool
    decided: bool
    revision_count: int
    open_feedback_count: int
    # Current documents whose latest check needs a person: issues found, needs review, failed, unavailable.
    documents_attention: int
    documents_checking: int
    submitted_at: datetime | None
    last_activity_at: datetime


class QueueOut(BaseModel):
    items: list[QueueItemOut]
    officer_turn_count: int
    waiting_on_operator_count: int
    decided_count: int


class ApplicantOut(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str


class OfficerSectionOut(BaseModel):
    key: str
    title: str
    description: str
    # From the submitted revision, never from the operator's working copy.
    data: dict[str, Any]
    complete: bool


class OfficerVerificationOut(BaseModel):
    status: str
    summary: str | None
    confidence: float | None
    issues: list[dict[str, Any]]
    missing_information: list[str]
    error_reason: str | None
    provider: str
    model: str | None
    requested_at: datetime
    finished_at: datetime | None


class OfficerDocumentOut(BaseModel):
    id: uuid.UUID
    document_type: str
    label: str
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    # True when this document is part of the current submitted revision; False for a file the operator
    # uploaded since (a replacement during resubmission that has not been resubmitted yet).
    in_current_revision: bool
    verification: OfficerVerificationOut | None


class RevisionOut(BaseModel):
    id: uuid.UUID
    number: int
    submitted_at: datetime
    submitted_by: str


class ActionOut(BaseModel):
    target: str
    label: str
    enabled: bool
    reason: str | None
    # Reject requires a note; the UI asks for it before calling the transition endpoint.
    requires_note: bool


class VerificationSummaryOut(BaseModel):
    total: int
    verified: int
    issues_found: int
    needs_review: int
    checking: int
    other: int


class FeedbackOut(BaseModel):
    id: uuid.UUID
    target_type: str
    section_key: str | None
    document_type: str | None
    target_label: str
    message: str
    template_key: str | None
    resolution: str
    # Revision number the item was raised against (the "round").
    raised_in_revision: int
    author_name: str
    created_at: datetime
    released_to_operator_at: datetime | None
    addressed_in_revision: int | None
    resolved_at: datetime | None
    # True while the calling officer can undo their own withdraw or resolve (US-039).
    can_undo: bool = False
    # True while this item can be marked resolved: open or addressed, released, and the case with the
    # office (US-083); the screen no longer recomputes the rule from the status.
    can_resolve: bool = False


class FeedbackIn(BaseModel):
    target_type: str
    section_key: str | None = None
    document_type: str | None = None
    message: str = Field(max_length=2000)
    template_key: str | None = None


class FeedbackTemplateOut(BaseModel):
    key: str
    title: str
    target_type: str
    section_key: str | None
    document_type: str | None
    message: str


class EarlierVisitOfficerOut(BaseModel):
    """A visit before the active one (UAT run 5, F17 and F18): its appointment, its checklist summary
    (readable at /checklist?visit=N) and its clarification threads, read-only."""

    visit_no: int
    site_visit: SiteVisitOut | None = None
    checklist: ChecklistSummaryOut | None = None
    clarification: ClarificationOfficerView | None = None


class OfficerApplicationOut(BaseModel):
    id: uuid.UUID
    reference_no: str
    licence_title: str
    status: str
    status_label: str
    status_tone: str
    # US-083: the stage (draft, pre_site, site_visit, post_site, decision, decided) and how it ended
    # (approved, rejected, withdrawn, or null); the screens branch on these, never on label strings.
    phase: str
    outcome: str | None
    applicant: ApplicantOut
    business_name: str | None
    premises_summary: str | None
    sections: list[OfficerSectionOut]
    documents: list[OfficerDocumentOut]
    missing_document_types: list[str]
    verification_summary: VerificationSummaryOut
    revisions: list[RevisionOut]
    current_revision_number: int
    previous_revision_number: int | None
    changed_sections: list[str]
    changed_document_types: list[str]
    # Addressed items the officer has not resolved yet (warning before moving on).
    addressed_unresolved_count: int
    feedback: list[FeedbackOut]
    open_feedback_count: int
    # Feedback can be created or withdrawn only while under review; the reason explains why not.
    feedback_editable: bool
    feedback_locked_reason: str | None
    actions: list[ActionOut]
    decision_note: str | None
    # Operator's reason when they withdrew (US-038).
    withdrawal_reason: str | None
    # The site visit appointment (US-084): present once a date was proposed for the current visit.
    site_visit: SiteVisitOut | None = None
    # The current visit's checklist (US-060): present once the officer opened it.
    checklist: ChecklistSummaryOut | None = None
    # The clarification threads once the checklist is submitted (US-066).
    clarification: ClarificationOfficerView | None = None
    # Earlier visits, latest first, read-only (the active visit is the fields above).
    earlier_visits: list[EarlierVisitOfficerOut] = []
    licence: LicenceView | None = None
    version: int
    created_at: datetime
    updated_at: datetime


class TransitionIn(BaseModel):
    target: str
    # Stored as the decision note for `approved` and `rejected` (required for reject); ignored otherwise.
    note: str | None = Field(default=None, max_length=2000)
    expected_version: int


class AuditEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    summary: str
    actor_name: str | None
    actor_role: str | None
    payload: dict[str, Any]
    created_at: datetime


class AuditTrailOut(BaseModel):
    application_id: uuid.UUID
    events: list[AuditEventOut]
