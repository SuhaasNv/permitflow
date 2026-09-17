"""Completion rules shared by the progress indicator and the submit guard (FR-006, FR-007)."""

from dataclasses import dataclass
from typing import Any

from app.domain.enums import DocumentType
from app.domain.form_schema import (
    DOCUMENT_TYPE_LABELS,
    REQUIRED_DOCUMENT_TYPES,
    SECTIONS,
    validate_section,
)


@dataclass(frozen=True)
class SectionState:
    key: str
    title: str
    complete: bool
    started: bool
    errors: dict[str, str]


@dataclass(frozen=True)
class DocumentSlotState:
    type: DocumentType
    label: str
    present: bool


@dataclass(frozen=True)
class Completeness:
    sections: tuple[SectionState, ...]
    documents: tuple[DocumentSlotState, ...]
    percent: int
    is_complete: bool
    missing: tuple[str, ...]  # human-readable list of what is still needed


def compute(draft_data: dict[str, Any], present_document_types: set[DocumentType]) -> Completeness:
    sections: list[SectionState] = []
    for s in SECTIONS:
        data = draft_data.get(s.key) or {}
        errors = validate_section(s.key, data) if data else {}
        started = bool(data)
        complete = started and not errors
        sections.append(SectionState(s.key, s.title, complete, started, errors))
    documents = tuple(
        DocumentSlotState(t, DOCUMENT_TYPE_LABELS[t], t in present_document_types)
        for t in REQUIRED_DOCUMENT_TYPES
    )
    total = len(sections) + len(documents)
    done = sum(1 for s in sections if s.complete) + sum(1 for d in documents if d.present)
    missing = [f"Section: {s.title}" for s in sections if not s.complete] + [
        f"Document: {d.label}" for d in documents if not d.present
    ]
    return Completeness(
        sections=tuple(sections),
        documents=documents,
        percent=int(round(100 * done / total)) if total else 0,
        is_complete=done == total,
        missing=tuple(missing),
    )
