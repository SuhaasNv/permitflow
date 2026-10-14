"""ai_prices, ai_usage and verification_runs.requested_by: what each check cost and who ran it (US-100)

Revision ID: 0017
Revises: 0016

`ai_prices` is versioned: the price of a run is the row of its model with the latest `effective_from` not
after the run. The current model is seeded at its list price (USD per million tokens); a price change is a
new row, never an edit. `ai_usage` holds one row per run. Its run, document and application ids are plain
columns (no foreign keys) so the record outlives a deleted draft.

Downgrade drops the three additions; the usage history goes with them.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# gpt-4.1-mini list price (developers.openai.com/api/docs/pricing, checked 20 Sep 2026): the model the
# environment defaults to (`OPENAI_MODEL`). The invoice is the truth; this is the estimate.
SEED_MODEL = "gpt-4.1-mini"
SEED_INPUT_PER_MILLION = Decimal("0.40")
SEED_OUTPUT_PER_MILLION = Decimal("1.60")
SEED_EFFECTIVE_FROM = datetime(2025, 4, 14, tzinfo=UTC)


def upgrade() -> None:
    prices = op.create_table(
        "ai_prices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("input_per_million", sa.Numeric(12, 6), nullable=False),
        sa.Column("output_per_million", sa.Numeric(12, 6), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("model", "effective_from", name="uq_ai_prices_model_from"),
    )
    op.bulk_insert(
        prices,
        [
            {
                "id": uuid.uuid4(),
                "model": SEED_MODEL,
                "input_per_million": SEED_INPUT_PER_MILLION,
                "output_per_million": SEED_OUTPUT_PER_MILLION,
                "effective_from": SEED_EFFECTIVE_FROM,
            }
        ],
    )
    op.create_table(
        "ai_usage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(14, 8), nullable=False, server_default="0"),
        sa.Column("price_id", sa.Uuid(), sa.ForeignKey("ai_prices.id"), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_usage_created_at", "ai_usage", ["created_at"])
    op.create_index("ix_ai_usage_user_created", "ai_usage", ["user_id", "created_at"])
    op.create_index("ix_ai_usage_application_created", "ai_usage", ["application_id", "created_at"])
    op.add_column(
        "verification_runs",
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("verification_runs", "requested_by")
    op.drop_index("ix_ai_usage_application_created", table_name="ai_usage")
    op.drop_index("ix_ai_usage_user_created", table_name="ai_usage")
    op.drop_index("ix_ai_usage_created_at", table_name="ai_usage")
    op.drop_table("ai_usage")
    op.drop_table("ai_prices")
