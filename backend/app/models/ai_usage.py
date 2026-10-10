import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_id, utcnow


class AiPrice(Base):
    """What a model costs per million tokens from `effective_from` on (US-100). A price is never edited:
    a new row with a later date replaces it, so a past run keeps the price it was charged at."""

    __tablename__ = "ai_prices"
    __table_args__ = (UniqueConstraint("model", "effective_from", name="uq_ai_prices_model_from"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    input_per_million: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    output_per_million: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiUsage(Base):
    """One row per verification run: who ran it, on what, how many tokens, what it cost (US-100). Written
    in the transaction that stores the run's result. `run_id`, `document_id` and `application_id` are plain
    columns, not foreign keys: deleting a draft removes its runs and documents, but money already spent
    stays on the books."""

    __tablename__ = "ai_usage"
    __table_args__ = (
        Index("ix_ai_usage_created_at", "created_at"),
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
        Index("ix_ai_usage_application_created", "application_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    run_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True)
    document_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    application_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(14, 8), default=Decimal(0), nullable=False)
    price_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_prices.id"), nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
