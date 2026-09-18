"""Officer-facing schemas. These carry the internal status code, officer labels, confidence and evidence;
they are never served to operators (ADR-005)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
    finished_at: datetime | None


class OfficerDocumentOut(BaseModel):
    id: uuid.UUID
    document_type: str
    label: str
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    # True when this document was uploaded after the current revision was submitted (not part of it yet).
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


class OfficerApplicationOut(BaseModel):
    id: uuid.UUID
    reference_no: str
    licence_title: str
    status: str
    status_label: str
    status_tone: str
    applicant: ApplicantOut
    business_name: str | None
    premises_summary: str | None
    sections: list[OfficerSectionOut]
    documents: list[OfficerDocumentOut]
    missing_document_types: list[str]
    verification_summary: VerificationSummaryOut
    revisions: list[RevisionOut]
    current_revision_number: int
    actions: list[ActionOut]
    decision_note: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class TransitionIn(BaseModel):
    target: str
    note: str | None = Field(default=None, max_length=2000)
    expected_version: int
