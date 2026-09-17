"""Operator-facing application schemas. No internal status code, audit events or officer-only fields
appear here by construction (ADR-005, FR-026)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
    created_at: datetime
    updated_at: datetime


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
    created_at: datetime
    updated_at: datetime


UploadOut.model_rebuild()
