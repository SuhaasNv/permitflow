import logging
import uuid
from collections.abc import Iterable

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models import Application, User
from app.models.enums import ApplicationStatus, Role

logger = logging.getLogger("permitflow")


class ApplicationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for(self, user: User, application_id: uuid.UUID, *, for_update: bool = False) -> Application:
        """Ownership-aware lookup (SEC-002). Operators see only their own rows; others look like 404.

        Officers and admins may read any application. Drafts are never visible to officers/admins
        because they are not yet submitted (draft is a pre-submission state).
        """
        stmt = select(Application).where(Application.id == application_id)
        if for_update:
            stmt = stmt.with_for_update()
        app = self.db.scalar(stmt)
        if app is None:
            raise NotFound("Application not found.")
        if user.role == Role.OPERATOR and app.operator_id != user.id:
            logger.warning(
                "ownership_denied",
                extra={"extra_fields": {"user_id": str(user.id), "application_id": str(application_id)}},
            )
            raise NotFound("Application not found.")
        if user.role != Role.OPERATOR and app.status == ApplicationStatus.DRAFT:
            raise NotFound("Application not found.")
        return app

    def list_for_operator(self, operator_id: uuid.UUID) -> list[Application]:
        stmt = (
            select(Application)
            .where(Application.operator_id == operator_id)
            .order_by(Application.updated_at.desc())
        )
        return list(self.db.scalars(stmt))

    def list_submitted(self) -> list[tuple[Application, User]]:
        """Every non-draft application with its applicant, newest activity first (officer queue)."""
        stmt = (
            select(Application, User)
            .join(User, User.id == Application.operator_id)
            .where(Application.status != ApplicationStatus.DRAFT)
            .order_by(Application.updated_at.desc())
        )
        return [(row[0], row[1]) for row in self.db.execute(stmt)]

    def reference_numbers(self, ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, str]:
        wanted = list(ids)
        if not wanted:
            return {}
        stmt = select(Application.id, Application.reference_no).where(Application.id.in_(wanted))
        return {row[0]: row[1] for row in self.db.execute(stmt)}

    def count_by_status(self) -> dict[ApplicationStatus, int]:
        """Applications per status, one query (the `/metrics` gauge, US-077)."""
        stmt = select(Application.status, func.count()).group_by(Application.status)
        return {row[0]: int(row[1]) for row in self.db.execute(stmt)}

    def count_drafts(self, operator_id: uuid.UUID) -> int:
        """Open drafts an operator holds (US-058 quota)."""
        stmt = select(func.count()).where(
            Application.operator_id == operator_id, Application.status == ApplicationStatus.DRAFT
        )
        return int(self.db.execute(stmt).scalar_one())

    def next_reference_no(self, year: int) -> str:
        n = int(self.db.scalar(text("SELECT nextval('application_reference_seq')")) or 0)
        return f"PF-{year}-{n:06d}"

    def add(self, app: Application) -> Application:
        self.db.add(app)
        return app
