"""site visit checklist (US-060)

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "checklists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("visit_no", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("draft", "submitted", name="checklist_status", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("last_save_id", sa.String(length=64), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_by_id", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "visit_no", name="uq_checklists_application_visit"),
    )
    op.create_index("ix_checklists_application_id", "checklists", ["application_id"])
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("item_key", sa.String(length=48), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "result",
            sa.Enum(
                "not_assessed",
                "satisfactory",
                "unsatisfactory",
                "not_applicable",
                name="checklist_result",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("needs_clarification", sa.Boolean(), nullable=False),
        sa.Column(
            "clarification_status",
            sa.Enum(
                "none",
                "open",
                "answered",
                "resolved",
                "withdrawn",
                name="clarification_status",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("resolved_by_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["checklist_id"], ["checklists.id"]),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checklist_id", "item_key", name="uq_checklist_items_key"),
    )
    op.create_index("ix_checklist_items_checklist_id", "checklist_items", ["checklist_id"])


def downgrade() -> None:
    op.drop_index("ix_checklist_items_checklist_id", table_name="checklist_items")
    op.drop_table("checklist_items")
    op.drop_index("ix_checklists_application_id", table_name="checklists")
    op.drop_table("checklists")
