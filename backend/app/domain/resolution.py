"""Resubmission rules (ADR-007, FR-011 to FR-013, FR-024). Pure: which flagged targets changed between the
current revision and the working copy, and which feedback items that makes `addressed`."""

from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import DocumentType, FeedbackTargetType


@dataclass(frozen=True)
class OpenTargets:
    sections: frozenset[str] = frozenset()
    document_types: frozenset[DocumentType] = frozenset()


@dataclass(frozen=True)
class Changes:
    sections: frozenset[str] = frozenset()
    document_types: frozenset[DocumentType] = frozenset()

    @property
    def any(self) -> bool:
        return bool(self.sections or self.document_types)


@dataclass(frozen=True)
class FeedbackTarget:
    id: str
    target_type: FeedbackTargetType
    section_key: str | None = None
    document_type: DocumentType | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def open_targets(items: list[FeedbackTarget]) -> OpenTargets:
    return OpenTargets(
        sections=frozenset(i.section_key for i in items if i.section_key),
        document_types=frozenset(i.document_type for i in items if i.document_type),
    )


def changed_targets(
    previous_form: dict[str, Any],
    current_form: dict[str, Any],
    previous_docs: dict[DocumentType, str],
    current_docs: dict[DocumentType, str],
    flagged: OpenTargets,
) -> Changes:
    """Sections compare by value; documents by sha256. Only flagged targets count (others cannot change)."""
    sections = frozenset(
        key for key in flagged.sections if (previous_form.get(key) or {}) != (current_form.get(key) or {})
    )
    documents = frozenset(
        dtype for dtype in flagged.document_types if previous_docs.get(dtype) != current_docs.get(dtype)
    )
    return Changes(sections=sections, document_types=documents)


def addressed_items(items: list[FeedbackTarget], changes: Changes) -> list[str]:
    """Ids of open items whose target changed in this resubmission (open → addressed)."""
    out: list[str] = []
    for item in items:
        if item.section_key and item.section_key in changes.sections:
            out.append(item.id)
        elif item.document_type and item.document_type in changes.document_types:
            out.append(item.id)
    return out
