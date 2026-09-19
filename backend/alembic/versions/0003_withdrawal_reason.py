"""withdrawal reason (US-038)

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The status column is a plain VARCHAR (non-native enum), so the new "withdrawn" value needs no DDL.
    op.add_column("applications", sa.Column("withdrawal_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("applications", "withdrawal_reason")
