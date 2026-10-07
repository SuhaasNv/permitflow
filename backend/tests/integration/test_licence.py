"""US-051: approval issues a licence in the same transaction; owner and officers can fetch it."""

import uuid
from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Licence, Notification
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import to_pending_approval, transition, under_review


def _preview(client: TestClient, h: dict[str, str], app_id: str) -> int:
    return client.get(f"/api/v1/officer/applications/{app_id}/licence/preview", headers=h).status_code


def _licence(client: TestClient, h: dict[str, str], app_id: str) -> int:
    return client.get(f"/api/v1/applications/{app_id}/licence", headers=h).status_code


def _to_pending_approval(client: TestClient, off: dict[str, str], op: dict[str, str], app_id: str) -> None:
    to_pending_approval(client, off, op, app_id)


def test_preview_then_approve_issues_and_serves_the_licence(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    # preview only while awaiting a decision
    assert _preview(client, off, app_id) == 409
    _to_pending_approval(client, off, op, app_id)
    r = client.get(f"/api/v1/officer/applications/{app_id}/licence/preview", headers=off)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert "PREVIEW" in PdfReader(BytesIO(r.content)).pages[0].extract_text()
    assert db.scalar(select(Licence).where(Licence.application_id == uuid.UUID(app_id))) is None
    # nothing to download yet
    assert client.get(f"/api/v1/applications/{app_id}/licence", headers=op).status_code == 404

    view = transition(client, off, app_id, "approved", note="All good.")
    assert view["licence"] is not None and view["licence"]["licence_no"].startswith("FEL-")
    licence = db.scalar(select(Licence).where(Licence.application_id == uuid.UUID(app_id)))
    assert licence is not None and licence.revision_number == 1
    events = db.scalars(select(AuditEvent).where(AuditEvent.application_id == uuid.UUID(app_id))).all()
    issued = [e for e in events if e.event_type == "licence.issued"]
    assert len(issued) == 1 and issued[0].payload["licence_no"] == licence.licence_no
    last = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert last is not None and licence.licence_no in last.body

    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["licence"]["licence_no"] == licence.licence_no
    assert mine["licence"]["verification_code"] == licence.verification_code
    r = client.get(f"/api/v1/applications/{app_id}/licence", headers=op)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert f'filename="{licence.licence_no}.pdf"' in r.headers["content-disposition"]
    text = PdfReader(BytesIO(r.content)).pages[0].extract_text()
    assert licence.licence_no in text and "PREVIEW" not in text
    assert client.get(f"/api/v1/applications/{app_id}/licence", headers=off).status_code == 200
    # preview is closed once decided
    assert _preview(client, off, app_id) == 409
    trail = client.get(f"/api/v1/officer/applications/{app_id}/audit", headers=off).json()["events"]
    assert any(e["summary"].startswith(f"Licence {licence.licence_no} issued") for e in trail)


def test_licence_is_owner_or_officer_only_and_rejection_issues_none(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    _to_pending_approval(client, off, op, app_id)
    transition(client, off, app_id, "approved")
    make_user(db, "other@example.sg", Role.OPERATOR)
    make_user(db, "admin@example.sg", Role.ADMIN)
    assert _licence(client, login(client, "other@example.sg"), app_id) == 404
    # an administrator reads the certificate (US-072) but never previews one (officer-only)
    assert _licence(client, login(client, "admin@example.sg"), app_id) == 200
    assert _preview(client, login(client, "admin@example.sg"), app_id) == 403
    assert _preview(client, op, app_id) == 403


def test_rejection_issues_no_licence(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    transition(client, off, app_id, "rejected", note="Not eligible.")
    assert db.scalar(select(Licence).where(Licence.application_id == uuid.UUID(app_id))) is None
    assert client.get(f"/api/v1/applications/{app_id}/licence", headers=op).status_code == 404
    assert client.get(f"/api/v1/applications/{app_id}", headers=op).json()["licence"] is None


def test_licence_year_follows_the_singapore_date() -> None:
    """Between 00:00 and 08:00 SGT on 1 January the UTC year is still the old one (run-through fix L2)."""
    from datetime import UTC, date, datetime

    from app.domain.licence import licence_number, validity
    from app.services import licence as licence_service

    fixed = datetime(2026, 12, 31, 20, 0, tzinfo=UTC)
    issued_on = fixed.astimezone(licence_service.LOCAL_TZ).date()
    assert issued_on == date(2027, 1, 1)
    assert licence_number(issued_on.year, 1) == "FEL-2027-000001"
    assert validity(issued_on) == (date(2027, 1, 1), date(2027, 12, 31))
