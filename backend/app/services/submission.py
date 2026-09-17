"""Submit and resubmit (FR-007, FR-012).

One transaction: revision + status + audit + notifications (REL-002)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import InvalidTransition, ValidationFailed
from app.domain import completeness as completeness_rules
from app.domain.enums import ApplicationStatus, NotificationKind
from app.domain.workflow import Actor, TransitionContext, TransitionError, transition
from app.models import Application, ApplicationRevision, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.documents import DocumentRepository
from app.repositories.revisions import RevisionRepository
from app.services.notifications import NotificationService


class SubmissionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.documents = DocumentRepository(db)
        self.revisions = RevisionRepository(db)
        self.audit = AuditRepository(db)
        self.notifications = NotificationService(db)

    def submit(self, operator: User, application_id: uuid.UUID) -> Application:
        app = self.applications.get_for(operator, application_id, for_update=True)
        docs = self.documents.current_for(app.id)
        comp = completeness_rules.compute(app.draft_data, {d.document_type for d in docs})
        ctx = TransitionContext(is_complete=comp.is_complete)
        try:
            new_status = transition(app.status, ApplicationStatus.APPLICATION_RECEIVED, Actor.OPERATOR, ctx)
        except TransitionError as exc:
            if exc.kind == "guard":
                raise ValidationFailed(exc.message, details={"missing": list(comp.missing)}) from exc
            raise InvalidTransition(exc.message, details={"allowed": [s.value for s in exc.allowed]}) from exc

        number = self.revisions.next_number(app.id)
        revision = ApplicationRevision(
            application_id=app.id,
            revision_number=number,
            form_data=dict(app.draft_data),
            document_ids=[str(d.id) for d in docs],
            submitted_by=operator.id,
            submitted_at=datetime.now(UTC),
        )
        self.revisions.add(revision)
        self.db.flush()
        previous = app.status
        app.status = new_status
        app.current_revision_id = revision.id
        app.version += 1
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="revision.submitted",
            payload={"revision_number": number, "revision_id": str(revision.id), "document_count": len(docs)},
        )
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="status.changed",
            payload={"from": previous.value, "to": new_status.value, "trigger": "submit"},
        )
        business = (app.draft_data.get("business") or {}).get("business_name") or app.reference_no
        self.notifications.notify_officers(
            app,
            NotificationKind.SUBMITTED,
            f"New application {app.reference_no}",
            f"{business} · Food Establishment Licence · Revision {number}",
        )
        self.db.commit()
        self.db.refresh(app)
        return app
