"""verification_runs as a work queue: attempts, lease, worker (US-098, ADR-016)

Revision ID: 0016
Revises: 0015

The status column is a VARCHAR(16) without a CHECK constraint (`native_enum=False`), so the one new status,
`dead`, needs no DDL. `queued` is the existing `pending`; `running` and the finished states are unchanged.
Two partial indexes serve the worker: the oldest queued run, and the running runs by lease expiry.

Downgrade turns every `dead` run into `failed: interrupted` first, so the older code never meets a status
it does not know.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "verification_runs", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("verification_runs", sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("verification_runs", sa.Column("worker_id", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_verification_runs_queued",
        "verification_runs",
        ["created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_verification_runs_lease",
        "verification_runs",
        ["lease_until"],
        postgresql_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.execute(
        "UPDATE verification_runs SET status = 'failed', error_reason = 'interrupted' WHERE status = 'dead'"
    )
    op.drop_index("ix_verification_runs_lease", table_name="verification_runs")
    op.drop_index("ix_verification_runs_queued", table_name="verification_runs")
    op.drop_column("verification_runs", "worker_id")
    op.drop_column("verification_runs", "lease_until")
    op.drop_column("verification_runs", "attempts")
