"""Which sections and document types an operator may change in a given state (STATE_MACHINE.md)."""

from app.domain.enums import ApplicationStatus, DocumentType
from app.domain.form_schema import REQUIRED_DOCUMENT_TYPES, SECTION_KEYS


def editable_targets(
    status: ApplicationStatus,
    open_feedback_sections: set[str],
    open_feedback_document_types: set[DocumentType],
) -> tuple[set[str], set[DocumentType]]:
    if status == ApplicationStatus.DRAFT:
        return set(SECTION_KEYS), set(REQUIRED_DOCUMENT_TYPES)
    if status == ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
        return set(open_feedback_sections), set(open_feedback_document_types)
    return set(), set()
