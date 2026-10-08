"""platform_settings: administrator overrides of the environment limits (US-101)

Revision ID: 0015
Revises: 0014

An empty table changes nothing: every consumer falls back to the environment value. The history of
changes is kept in `audit_events` (`settings.changed`, `settings.reverted`), so there is no second table.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("platform_settings")
