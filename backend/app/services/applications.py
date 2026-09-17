"""Application use cases for operators: create, list, read."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Application, User
from app.models.enums import ApplicationStatus, LicenceType
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository


class ApplicationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.audit = AuditRepository(db)

    def create(self, operator: User) -> Application:
        """One transaction: application row + `application.created` audit event (AUD-005)."""
        app = Application(
            reference_no=self.applications.next_reference_no(datetime.now(UTC).year),
            operator_id=operator.id,
            licence_type=LicenceType.FOOD_ESTABLISHMENT,
            status=ApplicationStatus.DRAFT,
            draft_data={},
        )
        self.applications.add(app)
        self.db.flush()
        self.audit.record(
            application_id=app.id,
            actor_id=operator.id,
            event_type="application.created",
            payload={"reference_no": app.reference_no, "licence_type": app.licence_type.value},
        )
        self.db.commit()
        self.db.refresh(app)
        return app

    def list_for(self, operator: User) -> list[Application]:
        return self.applications.list_for_operator(operator.id)

    def get_for(self, user: User, application_id: uuid.UUID) -> Application:
        return self.applications.get_for(user, application_id)
