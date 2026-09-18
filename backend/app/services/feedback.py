"""Officer feedback (FR-018, FR-010, AUD-003). Items are created and withdrawn only while the application is
`under_review`; requesting a resubmission freezes and releases them (STATE_MACHINE.md, feedback lifecycle)."""

import uuid
from datetime import UTC, datetime

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


def target_label(item: Feedback) -> str:
    if item.target_type == FeedbackTargetType.SECTION and item.section_key:
        section = get_section(item.section_key)
        return section.title if section else item.section_key
    if item.document_type is not None:
        return DOCUMENT_TYPE_LABELS.get(item.document_type, item.document_type.value)
    return "Application"
