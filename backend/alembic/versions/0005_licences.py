"""licences (US-051)

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS licence_no_seq START WITH 1")
    op.create_table(
        "licences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("licence_no", sa.String(length=20), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("issued_by", sa.Uuid(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("verification_code", sa.String(length=20), nullable=False),
        sa.Column("stored_key", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["issued_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id"),
        sa.UniqueConstraint("licence_no"),
    )


def downgrade() -> None:
    op.drop_table("licences")
    op.execute("DROP SEQUENCE IF EXISTS licence_no_seq")
