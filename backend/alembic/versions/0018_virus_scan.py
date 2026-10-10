"""The virus scan state on documents and clarification attachments (US-099, ADR-017)

Revision ID: 0018
Revises: 0016

`scan_state` is NULL for every existing row and for every upload made with SCAN_MODE=off: those are served
as before. With SCAN_MODE=enforce it is `scanning`, `clean` or `infected` (a VARCHAR without a CHECK, like
the other state columns). `scan_signature` is the scanner's name for what it found; `active_content` is the
PDF flag (an automatic action with a script, a launch action, an embedded file).

Downgrade drops the three columns. Files still under `quarantine/` keep their key and are served by the
older code once it reads them, so run a downgrade only with SCAN_MODE=off and nothing left `scanning`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
# lead: rebase down_revision onto 0017 at merge
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("documents", "clarification_attachments")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("scan_state", sa.String(length=16), nullable=True))
        op.add_column(table, sa.Column("scan_signature", sa.String(length=120), nullable=True))
        op.add_column(
            table, sa.Column("active_content", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "active_content")
        op.drop_column(table, "scan_signature")
        op.drop_column(table, "scan_state")
