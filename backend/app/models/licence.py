import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_id, utcnow


class Licence(Base):
    """The certificate issued when an application is approved (US-051). One per application; immutable."""

    __tablename__ = "licences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id"), nullable=False, unique=True
    )
    licence_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(nullable=False)
    issued_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=False)
    verification_code: Mapped[str] = mapped_column(String(20), nullable=False)
    stored_key: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
