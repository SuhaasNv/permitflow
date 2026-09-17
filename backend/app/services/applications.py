"""Application use cases for operators: create, list, read."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.domain.editability import editable_targets
from app.domain.form_schema import get_section, validate_section
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

    def update_section(
        self, operator: User, application_id: uuid.UUID, key: str, data: dict[str, Any]
    ) -> Application:
        """Save one section of the working copy (FR-002, FR-003).

        The row is locked for the transaction; editability follows the state machine (403 outside the
        editable set); format/type errors are 422 with per-field messages; in `draft`, missing required
        fields are tolerated so a partial section can be saved and completed later.
        """
        if get_section(key) is None:
            raise NotFound("Section not found.")
        app = self.applications.get_for(operator, application_id, for_update=True)
        sections, _ = editable_targets(app.status, set(), set())  # open feedback wired in US-018
        if key not in sections:
            raise Forbidden("This section is not open for changes.")
        errors = validate_section(key, data, allow_missing=app.status == ApplicationStatus.DRAFT)
        if errors:
            raise ValidationFailed("Some fields need attention.", details={"fields": errors})
        draft = dict(app.draft_data)
        draft[key] = data
        app.draft_data = draft
        app.version += 1
        self.db.commit()
        self.db.refresh(app)
        return app
