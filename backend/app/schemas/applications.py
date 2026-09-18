"""Operator-facing application schemas. No internal status code, audit events or officer-only fields
appear here by construction (ADR-005, FR-026)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SectionView(BaseModel):
    key: str
    title: str
    description: str
    data: dict[str, Any]
    complete: bool
    started: bool
    errors: dict[str, str]
    editable: bool


class VerificationView(BaseModel):
    status: str
    summary: str | None
    issues: list[dict[str, Any]]
    missing_information: list[str]
    error_reason: str | None
    finished_at: datetime | None


class DocumentView(BaseModel):
    id: uuid.UUID
    document_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    replaces_filename: str | None
    verification: VerificationView | None


class DocumentSlotView(BaseModel):
    type: str
    label: str
    present: bool
    editable: bool
    document: DocumentView | None = None


class UploadOut(BaseModel):
    application: "ApplicationOperatorView"
    document: DocumentView
    unchanged: bool


class OperatorFeedbackView(BaseModel):
    """Released feedback only. No author name or internal fields: the operator sees the licensing office."""

    id: uuid.UUID
    target_type: str
    section_key: str | None
    document_type: str | None
    target_label: str
    message: str
    resolution: str
    round: int
    released_at: datetime
    addressed_in_revision: int | None


class ResubmitReadiness(BaseModel):
    can_resubmit: bool
    changed_sections: list[str]
    changed_document_types: list[str]
    # Open targets the operator has not changed yet.
    untouched_targets: list[str]
    reason: str | None


class RevisionSummaryView(BaseModel):
    number: int
    submitted_at: datetime


class CompletenessView(BaseModel):
    percent: int
    is_complete: bool
    sections_complete: int
    sections_total: int
    documents_present: int
    documents_total: int
    missing: list[str]


class ApplicationSummaryOut(BaseModel):
    id: uuid.UUID
    reference_no: str
    licence_title: str
    status_label: str
    status_tone: str
    business_name: str | None
    premises_summary: str | None
    percent: int
    revision_count: int
    # True when the licensing office is waiting on the operator (draft is not "waiting": it is theirs).
    needs_operator_action: bool
    created_at: datetime
    updated_at: datetime


class WithdrawIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class ApplicationOperatorView(BaseModel):
    id: uuid.UUID
    reference_no: str
    licence_title: str
    status_label: str
    status_tone: str
    status_explanation: str
    can_edit: bool
    can_submit: bool
    sections: list[SectionView]
    document_slots: list[DocumentSlotView]
    completeness: CompletenessView
    revision_count: int
    needs_operator_action: bool
    feedback: list[OperatorFeedbackView] = []
    resubmit: ResubmitReadiness | None = None
    revisions: list[RevisionSummaryView] = []
    # Officer's note shown with the final outcome only (Approved or Rejected).
    decision_note: str | None = None
    # Withdrawal (US-038): allowed after submission and before a decision; reason served once withdrawn.
    can_withdraw: bool = False
    # Drafts can be deleted outright (US-045).
    can_delete: bool = False
    withdrawal_reason: str | None = None
    created_at: datetime
    updated_at: datetime


UploadOut.model_rebuild()
