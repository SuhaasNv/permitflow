"""extra findings on the checklist (US-092)

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("checklist_items", sa.Column("custom_title", sa.String(length=120), nullable=True))
    op.add_column("checklist_items", sa.Column("parent_key", sa.String(length=48), nullable=True))


def downgrade() -> None:
    op.drop_column("checklist_items", "parent_key")
    op.drop_column("checklist_items", "custom_title")
