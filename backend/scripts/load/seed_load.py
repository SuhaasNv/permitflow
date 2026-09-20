"""Fill a scratch database for the load run (US-086, NFR-011): 10,000 applications across every
status, one submitted revision each, 100,000 audit rows spread over the last 90 days, and one case in
Site Visit Scheduled with a confirmed visit for the checklist save. Never point this at a database that
matters: it refuses a URL that does not contain "load" or "scratch".

    DATABASE_URL=postgresql+psycopg://permitflow:permitflow@localhost:5432/permitflow_load \\
      uv run python scripts/load/seed_load.py
"""

from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import insert, text  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.domain.enums import (  # noqa: E402
    ApplicationStatus,
    SiteVisitProposalOutcome,
    SiteVisitSlot,
    SiteVisitStatus,
)
from app.infra.db import session_factory  # noqa: E402
from app.models import Application, ApplicationRevision, AuditEvent, SiteVisit, User  # noqa: E402
from app.models.enums import Role  # noqa: E402
from app.models.site_visit import SiteVisitProposal  # noqa: E402

APPLICATIONS = int(os.environ.get("LOAD_APPLICATIONS", "10000"))
AUDIT_ROWS = int(os.environ.get("LOAD_AUDIT_ROWS", "100000"))
PASSWORD = os.environ.get("SEED_PASSWORD", "PermitFlow!2026")
STATUSES = [s for s in ApplicationStatus if s != ApplicationStatus.DRAFT]
EVENTS = [
    "status.changed",
    "section.updated",
    "document.uploaded",
    "verification.completed",
    "feedback.created",
]


def main() -> None:
    url = os.environ.get("DATABASE_URL", "")
    if "load" not in url and "scratch" not in url:
        raise SystemExit("refusing: DATABASE_URL must name a load or scratch database")
    rng = random.Random(86)
    now = datetime.now(UTC)
    with session_factory()() as db:
        users: dict[str, User] = {}
        for email, name, role in (
            ("operator@permitflow.example.sg", "Tan Wei Ling", Role.OPERATOR),
            ("officer@permitflow.example.sg", "Rahim bin Abdullah", Role.OFFICER),
            ("admin@permitflow.example.sg", "Priya Nair", Role.ADMIN),
        ):
            u = User(email=email, full_name=name, role=role, password_hash=hash_password(PASSWORD))
            db.add(u)
            users[email] = u
        db.flush()
        operator = users["operator@permitflow.example.sg"].id
        officer = users["officer@permitflow.example.sg"].id

        apps: list[dict] = []
        revisions: list[dict] = []
        for i in range(APPLICATIONS):
            app_id = uuid.uuid4()
            created = now - timedelta(days=rng.uniform(0, 90))
            status = STATUSES[i % len(STATUSES)] if i > 0 else ApplicationStatus.SITE_VISIT_SCHEDULED
            form = {
                "business": {"business_name": f"Load Test Kitchen {i:05d} Pte. Ltd."},
                "premises": {"address_line_1": f"{i} Load Street"},
            }
            apps.append(
                {
                    "id": app_id,
                    "reference_no": f"PF-2026-{100000 + i:06d}",
                    "operator_id": operator,
                    "licence_type": "food_establishment",
                    "status": status.value,
                    "draft_data": form,
                    "current_revision_id": None,
                    "decision_note": None,
                    "withdrawal_reason": None,
                    "version": 1,
                    "created_at": created,
                    "updated_at": created + timedelta(hours=1),
                }
            )
            revisions.append(
                {
                    "id": uuid.uuid4(),
                    "application_id": app_id,
                    "revision_number": 1,
                    "form_data": form,
                    "document_ids": [],
                    "submitted_by": operator,
                    "submitted_at": created + timedelta(minutes=30),
                }
            )
        db.execute(insert(Application), apps)
        db.execute(insert(ApplicationRevision), revisions)
        events: list[dict] = []
        ids = [a["id"] for a in apps]
        for _ in range(AUDIT_ROWS):
            kind = rng.choice(EVENTS)
            events.append(
                {
                    "id": uuid.uuid4(),
                    "application_id": rng.choice(ids),
                    "actor_id": officer if kind in ("status.changed", "feedback.created") else operator,
                    "event_type": kind,
                    "payload": {"from": "under_review", "to": "site_visit_scheduled"}
                    if kind == "status.changed"
                    else {},
                    "created_at": now - timedelta(seconds=rng.uniform(0, 90 * 86400)),
                }
            )
            if len(events) >= 5000:
                db.execute(insert(AuditEvent), events)
                events = []
        if events:
            db.execute(insert(AuditEvent), events)
        # the first application: a confirmed visit so the checklist can be opened and saved
        visit = SiteVisit(
            application_id=ids[0],
            visit_no=1,
            status=SiteVisitStatus.CONFIRMED,
            date=(now + timedelta(days=3)).date(),
            slot=SiteVisitSlot.AFTERNOON,
            note=None,
            proposed_by_id=officer,
            confirmed_at=now,
            confirmed_by_id=operator,
            updated_at=now,
        )
        db.add(visit)
        db.flush()
        db.add(
            SiteVisitProposal(
                site_visit_id=visit.id,
                round_no=1,
                author_id=officer,
                author_role="officer",
                date=visit.date,
                slot=SiteVisitSlot.AFTERNOON,
                reason=None,
                outcome=SiteVisitProposalOutcome.ACCEPTED,
                decided_at=now,
            )
        )
        db.execute(text("SELECT setval('application_reference_seq', :n)"), {"n": 100000 + APPLICATIONS + 1})
        db.commit()
    print(f"seeded {APPLICATIONS} applications, {AUDIT_ROWS} audit rows")
    print(f"checklist case {apps[0]['reference_no']} ({ids[0]})")


if __name__ == "__main__":
    main()
