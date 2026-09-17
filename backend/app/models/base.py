import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> uuid.UUID:
    return uuid.uuid4()


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def str_enum[E: enum.Enum](enum_cls: type[E], name: str, length: int) -> Enum:
    """VARCHAR-backed enum column that stores the enum *values* (stable API strings)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda cls: [m.value for m in cls],
    )
