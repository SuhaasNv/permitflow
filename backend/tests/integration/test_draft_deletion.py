"""US-045: the owner deletes a draft outright; anything submitted is protected."""

import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.models import Application, AuditEvent, Document, VerificationRun
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import TXT, draft, submitted, upload


def test_owner_deletes_draft_with_files(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    r = upload(client, op, app_id, "floor_plan", "plan.txt", TXT, "text/plain")
    assert r.status_code == 201, r.text
    doc = db.scalars(select(Document).where(Document.application_id == uuid.UUID(app_id))).one()
    path = Path(get_settings().upload_dir) / doc.stored_key
    assert path.exists()

    r = client.delete(f"/api/v1/applications/{app_id}", headers=op)
    assert r.status_code == 204, r.text
    assert db.get(Application, uuid.UUID(app_id)) is None
    assert db.scalars(select(Document).where(Document.application_id == uuid.UUID(app_id))).all() == []
    assert db.scalars(select(VerificationRun).where(VerificationRun.document_id == doc.id)).all() == []
    assert db.scalars(select(AuditEvent).where(AuditEvent.application_id == uuid.UUID(app_id))).all() == []
    assert not path.exists()
    assert client.get(f"/api/v1/applications/{app_id}", headers=op).status_code == 404
    assert all(a["id"] != app_id for a in client.get("/api/v1/applications", headers=op).json())


def test_submitted_cannot_be_deleted_and_only_the_owner_may(client: TestClient, db: Session) -> None:
    app_id, op, off = submitted(client, db)
    r = client.delete(f"/api/v1/applications/{app_id}", headers=op)
    assert r.status_code == 409 and "withdrawn" in r.json()["error"]["message"]
    assert client.delete(f"/api/v1/applications/{app_id}", headers=off).status_code == 403
    make_user(db, "other@example.sg", Role.OPERATOR)
    make_user(db, "admin@example.sg", Role.ADMIN)
    other = login(client, "other@example.sg")
    draft_id = draft(client, other)
    assert client.delete(f"/api/v1/applications/{draft_id}", headers=op).status_code == 404
    assert (
        client.delete(
            f"/api/v1/applications/{draft_id}", headers=login(client, "admin@example.sg")
        ).status_code
        == 403
    )
    assert client.get(f"/api/v1/applications/{draft_id}", headers=other).status_code == 200
