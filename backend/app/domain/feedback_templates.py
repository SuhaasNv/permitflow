"""Predefined officer comment templates (FR-018, US-024). Pure data; the officer edits before sending."""

from dataclasses import dataclass

from app.domain.enums import DocumentType, FeedbackTargetType


@dataclass(frozen=True)
class FeedbackTemplate:
    key: str
    title: str
    target_type: FeedbackTargetType
    # Suggested target when the template is picked; the officer can change it.
    section_key: str | None
    document_type: DocumentType | None
    message: str


TEMPLATES: tuple[FeedbackTemplate, ...] = (
    FeedbackTemplate(
        "address_mismatch",
        "Premises address does not match a document",
        FeedbackTargetType.SECTION,
        "premises",
        None,
        "The premises address in your application differs from the address shown in your supporting "
        "documents. Please confirm the correct address and update the application or the document so "
        "they match.",
    ),
    FeedbackTemplate(
        "uen_mismatch",
        "UEN does not match the business profile",
        FeedbackTargetType.SECTION,
        "business",
        None,
        "The UEN entered does not match the ACRA business profile you uploaded. Please enter the UEN "
        "exactly as it appears on the profile.",
    ),
    FeedbackTemplate(
        "certificate_expired",
        "Food hygiene certificate has expired",
        FeedbackTargetType.DOCUMENT,
        None,
        DocumentType.FOOD_HYGIENE_CERTIFICATE,
        "The food hygiene certificate you uploaded has expired. Please upload a certificate that is valid "
        "for the licence period.",
    ),
    FeedbackTemplate(
        "wrong_document",
        "Uploaded file is not the document requested",
        FeedbackTargetType.DOCUMENT,
        None,
        None,
        "The file uploaded for this document type appears to be a different document. Please upload the "
        "correct document.",
    ),
    FeedbackTemplate(
        "floor_plan_unclear",
        "Floor plan does not show the food preparation area",
        FeedbackTargetType.DOCUMENT,
        None,
        DocumentType.FLOOR_PLAN,
        "The floor plan does not clearly show the kitchen or food preparation area. Please upload a plan "
        "that marks the preparation, storage and washing areas.",
    ),
    FeedbackTemplate(
        "tenancy_period",
        "Tenancy does not cover the licence period",
        FeedbackTargetType.DOCUMENT,
        None,
        DocumentType.TENANCY_AGREEMENT,
        "The tenancy agreement ends before the licence period. Please upload an agreement or renewal "
        "that covers the full period.",
    ),
    FeedbackTemplate(
        "operations_detail",
        "Operations need more detail",
        FeedbackTargetType.SECTION,
        "operations",
        None,
        "Please describe the food you prepare and your operating hours in more detail so we can assess "
        "the premises requirements.",
    ),
)


def get_template(key: str) -> FeedbackTemplate | None:
    return next((t for t in TEMPLATES if t.key == key), None)
