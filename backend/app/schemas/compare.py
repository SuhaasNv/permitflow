"""Revision compare schemas (FR-022)."""

import uuid
from typing import Any

from pydantic import BaseModel


class FieldChangeOut(BaseModel):
    key: str
    label: str
    old: Any
    new: Any


class SectionDiffOut(BaseModel):
    key: str
    title: str
    changed: bool
    fields: list[FieldChangeOut]


class DocumentRefOut(BaseModel):
    id: uuid.UUID
    filename: str


class DocumentDiffOut(BaseModel):
    type: str
    label: str
    change: str
    old: DocumentRefOut | None
    new: DocumentRefOut | None


class CompareOut(BaseModel):
    application_id: uuid.UUID
    from_revision: int
    to_revision: int
    sections: list[SectionDiffOut]
    documents: list[DocumentDiffOut]
    changed_section_count: int
    changed_document_count: int
