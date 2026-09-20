"""Build the operator-facing view of an application from the aggregate."""

from app.domain import completeness as completeness_rules
from app.domain.enums import ApplicationStatus, DocumentType, SiteVisitStatus, VerificationStatus
from app.domain.form_schema import SECTIONS
from app.domain.labels import operator_label, tone_for
from app.domain.officer_actions import next_action
from app.domain.workflow import can_withdraw
from app.models import Application, Document, VerificationRun
from app.schemas.applications import (
    ApplicationOperatorView,
    ApplicationSummaryOut,
    CompletenessView,
    DocumentSlotView,
    DocumentView,
    LicenceView,
    OperatorFeedbackView,
    ResubmitReadiness,
    RevisionSummaryView,
    SectionView,
    VerificationView,
)
from app.schemas.clarification import ClarificationBlock
from app.schemas.site_visit import SiteVisitOperatorView
from app.schemas.storage import StorageView

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
    ApplicationStatus.SITE_VISIT_SCHEDULED: (
        "A site visit is being arranged. The date and slot are on this page once the officer proposes them."
    ),
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
    ApplicationStatus.WITHDRAWN: "You withdrew this application. It will not be reviewed further.",
}


def _needs_operator(status: ApplicationStatus, open_clarifications: int = 0) -> bool:
    # In the post-site operator-turn states the operator has something to do only while an item is
    # open (US-064): with nothing open the case is simply waiting on the office.
    if status in (
        ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION,
        ApplicationStatus.PENDING_POST_SITE_RESUBMISSION,
    ):
        return open_clarifications > 0
    action = next_action(status)
    return (
        status != ApplicationStatus.DRAFT
        and not action.officer_turn
        and status
        not in (
            ApplicationStatus.APPROVED,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        )
    )


def _present_types(app: Application, present: set[DocumentType] | None) -> set[DocumentType]:
    return present or set()


def summary(
    app: Application,
    *,
    present_types: set[DocumentType] | None = None,
    revision_count: int = 0,
    visit_awaits_operator: bool = False,
    open_clarifications: int = 0,
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
        needs_operator_action=_needs_operator(app.status, open_clarifications) or visit_awaits_operator,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


# Reasons an operator may see: the daily quota (so the slot can say why) and why their own file could not
# be read. Provider and infrastructure codes (`provider_not_configured`, `storage_error`, ...) describe our
# configuration, not their document, and are collapsed to `unavailable` (the officer sees the real code).
_OPERATOR_REASONS = frozenset({"daily_limit_reached", "interrupted"})


def _operator_reason(run: VerificationRun) -> str | None:
    if run.error_reason is None:
        return None
    if run.status == VerificationStatus.UNREADABLE or run.error_reason in _OPERATOR_REASONS:
        return run.error_reason
    return "unavailable"


def document_view(
    doc: Document, run: VerificationRun | None, replaces: Document | None = None
) -> DocumentView:
    verification = None
    if run is not None:
        # Operators see the outcome and a plain explanation; confidence is officer-only (design decision).
        verification = VerificationView(
            status=run.status.value,
            summary=run.summary,
            issues=[{k: v for k, v in i.items() if k != "evidence"} for i in run.issues],
            missing_information=list(run.missing_information),
            error_reason=_operator_reason(run),
            requested_at=run.created_at,
            finished_at=run.finished_at,
        )
    return DocumentView(
        id=doc.id,
        document_type=doc.document_type.value,
        original_filename=doc.original_filename,
        content_type=doc.content_type,
        size_bytes=doc.size_bytes,
        uploaded_at=doc.uploaded_at,
        replaces_filename=replaces.original_filename if replaces else None,
        verification=verification,
    )


_VISIT_EXPLANATIONS: dict[str, str] = {
    SiteVisitStatus.PROPOSED.value: (
        "The licensing officer proposed a site visit. Accept the date or propose another one."
    ),
    SiteVisitStatus.COUNTER_PROPOSED.value: (
        "You proposed another date for the site visit. The licensing officer decides next."
    ),
    SiteVisitStatus.CONFIRMED.value: (
        "Your site visit is confirmed. Nothing else is needed from you before the visit."
    ),
}


def _explanation(
    status: ApplicationStatus, site_visit: SiteVisitOperatorView | None, open_clarifications: int = 0
) -> str:
    """The status sentence, made specific to the appointment while one is being arranged (US-084) and
    to the number of items the officer flagged after the visit (US-063)."""
    if status == ApplicationStatus.SITE_VISIT_SCHEDULED and site_visit is not None:
        return _VISIT_EXPLANATIONS.get(site_visit.status, _EXPLANATIONS[status])
    if status == ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION:
        if open_clarifications:
            n = open_clarifications
            return (
                f"The licensing officer needs more information on {n} {'item' if n == 1 else 'items'} "
                "after the site visit. Answering arrives with the next update."
            )
        return "The site visit is recorded. The licensing office is finalising its assessment."
    return _EXPLANATIONS[status]


def operator_view(
    app: Application,
    *,
    documents: list[tuple[Document, VerificationRun | None]] | None = None,
    editable_sections: set[str] | None = None,
    editable_document_types: set[DocumentType] | None = None,
    revision_count: int = 0,
    feedback: list[OperatorFeedbackView] | None = None,
    resubmit: ResubmitReadiness | None = None,
    revisions: list[RevisionSummaryView] | None = None,
    licence: LicenceView | None = None,
    site_visit: SiteVisitOperatorView | None = None,
    open_clarifications: int = 0,
    clarification: ClarificationBlock | None = None,
    storage: StorageView | None = None,
) -> ApplicationOperatorView:
    documents = documents or []
    docs_by_type = {d.document_type: (d, r) for d, r in documents}
    comp = completeness_rules.compute(app.draft_data, set(docs_by_type))
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
    slots = []
    for d in comp.documents:
        pair = docs_by_type.get(d.type)
        slots.append(
            DocumentSlotView(
                type=d.type.value,
                label=d.label,
                present=d.present,
                editable=d.type in editable_document_types,
                document=document_view(pair[0], pair[1]) if pair else None,
            )
        )
    return ApplicationOperatorView(
        id=app.id,
        reference_no=app.reference_no,
        licence_title=LICENCE_TITLE,
        status_label=operator_label(app.status),
        status_tone=tone_for(app.status),
        status_explanation=_explanation(app.status, site_visit, open_clarifications),
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
        needs_operator_action=_needs_operator(app.status, open_clarifications)
        or (site_visit is not None and site_visit.status == SiteVisitStatus.PROPOSED.value),
        feedback=feedback or [],
        resubmit=resubmit,
        revisions=revisions or [],
        decision_note=(
            app.decision_note
            if app.status in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED)
            else None
        ),
        can_withdraw=can_withdraw(app.status),
        can_delete=app.status == ApplicationStatus.DRAFT,
        withdrawal_reason=app.withdrawal_reason if app.status == ApplicationStatus.WITHDRAWN else None,
        licence=licence,
        site_visit=site_visit,
        clarification=clarification,
        storage=storage,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )
