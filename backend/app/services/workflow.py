"""Status transitions driven by an officer or by the system (FR-019, SEC-004, REL-007). Every change
goes through `domain/workflow.py`; the row is locked, the version is checked, the audit event and the
notifications the edge's policy names are written in the same transaction.

The actor is the caller's (`actor_for_role`), never assumed (US-079): an admin has none and is refused
before the table is consulted; the checklist submit (US-063) passes `Actor.SYSTEM`."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import metrics
from app.core.errors import Forbidden, InvalidTransition, ValidationFailed, VersionConflict
from app.core.settings import get_settings
from app.domain.enums import ApplicationStatus, NotificationKind
from app.domain.labels import operator_label
from app.domain.workflow import Actor, TransitionContext, TransitionError, actor_for_role, transition
from app.infra.storage import get_storage
from app.models import Application, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.feedback import FeedbackRepository
from app.services.licence import LicenceService
from app.services.notifications import NotificationService
from app.services.site_visit import SiteVisitService


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)
        self.feedback = FeedbackRepository(db)
        self.notifications = NotificationService(db)

    def transition(
        self,
        actor_user: User,
        application_id: uuid.UUID,
        target: str,
        *,
        note: str | None,
        expected_version: int,
        actor: Actor | None = None,
        operator_body: str | None = None,
    ) -> Application:
        """Move `application_id` to `target` as `actor_user`. `actor` defaults to the user's own role;
        a service acting for the system passes `Actor.SYSTEM` (the audit row still names the user).
        `operator_body` replaces the standard notification text for edges whose message carries facts
        the caller knows (the count of flagged items, for example)."""
        try:
            new_status = ApplicationStatus(target)
        except ValueError as exc:
            raise ValidationFailed(
                "Unknown status.", details={"fields": {"target": "Unknown status."}}
            ) from exc
        app = self.applications.get_for(actor_user, application_id, for_update=True)
        if app.version != expected_version:
            raise VersionConflict("This application changed since you opened it. Reload to see the latest.")
        licence_key = self.apply(
            app, new_status, actor_user, note=note, actor=actor, operator_body=operator_body
        )
        try:
            self.db.commit()
        except Exception:
            # The PDF was written before the commit; without the row it would be an orphan on the volume.
            if licence_key is not None:
                get_storage().delete(licence_key)
            raise
        acting = actor if actor is not None else actor_for_role(actor_user.role)
        metrics.TRANSITIONS.labels(app.status.value, acting.value if acting else "system").inc()
        if app.status == ApplicationStatus.PENDING_POST_SITE_RESUBMISSION:
            # Request another round released the drafted questions inside the transaction (US-089).
            metrics.CLARIFICATION_ROUNDS.labels("released").inc()
        self.notifications.flush_sent()
        self.db.refresh(app)
        return app

    def apply(
        self,
        app: Application,
        new_status: ApplicationStatus,
        actor_user: User,
        *,
        note: str | None,
        actor: Actor | None = None,
        operator_body: str | None = None,
        notify_operator: bool = True,
    ) -> str | None:
        """Move an already locked `app` to `new_status` without committing: guards, side effects, the
        audit row and the operator's notification. Returns the licence storage key when one was issued,
        so the caller can remove the PDF if its commit fails."""
        acting = actor if actor is not None else actor_for_role(actor_user.role)
        if acting is None:
            raise Forbidden("Not available for your role.")
        note = (note or "").strip() or None
        ctx = self.build_context(
            app,
            open_feedback_count=self.feedback.open_counts([app.id]).get(app.id, 0),
            has_note=note is not None,
        )
        try:
            resolved = transition(app.status, new_status, acting, ctx)
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
                    actor_id=actor_user.id,
                    event_type="feedback.released",
                    payload={"feedback_ids": released},
                )
        if resolved == ApplicationStatus.SITE_VISIT_DONE:
            # The confirmed appointment is over (US-084); the guard made sure one exists.
            SiteVisitService(self.db).mark_done(app, datetime.now(UTC), actor_user)
        released_count = 0
        if resolved == ApplicationStatus.PENDING_POST_SITE_RESUBMISSION:
            # Request another round (US-066): the drafted questions reach the operator now.
            from app.services.clarification import ClarificationService  # noqa: PLC0415

            released_count = ClarificationService(self.db).release_next_round(
                app, actor_user, datetime.now(UTC)
            )
            if operator_body is None:
                word = "item" if released_count == 1 else "items"
                operator_body = (
                    f"The licensing officer needs more information on {released_count} {word} after "
                    "your answers. Open the application to respond."
                )
        # A note is stored only with a decision and ignored for other targets (TransitionIn says so).
        note = note if resolved in (ApplicationStatus.APPROVED, ApplicationStatus.REJECTED) else None
        if note is not None:
            app.decision_note = note
        licence_no: str | None = None
        licence_key: str | None = None
        if resolved == ApplicationStatus.APPROVED:
            # The certificate is part of the approval: same transaction, audited, or neither happens (US-051).
            licence = LicenceService(self.db).issue(app, actor_user)
            licence_no, licence_key = licence.licence_no, licence.stored_key
        app.version += 1
        self.audit.record(
            application_id=app.id,
            actor_id=actor_user.id,
            event_type="status.changed",
            payload={
                "from": previous.value,
                "to": resolved.value,
                "trigger": acting.value,
                "has_note": note is not None,
            },
        )
        # Notification policy per edge: the operator is told when the label or their next step
        # changes; officers are told by the operator-side services (submit, resubmit, send responses).
        if notify_operator and resolved in NOTIFY_OPERATOR:
            self.notifications.notify_user(
                app.operator_id,
                app,
                NotificationKind.STATUS_CHANGED,
                f"{app.reference_no}: {operator_label(resolved)}",
                operator_body or _operator_body(resolved, note, licence_no),
            )
        return licence_key

    def build_context(
        self, app: Application, *, open_feedback_count: int, has_note: bool
    ) -> TransitionContext:
        """The guard context for `app`, the same for a transition and for the case view's `actions[]`.
        The appointment part reads the current site visit (US-084); the checklist part reads the
        current visit's checklist and its clarification threads (US-060, US-063): submitting the
        checklist opens the automatic hop to Awaiting Post-Site Clarification, and the post-site guards
        count the open and answered items. Since US-063 every case reaches approval through it."""
        from app.services.checklist import ChecklistService  # noqa: PLC0415 - the services call each other

        checklists = ChecklistService(self.db)
        facts = checklists.facts(app)
        visits = SiteVisitService(self.db)
        day = visits.visit_day(app) if get_settings().site_visit_day_guard else None
        return TransitionContext(
            open_feedback_count=open_feedback_count,
            has_note=has_note,
            visit_confirmed=visits.visit_confirmed(app),
            visit_day_ahead=f"{day.strftime('%a')} {day.day} {day.strftime('%b')}" if day else None,
            checklist_complete=facts.complete,
            open_clarification_count=facts.open_clarifications,
            answered_clarification_count=facts.answered_clarifications,
            all_open_items_answered=facts.all_open_answered,
        )


# Every target the operator is told about. Every edge an officer or the system can take changes the
# operator's label or their next step, so the set is the whole table minus the operator's own edges.
NOTIFY_OPERATOR: frozenset[ApplicationStatus] = frozenset(
    {
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION,
        ApplicationStatus.SITE_VISIT_SCHEDULED,
        ApplicationStatus.SITE_VISIT_DONE,
        ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION,
        ApplicationStatus.PENDING_POST_SITE_RESUBMISSION,
        ApplicationStatus.PENDING_APPROVAL,
        ApplicationStatus.APPROVED,
        ApplicationStatus.REJECTED,
    }
)


def _operator_body(status: ApplicationStatus, note: str | None, licence_no: str | None = None) -> str:
    if status == ApplicationStatus.UNDER_REVIEW:
        return "A licensing officer has started reviewing your application. Nothing is needed from you."
    if status == ApplicationStatus.PENDING_PRE_SITE_RESUBMISSION:
        return "The licensing office has asked for changes. Open the application to see the feedback."
    if status == ApplicationStatus.SITE_VISIT_SCHEDULED:
        return "An officer will contact you to arrange a visit to the premises."
    if status == ApplicationStatus.SITE_VISIT_DONE:
        return (
            "The site visit is done. The officer is writing up the inspection; "
            "you will be told if anything needs clarifying."
        )
    if status == ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION:
        return (
            "The licensing officer completed the site visit and needs more information. "
            "Open the application to answer."
        )
    if status == ApplicationStatus.PENDING_POST_SITE_RESUBMISSION:
        return (
            "The licensing officer needs more information after your answers. "
            "Open the application to respond."
        )
    if status == ApplicationStatus.PENDING_APPROVAL:
        return "Your application is with the licensing office for a decision. Nothing is needed from you."
    if status == ApplicationStatus.APPROVED:
        text = "Your licence application has been approved."
        if licence_no:
            text += f" Licence {licence_no} is ready to download from the application page."
        return text + (f" Officer's note: {note}" if note else "")
    if status == ApplicationStatus.REJECTED:
        return "Your licence application was not approved." + (f" Officer's note: {note}" if note else "")
    return f"Your application is now {operator_label(status)}."
