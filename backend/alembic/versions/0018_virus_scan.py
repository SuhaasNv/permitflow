"""The virus scan state on documents and clarification attachments (US-099, ADR-017)

Revision ID: 0018
Revises: 0016

`scan_state` is NULL for every existing row and for every upload made with SCAN_MODE=off: those are served
as before. With SCAN_MODE=enforce it is `scanning`, `clean` or `infected` (a VARCHAR without a CHECK, like
the other state columns). `scan_signature` is the scanner's name for what it found; `active_content` is the
PDF flag (an automatic action with a script, a launch action, an embedded file). `scanned_at` is when the
verdict (clean or infected) landed; NULL while `scanning` and for rows the scan never touched.

The stored `scanner_fail_mode` setting changes its words (US-101 stored `closed` and `open`): `closed` becomes
`retry` and `open` becomes `hold`; the downgrade maps them back.

Downgrade drops the four columns. Files still under `quarantine/` keep their key and are served by the
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
RENAMES = (("closed", "retry"), ("open", "hold"))


def _rename_fail_mode(pairs: tuple[tuple[str, str], ...]) -> None:
    for old, new in pairs:
        op.execute(
            sa.text(
                "UPDATE platform_settings SET value = CAST(:new AS json) "
                "WHERE key = 'scanner_fail_mode' AND CAST(value AS text) = :old"
            ).bindparams(new=f'"{new}"', old=f'"{old}"')
        )


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("scan_state", sa.String(length=16), nullable=True))
        op.add_column(table, sa.Column("scan_signature", sa.String(length=120), nullable=True))
        op.add_column(table, sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(
            table, sa.Column("active_content", sa.Boolean(), nullable=False, server_default=sa.text("false"))
        )
    _rename_fail_mode(RENAMES)


def downgrade() -> None:
    _rename_fail_mode(tuple((new, old) for old, new in RENAMES))
    for table in TABLES:
        op.drop_column(table, "active_content")
        op.drop_column(table, "scanned_at")
        op.drop_column(table, "scan_signature")
        op.drop_column(table, "scan_state")
