"""Officer-facing schemas. These carry the internal status code and officer labels; they are never served
to operators (ADR-005)."""

import uuid
from datetime import datetime

from pydantic import BaseModel


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
