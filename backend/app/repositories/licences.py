import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Licence


class LicenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def next_sequence(self) -> int:
        """The next value of the licence number sequence (consumed even when the licence is a preview)."""
        return int(self.db.scalar(text("SELECT nextval('licence_no_seq')")) or 0)

    def for_application(self, application_id: uuid.UUID) -> Licence | None:
        return self.db.scalar(select(Licence).where(Licence.application_id == application_id))

    def add(self, licence: Licence) -> Licence:
        self.db.add(licence)
        return licence
