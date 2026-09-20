"""The clarification rounds as the operator sees them (US-064): only items with a released request,
never a result, an unflagged item or an unreleased question. A separate model from the officer's
checklist, so what the operator receives is decided by the schema, not filtered at runtime (ADR-005)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ClarificationRequestOut(BaseModel):
    id: uuid.UUID
    round_no: int
    message: str
    released_at: datetime


class ClarificationResponseOut(BaseModel):
    """The operator's own answer (US-065); listed here so the shape is fixed from the first release."""

    id: uuid.UUID
    round_no: int
    message: str
    created_at: datetime
    sent_at: datetime | None
    attachments: list["ClarificationAttachmentOut"]


class ClarificationAttachmentOut(BaseModel):
    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


class ClarificationItemOut(BaseModel):
    item_id: uuid.UUID
    key: str
    title: str
    guidance: str
    # Operator words only: Waiting for your response, Sent, Clarified, No longer needed.
    status: str
    round_no: int
    requests: list[ClarificationRequestOut]
    responses: list[ClarificationResponseOut]
    # True while a released request of the current round has no response yet.
    can_respond: bool


class ClarificationOperatorView(BaseModel):
    application_id: uuid.UUID
    visit_no: int | None
    items: list[ClarificationItemOut]
    open_count: int
    answered_count: int
    resolved_count: int
    # The highest round on any item; what "Round 2" means on the page.
    round: int
    can_respond: bool
    can_send: bool


class ClarificationResponseIn(BaseModel):
    message: str = Field(max_length=2000)


class ClarificationAttachOut(BaseModel):
    view: ClarificationOperatorView
    # An identical file on the same answer is kept once and reported as no change (SEC-005).
    unchanged: bool


class ClarificationBlock(BaseModel):
    """The block on the operator's application view: what to show and whether to act."""

    can_respond: bool
    open_count: int
    answered_count: int
    round: int


__all__ = [
    "ClarificationAttachOut",
    "ClarificationAttachmentOut",
    "ClarificationBlock",
    "ClarificationItemOut",
    "ClarificationOperatorView",
    "ClarificationRequestOut",
    "ClarificationResponseIn",
    "ClarificationResponseOut",
]
