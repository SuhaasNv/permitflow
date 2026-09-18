"""Revision comparison (FR-022, FR-023, ADR-007). Pure: field-level form diff, document add/remove/replace."""

from dataclasses import dataclass
from typing import Any

from app.domain.enums import DocumentType
from app.domain.form_schema import DOCUMENT_TYPE_LABELS, REQUIRED_DOCUMENT_TYPES, SECTIONS


@dataclass(frozen=True)
class FieldChange:
    key: str
    label: str
    old: Any
    new: Any


@dataclass(frozen=True)
class SectionDiff:
    key: str
    title: str
    changed: bool
    fields: list[FieldChange]


@dataclass(frozen=True)
class DocumentRef:
    id: str
    sha256: str
    filename: str


@dataclass(frozen=True)
class DocumentDiff:
    type: DocumentType
    label: str
    # unchanged | added | removed | replaced
    change: str
    old: DocumentRef | None
    new: DocumentRef | None


def diff_forms(previous: dict[str, Any], current: dict[str, Any]) -> list[SectionDiff]:
    """Compare every schema field; sections not in the schema are ignored."""
    out: list[SectionDiff] = []
    for section in SECTIONS:
        before = previous.get(section.key) or {}
        after = current.get(section.key) or {}
        fields = [
            FieldChange(key=f.key, label=f.label, old=before.get(f.key), new=after.get(f.key))
            for f in section.fields
            if before.get(f.key) != after.get(f.key)
        ]
        out.append(SectionDiff(key=section.key, title=section.title, changed=bool(fields), fields=fields))
    return out


def diff_documents(
    previous: dict[DocumentType, DocumentRef], current: dict[DocumentType, DocumentRef]
) -> list[DocumentDiff]:
    """Documents compare by sha256: a re-upload of identical bytes is unchanged."""
    out: list[DocumentDiff] = []
    for dtype in REQUIRED_DOCUMENT_TYPES:
        old = previous.get(dtype)
        new = current.get(dtype)
        if old is None and new is None:
            change = "unchanged"
        elif old is None:
            change = "added"
        elif new is None:
            change = "removed"
        elif old.sha256 != new.sha256:
            change = "replaced"
        else:
            change = "unchanged"
        out.append(
            DocumentDiff(type=dtype, label=DOCUMENT_TYPE_LABELS[dtype], change=change, old=old, new=new)
        )
    return out
