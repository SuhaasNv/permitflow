"""Operator withdrawal (US-038). Goes through `domain/workflow.py` like every status change: row lock,
state-machine check, audit event and officer notifications in the same transaction."""

import uuid

from sqlalchemy.orm import Session

from app.core.errors import InvalidTransition
from app.domain.enums import ApplicationStatus, NotificationKind
from app.domain.operator_errors import refusal
from app.domain.workflow import Actor, TransitionContext, TransitionError, transition
from app.models import Application, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.services.notifications import NotificationService


class WithdrawalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)
        self.notifications = NotificationService(db)

    def withdraw(self, operator: User, application_id: uuid.UUID, reason: str | None) -> Application:
        app = self.applications.get_for(operator, application_id, for_update=True)
        reason = (reason or "").strip() or None
        try:
            resolved = transition(
                app.status, ApplicationStatus.WITHDRAWN, Actor.OPERATOR, TransitionContext()
            )
        except TransitionError as exc:
            # Operator bodies never carry internal status codes (FR-026): no `allowed` list, own label only.
            if app.status == ApplicationStatus.DRAFT:
                message = "A draft has not been submitted, so there is nothing to withdraw."
            elif app.status in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED):
                message = "A decided application cannot be withdrawn."
            elif app.status == ApplicationStatus.WITHDRAWN:
                message = "This application has already been withdrawn."
            else:
                message = refusal(app.status, "withdraw")
            raise InvalidTransition(message, details={"kind": exc.kind}) from exc
        previous = app.status
        app.status = resolved
        app.withdrawal_reason = reason
        app.version += 1
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="status.changed",
            payload={
                "from": previous.value,
                "to": resolved.value,
                "trigger": "operator",
                "has_note": reason is not None,
            },
        )
        self.notifications.notify_officers(
            app,
            NotificationKind.STATUS_CHANGED,
            f"{app.reference_no}: Withdrawn",
            f"{operator.full_name} withdrew the application."
            + (f" Reason: {reason}" if reason else " No reason was given."),
        )
        self.db.commit()
        self.notifications.flush_sent()
        self.db.refresh(app)
        return app
