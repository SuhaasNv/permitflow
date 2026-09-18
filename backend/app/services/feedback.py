"""Officer feedback (FR-018, FR-010, AUD-003). Items are created and withdrawn only while the application is
`under_review`; requesting a resubmission freezes and releases them (STATE_MACHINE.md, feedback lifecycle)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.domain.enums import ApplicationStatus, DocumentType, FeedbackResolution, FeedbackTargetType
from app.domain.feedback_templates import get_template
from app.domain.form_schema import DOCUMENT_TYPE_LABELS, get_section
from app.models import Feedback, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.feedback import FeedbackRepository
from app.repositories.revisions import RevisionRepository

MAX_MESSAGE = 2000
# The UI offers Undo for 10 s; the server accepts a little longer to absorb latency.
UNDO_WINDOW = timedelta(seconds=15)

_RESOLVABLE_STATES = {
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.PRE_SITE_RESUBMITTED,
    ApplicationStatus.SITE_VISIT_SCHEDULED,
    ApplicationStatus.SITE_VISIT_DONE,
    ApplicationStatus.PENDING_APPROVAL,
}


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.feedback = FeedbackRepository(db)
        self.revisions = RevisionRepository(db)
        self.audit = AuditRepository(db)

    def create(
        self,
        officer: User,
        application_id: uuid.UUID,
        *,
        target_type: str,
        section_key: str | None,
        document_type: str | None,
        message: str,
        template_key: str | None,
    ) -> Feedback:
        fields: dict[str, str] = {}
        try:
            ttype = FeedbackTargetType(target_type)
        except ValueError:
            fields["target_type"] = "Choose a section or a document."
            raise ValidationFailed("Some fields need attention.", details={"fields": fields}) from None
        dtype: DocumentType | None = None
        if ttype == FeedbackTargetType.SECTION:
            if not section_key or get_section(section_key) is None:
                fields["section_key"] = "Choose one of the form sections."
            document_type = None
        else:
            try:
                dtype = DocumentType(document_type or "")
            except ValueError:
                fields["document_type"] = "Choose one of the required document types."
            section_key = None
        message = message.strip()
        if not message:
            fields["message"] = "Write the feedback the operator will read."
        elif len(message) > MAX_MESSAGE:
            fields["message"] = f"Keep the feedback under {MAX_MESSAGE} characters."
        if template_key and get_template(template_key) is None:
            fields["template_key"] = "Unknown template."
        if fields:
            raise ValidationFailed("Some fields need attention.", details={"fields": fields})

        app = self.applications.get_for(officer, application_id, for_update=True)
        if app.status != ApplicationStatus.UNDER_REVIEW:
            raise Conflict("Feedback can be added only while the application is Under Review.")
        current = self.revisions.list_for(app.id)[-1:]
        if not current:
            raise Conflict("This application has no submitted revision.")
        item = Feedback(
            application_id=app.id,
            raised_in_revision_id=current[0].id,
            author_id=officer.id,
            target_type=ttype,
            section_key=section_key,
            document_type=dtype,
            template_key=template_key,
            message=message,
            resolution=FeedbackResolution.OPEN,
        )
        self.feedback.add(item)
        self.db.flush()
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="feedback.created",
            payload={
                "feedback_id": str(item.id),
                "target": target_label(item),
                "template_key": template_key,
            },
        )
        app.version += 1
        self.db.commit()
        self.db.refresh(item)
        return item

    def withdraw(self, officer: User, application_id: uuid.UUID, feedback_id: uuid.UUID) -> Feedback:
        app = self.applications.get_for(officer, application_id, for_update=True)
        item = self.feedback.get_in_application(app.id, feedback_id)
        if item is None:
            raise NotFound("Feedback not found.")
        if app.status != ApplicationStatus.UNDER_REVIEW:
            raise Conflict("Feedback can be withdrawn only while the application is Under Review.")
        if item.resolution != FeedbackResolution.OPEN:
            raise Conflict("Only open feedback can be withdrawn.")
        item.previous_resolution = item.resolution
        item.resolution = FeedbackResolution.WITHDRAWN
        item.resolved_by = officer.id
        item.resolved_at = datetime.now(UTC)
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="feedback.withdrawn",
            payload={"feedback_id": str(item.id), "target": target_label(item)},
        )
        app.version += 1
        self.db.commit()
        self.db.refresh(item)
        return item

    def reopen(self, officer: User, application_id: uuid.UUID, feedback_id: uuid.UUID) -> Feedback:
        """Not fixed (US-049): addressed → open with the same text, as a draft for the next round.

        Only while Under Review, like create and withdraw. The item leaves the operator's view until the
        officer requests the next resubmission (release), which keeps the freeze rule intact.
        """
        app = self.applications.get_for(officer, application_id, for_update=True)
        item = self.feedback.get_in_application(app.id, feedback_id)
        if item is None:
            raise NotFound("Feedback not found.")
        if app.status != ApplicationStatus.UNDER_REVIEW:
            raise Conflict("Feedback can be reopened only while the application is Under Review.")
        if item.resolution != FeedbackResolution.ADDRESSED:
            raise Conflict("Only an addressed item can be marked as not fixed.")
        item.previous_resolution = item.resolution
        item.resolution = FeedbackResolution.OPEN
        item.released_to_operator_at = None
        item.resolved_by = officer.id
        item.resolved_at = datetime.now(UTC)
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="feedback.reopened",
            payload={"feedback_id": str(item.id), "target": target_label(item)},
        )
        app.version += 1
        self.db.commit()
        self.db.refresh(item)
        return item

    def resolve(self, officer: User, application_id: uuid.UUID, feedback_id: uuid.UUID) -> Feedback:
        """open or addressed → resolved, by officer action, while the application is with the officer."""
        app = self.applications.get_for(officer, application_id, for_update=True)
        item = self.feedback.get_in_application(app.id, feedback_id)
        if item is None:
            raise NotFound("Feedback not found.")
        if app.status not in _RESOLVABLE_STATES:
            raise Conflict(
                "Feedback can be resolved only while the application is with the licensing office."
            )
        if item.resolution not in (FeedbackResolution.OPEN, FeedbackResolution.ADDRESSED):
            raise Conflict("Only open or addressed feedback can be resolved.")
        if item.released_to_operator_at is None:
            raise Conflict(
                "This item was never sent to the operator, so there is nothing to resolve. "
                "Withdraw it instead."
            )
        item.previous_resolution = item.resolution
        item.resolution = FeedbackResolution.RESOLVED
        item.resolved_by = officer.id
        item.resolved_at = datetime.now(UTC)
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="feedback.resolved",
            payload={"feedback_id": str(item.id), "target": target_label(item)},
        )
        app.version += 1
        self.db.commit()
        self.db.refresh(item)
        return item

    def restore(self, officer: User, application_id: uuid.UUID, feedback_id: uuid.UUID) -> Feedback:
        """Undo the officer's own withdraw or resolve within `UNDO_WINDOW` (US-039). Audited."""
        app = self.applications.get_for(officer, application_id, for_update=True)
        item = self.feedback.get_in_application(app.id, feedback_id)
        if item is None:
            raise NotFound("Feedback not found.")
        if not restorable(item, app.status, officer.id, datetime.now(UTC)):
            raise Conflict("This decision can no longer be undone.")
        previous = item.previous_resolution
        assert previous is not None  # guaranteed by restorable()
        undone = item.resolution
        item.resolution = previous
        item.previous_resolution = None
        if undone == FeedbackResolution.OPEN and previous == FeedbackResolution.ADDRESSED:
            # Undoing "not fixed": the item goes back to the operator's view as addressed.
            item.released_to_operator_at = item.resolved_at
        item.resolved_by = None
        item.resolved_at = None
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="feedback.restored",
            payload={
                "feedback_id": str(item.id),
                "target": target_label(item),
                "from": undone.value,
                "to": previous.value,
            },
        )
        app.version += 1
        self.db.commit()
        self.db.refresh(item)
        return item


def restorable(item: Feedback, status: ApplicationStatus, officer_id: uuid.UUID, now: datetime) -> bool:
    """The officer who decided may undo while the window is open and the state still allows it."""
    if item.previous_resolution is None or item.resolved_at is None or item.resolved_by != officer_id:
        return False
    if now - item.resolved_at > UNDO_WINDOW:
        return False
    if item.resolution == FeedbackResolution.WITHDRAWN:
        return status == ApplicationStatus.UNDER_REVIEW
    if item.resolution == FeedbackResolution.RESOLVED:
        return status in _RESOLVABLE_STATES
    reopened = item.resolution == FeedbackResolution.OPEN
    if reopened and item.previous_resolution == FeedbackResolution.ADDRESSED:
        return status == ApplicationStatus.UNDER_REVIEW
    return False


def target_label(item: Feedback) -> str:
    if item.target_type == FeedbackTargetType.SECTION and item.section_key:
        section = get_section(item.section_key)
        return section.title if section else item.section_key
    if item.document_type is not None:
        return DOCUMENT_TYPE_LABELS.get(item.document_type, item.document_type.value)
    return "Application"
