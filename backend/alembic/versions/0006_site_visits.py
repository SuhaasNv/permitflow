"""site visit appointment (US-084)

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_visits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("visit_no", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "proposed",
                "counter_proposed",
                "confirmed",
                "done",
                name="site_visit_status",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "slot",
            sa.Enum("morning", "afternoon", name="site_visit_slot", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("proposed_by_id", sa.Uuid(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by_id", sa.Uuid(), nullable=True),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["proposed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["confirmed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "visit_no", name="uq_site_visits_application_visit"),
    )
    op.create_index("ix_site_visits_application_id", "site_visits", ["application_id"])
    op.create_table(
        "site_visit_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_visit_id", sa.Uuid(), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("author_role", sa.String(length=16), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "slot",
            sa.Enum("morning", "afternoon", name="site_visit_slot", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "outcome",
            sa.Enum(
                "pending",
                "accepted",
                "kept",
                "declined",
                "superseded",
                name="site_visit_proposal_outcome",
                native_enum=False,
                length=16,
            ),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_visit_id"], ["site_visits.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_visit_proposals_site_visit_id", "site_visit_proposals", ["site_visit_id"])


def downgrade() -> None:
    op.drop_index("ix_site_visit_proposals_site_visit_id", table_name="site_visit_proposals")
    op.drop_table("site_visit_proposals")
    op.drop_index("ix_site_visits_application_id", table_name="site_visits")
    op.drop_table("site_visits")
