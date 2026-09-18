"""Regression tests from the Sprint 2 edge-case review (docs/reviews/EDGE_CASE_REVIEW.md)."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1 import auth as auth_module
from app.core.settings import get_settings
from app.domain.enums import IssueCode, VerificationStatus
from app.domain.verification_rules import VerificationResult, apply_rules
from app.models import AuditEvent, Document, VerificationRun
from app.models.enums import Role
from app.services.verification import mark_stale_runs_failed
from tests.factories import DEFAULT_PASSWORD, login, make_user
from tests.journeys import PDF
from tests.journeys import draft as _draft
from tests.journeys import upload as _upload


def test_forwarded_for_is_ignored_from_untrusted_clients(
    client: TestClient, db: Session, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    make_user(db, "op@example.sg", Role.OPERATOR)
    limiter = auth_module.login_limiter
    monkeypatch.setattr(limiter, "limit", 3)
    limiter.clear()
    for i in range(3):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "op@example.sg", "password": "bad"},
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        )
        assert r.status_code == 401
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "op@example.sg", "password": DEFAULT_PASSWORD},
        headers={"X-Forwarded-For": "10.0.0.99"},
    )
    assert r.status_code == 429, "a fresh X-Forwarded-For must not open a fresh bucket"
    limiter.clear()


def test_forwarded_for_is_honoured_behind_a_wildcard_trusted_proxy(
    client: TestClient, db: Session, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """TRUSTED_PROXIES=* (a PaaS edge proxy is the only peer): each forwarded client gets its own bucket."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    limiter = auth_module.login_limiter
    monkeypatch.setattr(limiter, "limit", 2)
    monkeypatch.setattr(auth_module._settings, "trusted_proxies", "*")
    limiter.clear()
    for _ in range(2):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "op@example.sg", "password": "bad"},
            headers={"X-Forwarded-For": "203.0.113.5, 10.0.0.1"},
        )
        assert r.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "op@example.sg", "password": DEFAULT_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.5, 10.0.0.1"},
    )
    assert blocked.status_code == 429
    other = client.post(
        "/api/v1/auth/login",
        json={"email": "op@example.sg", "password": DEFAULT_PASSWORD},
        headers={"X-Forwarded-For": "203.0.113.6, 10.0.0.1"},
    )
    assert other.status_code == 200, "another client behind the same proxy is not blocked"
    limiter.clear()


def test_successful_login_does_not_reset_failure_window(client: TestClient, db: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    make_user(db, "victim@example.sg", Role.OPERATOR)
    make_user(db, "mine@example.sg", Role.OPERATOR)
    limiter = auth_module.login_limiter
    monkeypatch.setattr(limiter, "limit", 4)
    limiter.clear()
    for _ in range(2):
        client.post("/api/v1/auth/login", json={"email": "victim@example.sg", "password": "bad"})
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": "mine@example.sg", "password": DEFAULT_PASSWORD}
        ).status_code
        == 200
    )
    for _ in range(2):
        client.post("/api/v1/auth/login", json={"email": "victim@example.sg", "password": "bad"})
    r = client.post("/api/v1/auth/login", json={"email": "victim@example.sg", "password": DEFAULT_PASSWORD})
    assert r.status_code == 429
    limiter.clear()


def test_unknown_email_still_costs_a_hash_check(client: TestClient, db: Session) -> None:
    # Behavioural check only: both paths answer with the same generic 401 body.
    make_user(db, "op@example.sg", Role.OPERATOR)
    a = client.post("/api/v1/auth/login", json={"email": "nobody@example.sg", "password": "x"})
    b = client.post("/api/v1/auth/login", json={"email": "op@example.sg", "password": "x"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_oversized_content_length_is_rejected_before_the_body(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    limit = get_settings().upload_max_bytes
    r = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers={**h, "Content-Length": str(limit * 5), "Content-Type": "multipart/form-data; boundary=x"},
        content=b"",
    )
    assert r.status_code == 400
    assert r.json()["error"]["details"]["reason"] == "too_large"


def test_rejected_upload_leaves_no_part_file(client: TestClient, db: Session, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    monkeypatch.setattr(get_settings(), "upload_max_bytes", 64)
    r = _upload(client, h, app_id, "floor_plan", "plan.pdf", PDF + b"x" * 200)
    assert r.status_code == 400
    leftovers = list(Path(get_settings().upload_dir).rglob("*.part"))
    assert leftovers == []


def test_download_handles_non_latin_filename_and_missing_file(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    doc_id = _upload(client, h, app_id, "tenancy_agreement", "租约 agreement.pdf", PDF).json()["document"][
        "id"
    ]
    r = client.get(f"/api/v1/applications/{app_id}/documents/{doc_id}/download", headers=h)
    assert r.status_code == 200
    assert "filename*=UTF-8''" in r.headers["content-disposition"]
    doc = db.get(Document, uuid.UUID(doc_id))
    assert doc is not None
    (Path(get_settings().upload_dir) / doc.stored_key).unlink()
    r = client.get(f"/api/v1/applications/{app_id}/documents/{doc_id}/download", headers=h)
    assert r.status_code == 404


def test_admin_cannot_download_documents(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "adm@example.sg", Role.ADMIN)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    doc_id = _upload(client, h, app_id, "tenancy_agreement", "t.pdf", PDF).json()["document"]["id"]
    r = client.get(
        f"/api/v1/applications/{app_id}/documents/{doc_id}/download", headers=login(client, "adm@example.sg")
    )
    assert r.status_code == 403


def test_nan_in_a_number_field_is_422_not_500(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises",
        headers={**h, "Content-Type": "application/json"},
        content=b'{"floor_area_sqm": NaN}',
    )
    assert r.status_code == 422
    assert "floor_area_sqm" in r.json()["error"]["details"]["fields"]


def test_section_save_is_audited_with_field_names_only(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    client.patch(
        f"/api/v1/applications/{app_id}/sections/business", headers=h, json={"business_name": "Kopi"}
    )
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.event_type == "section.updated")))
    assert len(events) == 1
    assert events[0].payload == {"section": "business", "fields": ["business_name"]}
    assert "Kopi" not in str(events[0].payload)


def test_injection_beats_model_declared_unreadable() -> None:
    r = VerificationResult(status="unreadable", confidence=0.2, summary="x")
    out = apply_rules(r, confidence_threshold=0.6, injection_phrases=["ignore previous instructions"])
    assert out.status == VerificationStatus.NEEDS_REVIEW
    assert out.issues[-1]["code"] == IssueCode.POSSIBLE_PROMPT_INJECTION.value


def test_stale_pending_runs_are_failed_on_startup(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    doc_id = uuid.UUID(_upload(client, h, app_id, "floor_plan", "p.pdf", PDF).json()["document"]["id"])
    # Make the pending run look old, as if the process died before the task ran.
    run = db.scalar(select(VerificationRun).where(VerificationRun.document_id == doc_id))
    assert run is not None
    run.status = VerificationStatus.PENDING
    run.created_at = datetime.now(UTC) - timedelta(hours=1)
    db.commit()
    assert mark_stale_runs_failed() >= 1
    db.refresh(run)
    assert run.status == VerificationStatus.FAILED and run.error_reason == "interrupted"
    # And a re-run is possible again.
    r = client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/verify", headers=h)
    assert r.status_code == 202
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.event_type == "verification.requested")))
    assert len(events) == 1
