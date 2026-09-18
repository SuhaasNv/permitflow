"""Officer-driven status transitions (FR-019, SEC-004, REL-007). Every change goes through
`domain/workflow.py`; the row is locked, the version is checked, the audit event and the operator
notification are written in the same transaction."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import InvalidTransition, ValidationFailed, VersionConflict
from app.domain.enums import ApplicationStatus, NotificationKind
from app.domain.labels import operator_label
from app.domain.workflow import Actor, TransitionContext, TransitionError, transition
from app.models import Application, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.feedback import FeedbackRepository
from app.services.notifications import NotificationService


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)
        self.feedback = FeedbackRepository(db)
        self.notifications = NotificationService(db)

    def transition(
        self,
        officer: User,
        application_id: uuid.UUID,
        target: str,
        *,
        note: str | None,
        expected_version: int,
    ) -> Application:
        try:
            new_status = ApplicationStatus(target)
        except ValueError as exc:
            raise ValidationFailed(
                "Unknown status.", details={"fields": {"target": "Unknown status."}}
            ) from exc
        app = self.applications.get_for(officer, application_id, for_update=True)
        if app.version != expected_version:
            raise VersionConflict("This application changed since you opened it. Reload to see the latest.")
        note = (note or "").strip() or None
        ctx = TransitionContext(
            open_feedback_count=self.feedback.open_counts([app.id]).get(app.id, 0),
            has_note=note is not None,
        )
        try:
            resolved = transition(app.status, new_status, Actor.OFFICER, ctx)
        except TransitionError as exc:
            raise InvalidTransition(
                exc.message, details={"kind": exc.kind, "allowed": [s.value for s in exc.allowed]}
            ) from exc
        previous = app.status
        app.status = resolved
        if resolved == ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
            # Release this round's feedback to the operator and freeze it (STATE_MACHINE side effects).
            now = datetime.now(UTC)
            released = []
            for item in self.feedback.open_for(app.id):
                if item.released_to_operator_at is None:
                    item.released_to_operator_at = now
                    released.append(str(item.id))
            if released:
                self.audit.record(
                    application_id=app.id,
                    actor_id=officer.id,
                    event_type="feedback.released",
                    payload={"feedback_ids": released},
                )
        if note is not None and resolved in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED):
            app.decision_note = note
        app.version += 1
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="status.changed",
            payload={
                "from": previous.value,
                "to": resolved.value,
                "trigger": "officer",
                "has_note": note is not None,
            },
        )
        self.notifications.notify_user(
            app.operator_id,
            app,
            NotificationKind.STATUS_CHANGED,
            f"{app.reference_no}: {operator_label(resolved)}",
            _operator_body(resolved, note),
        )
        self.db.commit()
        self.notifications.flush_sent()
        self.db.refresh(app)
        return app


def _operator_body(status: ApplicationStatus, note: str | None) -> str:
    if status == ApplicationStatus.UNDER_REVIEW:
        return "A licensing officer has started reviewing your application. Nothing is needed from you."
    if status == ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
        return "The licensing office has asked for changes. Open the application to see the feedback."
    if status == ApplicationStatus.SITE_VISIT_SCHEDULED:
        return "An officer will contact you to arrange a visit to the premises."
    if status == ApplicationStatus.APPROVED:
        return "Your licence application has been approved." + (f" Officer's note: {note}" if note else "")
    if status == ApplicationStatus.REJECTED:
        return "Your licence application was not approved." + (f" Officer's note: {note}" if note else "")
    return f"Your application is now {operator_label(status)}."
