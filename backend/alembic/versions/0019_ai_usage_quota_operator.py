"""ai_usage.quota_operator_id: the daily AI quota counts from the ledger (security audit run 5)

Revision ID: 0019
Revises: 0018

The quota used to count `verification_runs`, which are deleted with a draft, so deleting a draft reset the
count. `quota_operator_id` is the owner of the application the run counted toward; it is NULL for a run
refused by a quota or the AI pause (those never count). Existing rows are filled from their application.

Downgrade drops the column and its index; the quota then counts live runs again (older code).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_usage", sa.Column("quota_operator_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_ai_usage_quota_operator", "ai_usage", "users", ["quota_operator_id"], ["id"])
    op.create_index("ix_ai_usage_quota_operator_created", "ai_usage", ["quota_operator_id", "created_at"])
    op.execute(
        sa.text(
            "UPDATE ai_usage u SET quota_operator_id = a.operator_id FROM applications a "
            "WHERE a.id = u.application_id AND NOT EXISTS (SELECT 1 FROM verification_runs r "
            "WHERE r.id = u.run_id AND r.error_reason IN ('daily_limit_reached', 'ai_paused'))"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_quota_operator_created", table_name="ai_usage")
    op.drop_constraint("fk_ai_usage_quota_operator", "ai_usage", type_="foreignkey")
    op.drop_column("ai_usage", "quota_operator_id")
