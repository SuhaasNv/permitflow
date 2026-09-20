"""indexes for the admin reads at volume (US-086, NFR-011)

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The idle list (newest event per application) and the per-case trail.
    op.create_index("ix_audit_events_application_created", "audit_events", ["application_id", "created_at"])
    # The activity feed's keyset: ORDER BY created_at DESC, id DESC with a (created_at, id) < cursor bound.
    op.create_index("ix_audit_events_created_id", "audit_events", ["created_at", "id"])
    # Today's counts and the transitions window: event type then time.
    op.create_index("ix_audit_events_type_created", "audit_events", ["event_type", "created_at"])
    # The check-health block (runs in the last 24 hours) and the daily quota count.
    op.create_index("ix_verification_runs_created_at", "verification_runs", ["created_at"])
    op.create_index("ix_verification_runs_started_at", "verification_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_verification_runs_started_at", table_name="verification_runs")
    op.drop_index("ix_verification_runs_created_at", table_name="verification_runs")
    op.drop_index("ix_audit_events_type_created", table_name="audit_events")
    op.drop_index("ix_audit_events_created_id", table_name="audit_events")
    op.drop_index("ix_audit_events_application_created", table_name="audit_events")
