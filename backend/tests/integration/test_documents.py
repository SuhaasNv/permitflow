import io
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, AuditEvent, Document, VerificationRun
from app.models.enums import ApplicationStatus, Role
from tests.factories import login, make_user

PDF = b"%PDF-1.4\n%fake\n1 0 obj << >> endobj\n%%EOF\n"


def _draft(client: TestClient, h: dict[str, str]) -> str:
    return str(client.post("/api/v1/applications", headers=h).json()["id"])


def _upload(
    client: TestClient,
    h: dict[str, str],
    app_id: str,
    dtype: str,
    name: str,
    data: bytes,
    mime: str = "application/pdf",
):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=h,
        data={"document_type": dtype},
        files={"file": (name, io.BytesIO(data), mime)},
    )


def test_upload_creates_document_pending_run_and_audit(client: TestClient, db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = _upload(client, h, app_id, "business_profile", "ACRA_BizProfile.pdf", PDF)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["unchanged"] is False
    assert body["document"]["original_filename"] == "ACRA_BizProfile.pdf"
    assert body["document"]["verification"]["status"] == "pending"
    slot = next(s for s in body["application"]["document_slots"] if s["type"] == "business_profile")
    assert slot["present"] is True and slot["document"]["id"] == body["document"]["id"]
    assert body["application"]["completeness"]["documents_present"] == 1
    doc = db.scalar(select(Document))
    assert (
        doc is not None
        and doc.is_current
        and doc.stored_key != "ACRA_BizProfile.pdf"
        and len(doc.sha256) == 64
    )
    assert db.scalar(select(VerificationRun)) is not None
    assert [e.event_type for e in db.scalars(select(AuditEvent))] == [
        "application.created",
        "document.uploaded",
    ]


def test_replace_supersedes_and_identical_is_unchanged(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    first = _upload(client, h, app_id, "floor_plan", "plan_v1.pdf", PDF).json()["document"]["id"]
    same = _upload(client, h, app_id, "floor_plan", "plan_v1_copy.pdf", PDF)
    assert same.status_code == 201 and same.json()["unchanged"] is True
    assert same.json()["document"]["id"] == first
    replaced = _upload(client, h, app_id, "floor_plan", "plan_v2.pdf", PDF + b"more\n")
    assert replaced.json()["unchanged"] is False
    assert replaced.json()["document"]["id"] != first
    docs = list(db.scalars(select(Document).order_by(Document.uploaded_at)))
    assert [d.is_current for d in docs] == [False, True]
    assert docs[1].supersedes_id == docs[0].id
    events = [e.event_type for e in db.scalars(select(AuditEvent))]
    assert events.count("document.uploaded") == 1 and events.count("document.replaced") == 1
    # exactly one current document per type
    assert len(client.get(f"/api/v1/applications/{app_id}", headers=h).json()["document_slots"]) == 4


def test_rejections(client: TestClient, db: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = _upload(
        client,
        h,
        app_id,
        "floor_plan",
        "plan.docx",
        b"PK\x03\x04",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "unsupported_format"
    r = _upload(client, h, app_id, "floor_plan", "plan.pdf", b"PK\x03\x04 not a pdf")
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "content_mismatch"
    r = _upload(client, h, app_id, "floor_plan", "plan.pdf", b"")
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "empty"
    from app.core import settings as settings_module

    monkeypatch.setattr(settings_module.get_settings(), "upload_max_bytes", 64)
    r = _upload(client, h, app_id, "floor_plan", "plan.pdf", PDF + b"x" * 100)
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "too_large"
    r = _upload(client, h, app_id, "not_a_type", "plan.pdf", PDF)
    assert r.status_code == 422
    assert db.scalar(select(Document)) is None  # nothing persisted from rejected uploads


def test_download_and_ownership(client: TestClient, db: Session) -> None:
    make_user(db, "a@example.sg", Role.OPERATOR)
    make_user(db, "b@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    ha, hb, ho = login(client, "a@example.sg"), login(client, "b@example.sg"), login(client, "off@example.sg")
    app_id = _draft(client, ha)
    doc_id = _upload(client, ha, app_id, "tenancy_agreement", "tenancy.pdf", PDF).json()["document"]["id"]
    r = client.get(f"/api/v1/applications/{app_id}/documents/{doc_id}/download", headers=ha)
    assert (
        r.status_code == 200 and r.content == PDF and r.headers["content-type"].startswith("application/pdf")
    )
    assert (
        client.get(f"/api/v1/applications/{app_id}/documents/{doc_id}/download", headers=hb).status_code
        == 404
    )
    # officer cannot see a draft; document of another application is 404 even for the owner
    assert (
        client.get(f"/api/v1/applications/{app_id}/documents/{doc_id}/download", headers=ho).status_code
        == 404
    )
    other = _draft(client, ha)
    assert (
        client.get(f"/api/v1/applications/{other}/documents/{doc_id}/download", headers=ha).status_code == 404
    )
    assert (
        client.get(f"/api/v1/applications/{app_id}/documents/{uuid.uuid4()}/download", headers=ha).status_code
        == 404
    )


def test_delete_only_in_draft(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    doc_id = _upload(client, h, app_id, "floor_plan", "plan.pdf", PDF).json()["document"]["id"]
    r = client.delete(f"/api/v1/applications/{app_id}/documents/{doc_id}", headers=h)
    assert r.status_code == 200
    assert next(s for s in r.json()["document_slots"] if s["type"] == "floor_plan")["present"] is False
    doc_id = _upload(client, h, app_id, "floor_plan", "plan.pdf", PDF).json()["document"]["id"]
    app = db.get(Application, uuid.UUID(app_id))
    assert app is not None
    app.status = ApplicationStatus.UNDER_REVIEW
    db.commit()
    assert client.delete(f"/api/v1/applications/{app_id}/documents/{doc_id}", headers=h).status_code == 403
    assert _upload(client, h, app_id, "floor_plan", "plan2.pdf", PDF + b"2").status_code == 403
