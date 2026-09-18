"""Licence certificate (US-051): issued inside the approval transaction, stored on the uploads volume,
served only to the owner and officers. Preview renders the same template with a watermark and stores
nothing."""

import hashlib
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.domain.enums import ApplicationStatus, Role
from app.domain.licence import build_licence_data, licence_number
from app.infra.pdf.licence import render_licence_pdf
from app.infra.storage import FileStorage, get_storage
from app.models import Application, Licence, User
from app.repositories.applications import ApplicationRepository
from app.repositories.audit import AuditRepository
from app.repositories.revisions import RevisionRepository
from app.repositories.users import UserRepository
from app.schemas.applications import LicenceView


def licence_view(licence: Licence | None) -> LicenceView | None:
    if licence is None:
        return None
    return LicenceView(
        licence_no=licence.licence_no,
        issued_at=licence.issued_at,
        valid_from=licence.valid_from,
        valid_to=licence.valid_to,
        verification_code=licence.verification_code,
    )


# Licence dates are calendar dates in the issuing jurisdiction, not UTC.
LOCAL_TZ = ZoneInfo("Asia/Singapore")


class LicenceService:
    def __init__(self, db: Session, storage: FileStorage | None = None) -> None:
        self.db = db
        self.applications = ApplicationRepository(db)
        self.revisions = RevisionRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)
        self.storage = storage or get_storage()

    def issue(self, app: Application, officer: User) -> Licence:
        """Called by the workflow service after the status became approved, before the commit."""
        revisions = self.revisions.list_for(app.id)
        if not revisions:
            raise Conflict("Cannot issue a licence without a submitted revision.")
        current = revisions[-1]
        holder = self.users.get(app.operator_id)
        issued_at = datetime.now(UTC)
        sequence = int(self.db.scalar(text("SELECT nextval('licence_no_seq')")) or 0)
        data = build_licence_data(
            licence_no=licence_number(issued_at.year, sequence),
            reference_no=app.reference_no,
            form_data=current.form_data,
            holder_name=holder.full_name if holder else "",
            approved_by=officer.full_name,
            issued_on=issued_at.astimezone(LOCAL_TZ).date(),
        )
        pdf = render_licence_pdf(data)
        key = f"{app.id}/licence-{data.licence_no}.pdf"
        self.storage.put(key, iter([pdf]))
        licence = Licence(
            application_id=app.id,
            licence_no=data.licence_no,
            revision_number=current.revision_number,
            issued_by=officer.id,
            issued_at=issued_at,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
            verification_code=data.verification_code,
            stored_key=key,
            sha256=hashlib.sha256(pdf).hexdigest(),
        )
        self.db.add(licence)
        self.audit.record(
            application_id=app.id,
            actor_id=officer.id,
            event_type="licence.issued",
            payload={"licence_no": data.licence_no, "valid_to": data.valid_to.isoformat()},
        )
        return licence

    def preview(self, officer: User, application_id: uuid.UUID) -> bytes:
        """What the certificate would say if the officer approved now. Officers only; nothing is stored."""
        if officer.role != Role.OFFICER:
            raise NotFound("Application not found.")
        app = self.applications.get_for(officer, application_id)
        if app.status != ApplicationStatus.PENDING_APPROVAL:
            raise Conflict("A licence can be previewed only while the application is awaiting a decision.")
        revisions = self.revisions.list_for(app.id)
        if not revisions:
            raise Conflict("Cannot preview a licence without a submitted revision.")
        holder = self.users.get(app.operator_id)
        today = datetime.now(LOCAL_TZ).date()
        data = build_licence_data(
            licence_no=licence_number(today.year, 0),
            reference_no=app.reference_no,
            form_data=revisions[-1].form_data,
            holder_name=holder.full_name if holder else "",
            approved_by=officer.full_name,
            issued_on=today,
            preview=True,
        )
        return render_licence_pdf(data)

    def for_application(self, application_id: uuid.UUID) -> Licence | None:
        return self.db.scalar(select(Licence).where(Licence.application_id == application_id))

    def open_for_download(self, user: User, application_id: uuid.UUID) -> tuple[Licence, Iterator[bytes]]:
        """Owner or officer (SEC-002); admins wait for US-072 like document downloads."""
        if user.role not in (Role.OPERATOR, Role.OFFICER):
            raise NotFound("Licence not found.")
        app = self.applications.get_for(user, application_id)
        licence = self.for_application(app.id)
        if licence is None:
            raise NotFound("No licence has been issued for this application.")
        if not self.storage.exists(licence.stored_key):
            raise NotFound("This file is no longer available.")
        return licence, self.storage.open(licence.stored_key)
