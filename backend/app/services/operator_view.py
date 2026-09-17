"""Build the operator-facing view of an application from the aggregate."""

from app.api.v1.applications_schemas import (
    ApplicationOperatorView,
    ApplicationSummaryOut,
    CompletenessView,
    DocumentSlotView,
    SectionView,
)
from app.domain import completeness as completeness_rules
from app.domain.enums import ApplicationStatus, DocumentType
from app.domain.form_schema import SECTIONS
from app.domain.labels import operator_label, tone_for
from app.models import Application

LICENCE_TITLE = "Food Establishment Licence"

_EXPLANATIONS: dict[ApplicationStatus, str] = {
    ApplicationStatus.DRAFT: "Not yet submitted. You can save and return any time.",
    ApplicationStatus.APPLICATION_RECEIVED: (
        "Received by the licensing office. You will be notified when the review starts."
    ),
    ApplicationStatus.UNDER_REVIEW: (
        "A licensing officer is reviewing your application. Nothing is needed from you."
    ),
    ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION: (
        "The licensing office has asked for changes. Update the flagged items and resubmit."
    ),
    ApplicationStatus.PRE_SITE_RESUBMITTED: (
        "Your changes were sent to the licensing office. You will be notified when the review continues."
    ),
    ApplicationStatus.SITE_VISIT_SCHEDULED: "An officer will contact you to arrange a visit to the premises.",
    ApplicationStatus.SITE_VISIT_DONE: (
        "The site visit is complete. The licensing office is finalising its assessment."
    ),
    ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION: (
        "The licensing office is finalising its assessment after the site visit."
    ),
    ApplicationStatus.PENDING_POST_SITE_RESUBMISSION: (
        "The licensing office has asked for clarification after the site visit."
    ),
    ApplicationStatus.POST_SITE_CLARIFICATION_RESUBMITTED: (
        "Your clarification was sent to the licensing office."
    ),
    ApplicationStatus.PENDING_APPROVAL: "Your application is with the licensing office for a decision.",
    ApplicationStatus.APPROVED: "Your licence application has been approved.",
    ApplicationStatus.REJECTED: "Your licence application was not approved. See the officer's note.",
}


def _present_types(app: Application, present: set[DocumentType] | None) -> set[DocumentType]:
    return present or set()


def summary(
    app: Application, *, present_types: set[DocumentType] | None = None, revision_count: int = 0
) -> ApplicationSummaryOut:
    comp = completeness_rules.compute(app.draft_data, _present_types(app, present_types))
    business = (app.draft_data.get("business") or {}).get("business_name")
    premises = (app.draft_data.get("premises") or {}).get("address_line_1")
    return ApplicationSummaryOut(
        id=app.id,
        reference_no=app.reference_no,
        licence_title=LICENCE_TITLE,
        status_label=operator_label(app.status),
        status_tone=tone_for(app.status),
        business_name=business if isinstance(business, str) and business else None,
        premises_summary=premises if isinstance(premises, str) and premises else None,
        percent=comp.percent,
        revision_count=revision_count,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def operator_view(
    app: Application,
    *,
    present_types: set[DocumentType] | None = None,
    editable_sections: set[str] | None = None,
    editable_document_types: set[DocumentType] | None = None,
    revision_count: int = 0,
) -> ApplicationOperatorView:
    comp = completeness_rules.compute(app.draft_data, _present_types(app, present_types))
    editable_sections = editable_sections or set()
    editable_document_types = editable_document_types or set()
    sections = [
        SectionView(
            key=s.key,
            title=s.title,
            description=s.description,
            data=dict(app.draft_data.get(s.key) or {}),
            complete=state.complete,
            started=state.started,
            errors=state.errors,
            editable=s.key in editable_sections,
        )
        for s, state in zip(SECTIONS, comp.sections, strict=True)
    ]
    slots = [
        DocumentSlotView(
            type=d.type.value, label=d.label, present=d.present, editable=d.type in editable_document_types
        )
        for d in comp.documents
    ]
    return ApplicationOperatorView(
        id=app.id,
        reference_no=app.reference_no,
        licence_title=LICENCE_TITLE,
        status_label=operator_label(app.status),
        status_tone=tone_for(app.status),
        status_explanation=_EXPLANATIONS[app.status],
        can_edit=bool(editable_sections or editable_document_types),
        can_submit=app.status == ApplicationStatus.DRAFT and comp.is_complete,
        sections=sections,
        document_slots=slots,
        completeness=CompletenessView(
            percent=comp.percent,
            is_complete=comp.is_complete,
            sections_complete=sum(1 for s in comp.sections if s.complete),
            sections_total=len(comp.sections),
            documents_present=sum(1 for d in comp.documents if d.present),
            documents_total=len(comp.documents),
            missing=list(comp.missing),
        ),
        revision_count=revision_count,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )
