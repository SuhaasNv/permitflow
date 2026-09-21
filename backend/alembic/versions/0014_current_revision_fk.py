"""the foreign key from applications.current_revision_id to application_revisions

Revision ID: 0014
Revises: 0013

Migration 0001 declared the key with `use_alter=True` inside `create_table`, which Alembic does not emit,
so the column has carried no referential integrity since the first schema (review finding, 21 Sep 2026).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_applications_current_revision",
        "applications",
        "application_revisions",
        ["current_revision_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_applications_current_revision", "applications", type_="foreignkey")
