"""Regression tests from the Sprint 2 edge-case review (docs/11-reviews/EDGE_CASE_REVIEW.md)."""

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
from tests.journeys import PDF, VALID_PREMISES
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
    """TRUSTED_PROXIES=* (a PaaS edge proxy is the only peer): each forwarded client gets its own bucket.
    The client is the hop the proxy appended (the last one); the leading hop is whatever the caller sent."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    limiter = auth_module.login_limiter
    monkeypatch.setattr(limiter, "limit", 2)
    monkeypatch.setattr(auth_module._settings, "trusted_proxies", "*")
    limiter.clear()
    for _ in range(2):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "op@example.sg", "password": "bad"},
            headers={"X-Forwarded-For": "10.0.0.1, 203.0.113.5"},
        )
        assert r.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "op@example.sg", "password": DEFAULT_PASSWORD},
        headers={"X-Forwarded-For": "10.0.0.2, 203.0.113.5"},
    )
    assert blocked.status_code == 429, "a caller-supplied leading hop must not open a fresh bucket"
    other = client.post(
        "/api/v1/auth/login",
        json={"email": "op@example.sg", "password": DEFAULT_PASSWORD, "take_over": True},
        headers={"X-Forwarded-For": "10.0.0.1, 203.0.113.6"},
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


def test_every_body_is_bounded_before_it_is_read(client: TestClient, db: Session) -> None:
    """Review finding, 21 Sep: FastAPI reads a body before the route's dependencies run, so the cap has
    to sit in front of the router: JSON routes at 256 KiB, the two multipart routes at the upload cap,
    a chunked body without a length refused, and all of it before authentication."""
    from app.core.body_limit import JSON_BODY_LIMIT

    limit = get_settings().upload_max_bytes
    # unauthenticated, JSON, one byte over the cap: refused from the header, never buffered
    r = client.patch(
        "/api/v1/applications/00000000-0000-0000-0000-000000000000/sections/premises",
        headers={"Content-Type": "application/json", "Content-Length": str(JSON_BODY_LIMIT + 1)},
        content=b"",
    )
    assert r.status_code == 413 and r.json()["error"]["code"] == "payload_too_large"
    assert "request_id" in r.json()["error"]["details"]
    # the public sign-in route too
    r = client.post(
        "/api/v1/auth/login",
        headers={"Content-Type": "application/json", "Content-Length": str(JSON_BODY_LIMIT * 4)},
        content=b"",
    )
    assert r.status_code == 413
    # the attachment route follows the upload cap, like documents
    r = client.post(
        "/api/v1/applications/00000000-0000-0000-0000-000000000000/clarifications/responses/"
        "00000000-0000-0000-0000-000000000000/attachments",
        headers={"Content-Length": str(limit * 5), "Content-Type": "multipart/form-data; boundary=x"},
        content=b"",
    )
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "too_large"
    # a chunked body carries no length: 411, whatever the route

    def chunks():  # type: ignore[no-untyped-def]
        yield b'{"email": "x@y.sg", "password": "p"}'

    r = client.post("/api/v1/auth/login", headers={"Content-Type": "application/json"}, content=chunks())
    assert r.status_code == 411 and r.json()["error"]["code"] == "length_required"
    # an honest body under the cap goes through as before
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises",
        headers=h,
        json={"address_line_1": "x" * 2000, "postal_code": "208787"},
    )
    assert r.status_code in (200, 422)


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


def test_admin_cannot_download_a_drafts_documents(client: TestClient, db: Session) -> None:
    """Since US-072 an administrator downloads what an officer can; a draft is visible to neither (404)."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "adm@example.sg", Role.ADMIN)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    doc_id = _upload(client, h, app_id, "tenancy_agreement", "t.pdf", PDF).json()["document"]["id"]
    r = client.get(
        f"/api/v1/applications/{app_id}/documents/{doc_id}/download", headers=login(client, "adm@example.sg")
    )
    assert r.status_code == 404


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


def test_bug_hunt_regressions(client: TestClient, db: Session) -> None:
    """20 Sep audit: not-a-uuid path is 404; operator cannot re-run once the document is with the officer;
    a multibyte character on the sniff boundary is still text; undoing a resolve cannot reopen an item
    after the site visit was scheduled."""
    from tests.journeys import add_feedback, submitted, transition

    make_user(db, "solo@example.sg", Role.OPERATOR)
    solo = login(client, "solo@example.sg")
    r = client.get("/api/v1/applications/not-a-uuid", headers=solo)
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"

    app_id = _draft(client, solo)
    boundary = b"A" * 15 + "é and more text after the boundary. Tenancy agreement.".encode()
    r = _upload(client, solo, app_id, "tenancy_agreement", "notes.txt", boundary, "text/plain")
    assert r.status_code == 201, r.text

    app_id, op, off = submitted(client, db)
    doc = client.get(f"/api/v1/applications/{app_id}", headers=op).json()["document_slots"][0]["document"]
    r = client.post(f"/api/v1/applications/{app_id}/documents/{doc['id']}/verify", headers=op)
    assert r.status_code == 403, "operator re-run is closed once the application is with the office"

    transition(client, off, app_id, "under_review")
    add_feedback(client, off, app_id, target_type="section", section_key="premises", message="x")
    body = add_feedback(client, off, app_id, target_type="section", section_key="operations", message="y")
    fid = next(f["id"] for f in body["feedback"] if f["section_key"] == "operations")  # stays open
    transition(client, off, app_id, "pending_pre_site_resubmission")
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises",
        headers=op,
        json={**VALID_PREMISES, "address_line_1": "10 Jalan Besar #01-21"},
    )
    assert r.status_code == 200
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 200
    transition(client, off, app_id, "under_review")
    body = client.post(f"/api/v1/officer/applications/{app_id}/feedback/{fid}/resolve", headers=off).json()
    assert next(f for f in body["feedback"] if f["id"] == fid)["resolution"] == "resolved"
    transition(client, off, app_id, "site_visit_scheduled")
    r = client.post(f"/api/v1/officer/applications/{app_id}/feedback/{fid}/restore", headers=off)
    assert r.status_code == 409, "an undo may not put an open item under a scheduled site visit"
