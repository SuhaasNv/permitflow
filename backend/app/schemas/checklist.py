"""The site visit checklist (US-060 to US-063) as the officer works on it and as the case summarises
it. Operators never receive these models (US-064 serves them a separate clarification view)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChecklistItemDefOut(BaseModel):
    key: str
    section: str
    title: str
    guidance: str
    applicable_by_default: bool


class ChecklistSectionOut(BaseModel):
    key: str
    title: str
    items: list[ChecklistItemDefOut]


class ChecklistSchemaOut(BaseModel):
    version: int
    description: str
    sections: list[ChecklistSectionOut]
    item_count: int


class ChecklistItemOut(BaseModel):
    id: uuid.UUID
    key: str
    section: str
    title: str
    guidance: str
    position: int
    result: str
    comment: str | None
    needs_clarification: bool
    clarification_status: str
    # Extra findings (US-092): the officer's own title, and the template item it sits under when linked.
    is_extra: bool = False
    custom_title: str | None = None
    parent_key: str | None = None


class ChecklistCounts(BaseModel):
    total: int
    assessed: int
    flagged: int
    unsatisfactory: int
    not_applicable: int
    # Unsatisfactory or flagged items without a comment: what still blocks a submit.
    missing_comments: int


class ChecklistOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    visit_no: int
    schema_version: int
    status: str
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime | None
    submitted_by: str | None
    submitted_at: datetime | None
    counts: ChecklistCounts
    # What stands between the draft and a submit, in a sentence; None when nothing does.
    remaining: str | None
    items: list[ChecklistItemOut]


class ChecklistSummaryOut(BaseModel):
    """The line the case rail shows (S-31 summary card)."""

    visit_no: int
    status: str
    version: int
    counts: ChecklistCounts
    updated_at: datetime | None
    submitted_at: datetime | None


class ChecklistItemIn(BaseModel):
    # None for a new extra finding: the server assigns its key and returns it (US-092).
    key: str | None = None
    result: str
    comment: str | None = Field(default=None, max_length=2000)
    needs_clarification: bool = False
    custom_title: str | None = Field(default=None, max_length=120)
    parent_key: str | None = Field(default=None, max_length=48)


class ChecklistSaveIn(BaseModel):
    items: list[ChecklistItemIn]
    version: int
    # Client-generated per save; a replayed one answers with the current state (US-061).
    save_id: str | None = Field(default=None, max_length=64)


__all__ = [
    "ChecklistCounts",
    "ChecklistItemDefOut",
    "ChecklistItemIn",
    "ChecklistItemOut",
    "ChecklistOut",
    "ChecklistSaveIn",
    "ChecklistSchemaOut",
    "ChecklistSectionOut",
    "ChecklistSummaryOut",
]
