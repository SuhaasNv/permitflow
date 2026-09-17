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


class DocumentSlotView(BaseModel):
    type: str
    label: str
    present: bool
    editable: bool


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
