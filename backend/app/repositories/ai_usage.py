import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import AiPrice, AiUsage, Application, User


@dataclass(frozen=True)
class UsageFilters:
    user_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    since: datetime | None = None  # inclusive
    until: datetime | None = None  # exclusive


@dataclass(frozen=True)
class UsageRow:
    usage: AiUsage
    user_name: str | None
    reference_no: str | None


@dataclass(frozen=True)
class UsageTotals:
    runs: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal


class AiUsageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def price_at(self, model: str, at: datetime) -> AiPrice | None:
        """The price in force for `model` at `at`: the latest row not after it, or None when the model
        has no price yet (or none that early)."""
        return self.db.scalar(
            select(AiPrice)
            .where(AiPrice.model == model, AiPrice.effective_from <= at)
            .order_by(AiPrice.effective_from.desc())
            .limit(1)
        )

    def recorded(self, run_ids: list[uuid.UUID]) -> set[uuid.UUID]:
        """Which of these runs already have a usage row."""
        if not run_ids:
            return set()
        return set(self.db.scalars(select(AiUsage.run_id).where(AiUsage.run_id.in_(run_ids))))

    def add(self, row: AiUsage) -> AiUsage:
        self.db.add(row)
        return row

    @staticmethod
    def _where[T: tuple[object, ...]](stmt: Select[T], f: UsageFilters) -> Select[T]:
        if f.user_id is not None:
            stmt = stmt.where(AiUsage.user_id == f.user_id)
        if f.application_id is not None:
            stmt = stmt.where(AiUsage.application_id == f.application_id)
        if f.since is not None:
            stmt = stmt.where(AiUsage.created_at >= f.since)
        if f.until is not None:
            stmt = stmt.where(AiUsage.created_at < f.until)
        return stmt

    def _rows(self, f: UsageFilters) -> Select[tuple[AiUsage, str, str]]:  # outer joins: None at run time
        stmt = (
            select(AiUsage, User.full_name, Application.reference_no)
            .outerjoin(User, User.id == AiUsage.user_id)
            .outerjoin(Application, Application.id == AiUsage.application_id)
        )
        return self._where(stmt, f).order_by(AiUsage.created_at.desc(), AiUsage.id.desc())

    def page(
        self, f: UsageFilters, *, limit: int, before: tuple[datetime, uuid.UUID] | None
    ) -> list[UsageRow]:
        """Newest first, keyset-paged on (created_at, id)."""
        stmt = self._rows(f)
        if before is not None:
            created_at, row_id = before
            stmt = stmt.where(
                or_(
                    AiUsage.created_at < created_at,
                    and_(AiUsage.created_at == created_at, AiUsage.id < row_id),
                )
            )
        return [UsageRow(u, name, ref) for u, name, ref in self.db.execute(stmt.limit(limit))]

    def stream(self, f: UsageFilters, *, batch: int = 500) -> Iterator[UsageRow]:
        """Every matching row, newest first, fetched in batches (the CSV export)."""
        result = self.db.execute(self._rows(f).execution_options(yield_per=batch))
        for u, name, ref in result:
            yield UsageRow(u, name, ref)

    def totals(self, f: UsageFilters) -> UsageTotals:
        stmt = self._where(
            select(
                func.count(),
                func.coalesce(func.sum(AiUsage.input_tokens), 0),
                func.coalesce(func.sum(AiUsage.output_tokens), 0),
                func.coalesce(func.sum(AiUsage.cost_usd), 0),
            ).select_from(AiUsage),
            f,
        )
        runs, tokens_in, tokens_out, cost = self.db.execute(stmt).one()
        return UsageTotals(int(runs), int(tokens_in), int(tokens_out), Decimal(cost))
