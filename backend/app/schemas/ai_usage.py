"""AI usage and cost (US-100): the administrator's page of what each check cost and who ran it."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class AiUsageRowOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    run_id: uuid.UUID
    document_id: uuid.UUID
    application_id: uuid.UUID | None
    reference_no: str | None  # None once a deleted draft's application is gone
    business_name: str | None  # read from the application's form at query time; None for a deleted draft
    user_id: uuid.UUID | None
    user_name: str | None
    document_type: str
    provider: str
    model: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal  # sent as an exact decimal string
    latency_ms: int
    outcome: str


class AiUsageTotalsOut(BaseModel):
    runs: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    avg_latency_ms: int | None  # over the checks that reached a provider; null when none did


class AiUsageTodayOut(BaseModel):
    """The Singapore day so far. `runs` counts the checks that count toward `daily_cap`
    (`ai_runs_per_day`, the live setting); refusals by a quota or the pause switch are left out."""

    runs: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    daily_cap: int


class AiUsageOut(BaseModel):
    items: list[AiUsageRowOut]
    next_cursor: str | None
    totals: AiUsageTotalsOut  # over every row the filters match, not only this page
    today: AiUsageTodayOut
