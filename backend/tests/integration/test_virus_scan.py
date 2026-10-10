"""US-099 / ADR-017: the virus scan, against the real Postgres test database and a fake scanner.

`SCAN_MODE=enforce` is switched on per test; the rest of the suite runs with the scan `off` and is the proof
that the default behaviour is unchanged. The fake scanner replaces only the clamd socket (covered in
tests/unit/test_clamd_client.py); the EICAR test at the bottom talks to a real clamd when CLAMD_HOST is set.
"""

import os
import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.domain.scan import CLEAN, INFECTED, SCANNING
from app.infra import db as dbmod
from app.infra.clamd import ScannerError, ScanResult
from app.models import AuditEvent, ClarificationAttachment, Document, PlatformSetting, User, VerificationRun
from app.models.enums import Role, VerificationStatus
from app.services import scan as scan_module
from app.services import verification as verification_module
from app.services.draft_deletion import DraftDeletionService
from app.services.platform_settings import live
from app.services.verification import MAX_ATTEMPTS, claim_next_run, execute_run, reap_expired_runs
from app.worker import Worker
from tests.conftest import BACKEND_DIR
from tests.factories import login, make_user
from tests.integration.test_clarification import _attach, _respond, _submitted
from tests.journeys import PDF, TXT, complete_draft, draft, submitted, upload

API = "/api/v1"
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
INFECTED_MESSAGE = "This file was blocked by the security check. Upload a different copy."


class FakeScanner:
    """Stands in for ClamdClient: `mode` is clean, infected or down."""

    def __init__(self) -> None:
        self.mode = "clean"
        self.seen: list[bytes] = []
        self.before_reply: Callable[[], None] | None = None

    def scan(self, data: bytes) -> ScanResult:
        self.seen.append(data)
        if self.before_reply:
            self.before_reply()
        if self.mode == "down":
            raise ScannerError("clamd connection failed: ConnectionRefusedError")
        if self.mode == "infected":
            return ScanResult(infected=True, signature="Test.Signature-1")
        return ScanResult(infected=False)


@pytest.fixture
def scanner(monkeypatch: pytest.MonkeyPatch) -> FakeScanner:
    fake = FakeScanner()
    monkeypatch.setattr(get_settings(), "scan_mode", "enforce")
    monkeypatch.setattr(scan_module, "client_from_settings", lambda: fake)
    return fake


@pytest.fixture
def alerts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent: list[str] = []
    monkeypatch.setattr(scan_module.notifier, "notify", sent.append)
    return sent


@pytest.fixture
def ai_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[int]]:
    """How many times a run reached the AI provider."""
    calls: list[int] = []
    real = verification_module.get_provider

    def spy():  # type: ignore[no-untyped-def]
        calls.append(1)
        return real()

    monkeypatch.setattr(verification_module, "get_provider", spy)
    yield calls


@pytest.fixture
def worker_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "verification_mode", "worker")


def _operator(client: TestClient, db: Session, email: str = "op@example.sg") -> dict[str, str]:
    make_user(db, email, Role.OPERATOR)
    return login(client, email)


def _doc(db: Session) -> Document:
    db.expire_all()
    doc = db.scalar(select(Document))
    assert doc is not None
    return doc


def _run(db: Session) -> VerificationRun:
    db.expire_all()
    run = db.scalar(select(VerificationRun).order_by(VerificationRun.created_at.desc()))
    assert run is not None
    return run


def _stored(key: str) -> bool:
    return (Path(get_settings().upload_dir) / key).exists()


def _download(client: TestClient, h: dict[str, str], app_id: str, doc_id: uuid.UUID) -> object:
    return client.get(f"{API}/applications/{app_id}/documents/{doc_id}/download", headers=h)


def _set_fail_mode(db: Session, mode: str) -> None:
    admin = make_user(db, f"adm{uuid.uuid4().hex[:6]}@example.sg", Role.ADMIN)
    db.merge(
        PlatformSetting(
            key="scanner_fail_mode", value=mode, updated_by=admin.id, updated_at=datetime.now(UTC), reason="t"
        )
    )
    db.commit()


# ---- off: today's behaviour ----


def test_scan_off_stores_and_serves_as_before(client: TestClient, db: Session) -> None:
    assert get_settings().scan_mode == "off"
    h = _operator(client, db)
    app_id = draft(client, h)
    body = upload(client, h, app_id, "floor_plan", "plan.pdf", PDF).json()
    assert body["document"]["scan_state"] is None
    doc = _doc(db)
    assert (
        doc.scan_state is None
        and not doc.stored_key.startswith("quarantine/")
        and doc.active_content is False
    )
    assert _download(client, h, app_id, doc.id).status_code == 200  # type: ignore[attr-defined]


# ---- enforce: clean ----


def test_clean_file_is_released_from_quarantine_and_served(
    client: TestClient, db: Session, scanner: FakeScanner, ai_calls: list[int]
) -> None:
    h = _operator(client, db)
    app_id = draft(client, h)
    r = upload(client, h, app_id, "business_profile", "profile.txt", TXT, "text/plain")
    assert r.json()["document"]["scan_state"] == SCANNING  # the response is written before the check runs
    doc = _doc(db)
    assert doc.scan_state == CLEAN and not doc.stored_key.startswith("quarantine/")
    assert _stored(doc.stored_key) and not _stored("quarantine/" + doc.stored_key)
    assert scanner.seen == [TXT]
    assert _run(db).status != VerificationStatus.PENDING and ai_calls  # the check went on to the provider
    got = _download(client, h, app_id, doc.id)
    assert got.status_code == 200 and got.content == TXT  # type: ignore[attr-defined]
    view = client.get(f"{API}/applications/{app_id}", headers=h).json()
    slot = next(s for s in view["document_slots"] if s["type"] == "business_profile")
    assert slot["document"]["scan_state"] == CLEAN


def test_a_file_is_quarantined_while_it_waits_for_its_scan(
    client: TestClient, db: Session, scanner: FakeScanner, worker_mode: None
) -> None:
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "floor_plan", "plan.pdf", PDF)
    doc = _doc(db)
    assert doc.scan_state == SCANNING and doc.stored_key.startswith("quarantine/") and _stored(doc.stored_key)
    got = _download(client, h, app_id, doc.id)
    assert got.status_code == 409 and got.json()["error"]["code"] == "file_scanning"  # type: ignore[attr-defined]
    assert scanner.seen == []  # the API itself never scans in worker mode
    run_id = claim_next_run("w1")
    assert run_id is not None
    execute_run(run_id, "w1")
    doc = _doc(db)
    assert doc.scan_state == CLEAN and _stored(doc.stored_key) and not _stored("quarantine/" + doc.stored_key)
    assert _download(client, h, app_id, doc.id).status_code == 200  # type: ignore[attr-defined]


# ---- enforce: infected ----


def test_infected_file_is_blocked_everywhere_and_never_reaches_the_ai(
    client: TestClient, db: Session, scanner: FakeScanner, alerts: list[str], ai_calls: list[int]
) -> None:
    scanner.mode = "infected"
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "floor_plan", "private-plan.pdf", PDF)
    doc = _doc(db)
    assert doc.scan_state == INFECTED and doc.scan_signature == "Test.Signature-1"
    assert doc.stored_key.startswith("quarantine/") and _stored(doc.stored_key)  # stays quarantined
    assert ai_calls == []  # before any extraction or model call
    run = _run(db)
    assert run.status == VerificationStatus.UNREADABLE and run.error_reason == "file_infected"
    got = _download(client, h, app_id, doc.id)
    assert got.status_code == 403  # type: ignore[attr-defined]
    assert got.json()["error"] == {"code": "file_infected", "message": INFECTED_MESSAGE}  # type: ignore[attr-defined]
    view = client.get(f"{API}/applications/{app_id}", headers=h).json()
    slot = next(s for s in view["document_slots"] if s["type"] == "floor_plan")["document"]
    assert slot["scan_state"] == INFECTED and slot["verification"]["error_reason"] == "file_infected"
    # audit event, and one Telegram message without a file name or a person
    event = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "document.infected"))
    assert event is not None and event.payload["signature"] == "Test.Signature-1"
    assert len(alerts) == 1
    assert (
        "Test.Signature-1" in alerts[0]
        and "private-plan" not in alerts[0]
        and "op@example.sg" not in alerts[0]
    )


def test_a_rerun_on_an_infected_file_does_not_scan_it_again(
    client: TestClient, db: Session, scanner: FakeScanner, alerts: list[str]
) -> None:
    scanner.mode = "infected"
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "floor_plan", "plan.pdf", PDF)
    doc = _doc(db)
    scanner.mode = "clean"  # a later, different answer must not release it
    assert client.post(f"{API}/applications/{app_id}/documents/{doc.id}/verify", headers=h).status_code == 202
    assert _doc(db).scan_state == INFECTED and len(scanner.seen) == 1 and len(alerts) == 1
    assert _run(db).error_reason == "file_infected"


def test_officer_and_admin_are_refused_a_blocked_file_with_their_own_wording(
    client: TestClient, db: Session
) -> None:
    app_id, op, off = submitted(client, db)
    make_user(db, "adm@example.sg", Role.ADMIN)
    adm = login(client, "adm@example.sg")
    doc = _doc(db)
    assert _download(client, off, app_id, doc.id).status_code == 200  # type: ignore[attr-defined]  # NULL: legacy
    db.execute(update(Document).where(Document.id == doc.id).values(scan_state=INFECTED, active_content=True))
    db.commit()
    for h in (off, adm):
        got = _download(client, h, app_id, doc.id)
        assert got.status_code == 403  # type: ignore[attr-defined]
        assert got.json()["error"]["code"] == "file_infected"  # type: ignore[attr-defined]
        assert "cannot be opened" in got.json()["error"]["message"]  # type: ignore[attr-defined]
    case = client.get(f"{API}/officer/applications/{app_id}", headers=off).json()
    flagged = next(d for d in case["documents"] if d["id"] == str(doc.id))
    assert flagged["scan_state"] == INFECTED and flagged["active_content"] is True
    db.execute(update(Document).where(Document.id == doc.id).values(scan_state=SCANNING))
    db.commit()
    assert _download(client, off, app_id, doc.id).status_code == 409  # type: ignore[attr-defined]


# ---- enforce: the scanner is down (no verdict is never clean) ----


def test_scanner_down_holds_the_file_and_never_marks_it_clean(
    client: TestClient, db: Session, scanner: FakeScanner, alerts: list[str], ai_calls: list[int]
) -> None:
    scanner.mode = "down"
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "floor_plan", "plan.pdf", PDF)
    doc = _doc(db)
    assert doc.scan_state == SCANNING and doc.stored_key.startswith("quarantine/")
    assert ai_calls == []
    run = _run(db)
    assert run.status == VerificationStatus.UNAVAILABLE and run.error_reason == "scanner_unavailable"
    assert _download(client, h, app_id, doc.id).status_code == 409  # type: ignore[attr-defined]
    assert len(alerts) == 1 and "scanner" in alerts[0]  # inline mode never retries by itself: say so
    # a person re-runs the check once the scanner is back
    scanner.mode = "clean"
    assert client.post(f"{API}/applications/{app_id}/documents/{doc.id}/verify", headers=h).status_code == 202
    assert _doc(db).scan_state == CLEAN


def test_worker_retries_a_held_file_later_then_gives_up_after_the_attempts(
    client: TestClient, db: Session, scanner: FakeScanner, worker_mode: None, ai_calls: list[int]
) -> None:
    scanner.mode = "down"
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "business_profile", "profile.txt", TXT, "text/plain")
    first = claim_next_run("w1")
    assert first is not None
    execute_run(first, "w1")
    run = _run(db)
    assert run.status == VerificationStatus.UNAVAILABLE and run.attempts == 1
    assert reap_expired_runs() == (0, 0)  # too soon: the retry waits

    def age() -> None:
        db.execute(update(VerificationRun).values(finished_at=datetime.now(UTC) - timedelta(minutes=2)))
        db.commit()

    age()
    assert reap_expired_runs()[0] == 1  # queued again
    assert _run(db).status == VerificationStatus.PENDING
    scanner.mode = "clean"  # the scanner is back
    again = claim_next_run("w1")
    assert again == first
    execute_run(again, "w1")
    assert _doc(db).scan_state == CLEAN and _run(db).status != VerificationStatus.UNAVAILABLE and ai_calls

    # a file that stays unscanned is retried only MAX_ATTEMPTS times
    db.execute(update(Document).values(scan_state=SCANNING))
    db.execute(
        update(VerificationRun).values(
            status=VerificationStatus.UNAVAILABLE,
            error_reason="scanner_unavailable",
            attempts=MAX_ATTEMPTS,
            finished_at=datetime.now(UTC) - timedelta(minutes=5),
        )
    )
    db.commit()
    assert reap_expired_runs() == (0, 0)


def test_hold_fail_mode_holds_without_retrying_and_never_releases(
    client: TestClient, db: Session, scanner: FakeScanner, worker_mode: None, alerts: list[str]
) -> None:
    _set_fail_mode(db, "hold")
    scanner.mode = "down"
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "floor_plan", "plan.pdf", PDF)
    run_id = claim_next_run("w1")
    assert run_id is not None
    execute_run(run_id, "w1")
    db.execute(update(VerificationRun).values(finished_at=datetime.now(UTC) - timedelta(minutes=5)))
    db.commit()
    assert reap_expired_runs() == (0, 0)  # no automatic retry
    doc = _doc(db)
    assert doc.scan_state == SCANNING and doc.stored_key.startswith("quarantine/")
    assert _download(client, h, app_id, doc.id).status_code == 409  # type: ignore[attr-defined]
    assert len(alerts) == 1  # nobody will retry it, so someone is told


def test_a_draft_deleted_during_the_scan_leaves_nothing_behind(
    client: TestClient, db: Session, scanner: FakeScanner
) -> None:
    h = _operator(client, db)
    app_id = draft(client, h)
    operator = db.scalar(select(User).where(User.email == "op@example.sg"))
    assert operator is not None

    def delete_the_draft() -> None:
        with dbmod.session_factory()() as other:
            DraftDeletionService(other).delete(operator, uuid.UUID(app_id))

    scanner.before_reply = delete_the_draft
    upload(client, h, app_id, "floor_plan", "plan.pdf", PDF)
    assert db.scalar(select(Document)) is None
    root = Path(get_settings().upload_dir)
    assert not any(p.is_file() for p in root.rglob("*"))  # neither the quarantine copy nor a released one


def test_pdf_active_content_is_flagged_but_not_blocked(
    client: TestClient, db: Session, scanner: FakeScanner
) -> None:
    h = _operator(client, db)
    app_id = draft(client, h)
    risky = PDF + b"<< /OpenAction << /S /JavaScript /JS (app.alert(1)) >> >>\n"
    upload(client, h, app_id, "floor_plan", "plan.pdf", risky)
    doc = _doc(db)
    assert doc.scan_state == CLEAN and doc.active_content is True
    assert _download(client, h, app_id, doc.id).status_code == 200  # type: ignore[attr-defined]
    upload(client, h, app_id, "tenancy_agreement", "plain.pdf", PDF)
    plain = db.scalar(select(Document).where(Document.original_filename == "plain.pdf"))
    assert plain is not None and plain.active_content is False


def test_clean_scan_metric_counts_results(client: TestClient, db: Session, scanner: FakeScanner) -> None:
    from prometheus_client import REGISTRY

    def count(result: str) -> float:
        return REGISTRY.get_sample_value("permitflow_scans_total", {"result": result}) or 0.0

    before = {r: count(r) for r in ("clean", "infected", "error")}
    h = _operator(client, db)
    app_id = draft(client, h)
    for mode, name in (("clean", "a.pdf"), ("infected", "b.pdf"), ("down", "c.pdf")):
        scanner.mode = mode
        upload(client, h, app_id, "floor_plan", name, PDF + name.encode())
    assert {r: count(r) - before[r] for r in before} == {"clean": 1, "infected": 1, "error": 1}


# ---- a paused AI never holds the scan ----


def _pause(db: Session, paused: bool) -> None:
    admin = make_user(db, f"adm{uuid.uuid4().hex[:6]}@example.sg", Role.ADMIN)
    db.merge(
        PlatformSetting(
            key="ai_paused", value=paused, updated_by=admin.id, updated_at=datetime.now(UTC), reason="t"
        )
    )
    db.commit()
    live().refresh()


def test_an_upload_during_an_ai_pause_is_still_scanned(
    client: TestClient, db: Session, scanner: FakeScanner, ai_calls: list[int]
) -> None:
    _pause(db, True)
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "business_profile", "profile.txt", TXT, "text/plain")
    doc = _doc(db)
    assert (
        doc.scan_state == CLEAN and not doc.stored_key.startswith("quarantine/") and _stored(doc.stored_key)
    )
    run = _run(db)
    assert run.status == VerificationStatus.UNAVAILABLE and run.error_reason == "ai_paused"
    assert ai_calls == [] and scanner.seen == [TXT]
    assert _download(client, h, app_id, doc.id).status_code == 200  # type: ignore[attr-defined]


def test_the_worker_scans_a_queued_file_while_paused_and_keeps_the_check_queued(
    client: TestClient, db: Session, scanner: FakeScanner, worker_mode: None, ai_calls: list[int]
) -> None:
    h = _operator(client, db)
    app_id = draft(client, h)
    upload(client, h, app_id, "business_profile", "profile.txt", TXT, "text/plain")
    assert _doc(db).scan_state == SCANNING
    _pause(db, True)
    w = Worker()
    assert w.fill_slots() == 1  # claimed for the scan only
    for t in list(w._active.values()):
        t.join(20)
    doc = _doc(db)
    assert doc.scan_state == CLEAN and _stored(doc.stored_key)
    run = _run(db)
    assert run.status == VerificationStatus.PENDING and run.attempts == 0 and run.worker_id is None
    assert ai_calls == []  # the AI step is still held
    assert w.fill_slots() == 0  # nothing left to scan: the check stays queued
    _pause(db, False)
    assert w.fill_slots() == 1
    for t in list(w._active.values()):
        t.join(20)
    assert _run(db).status != VerificationStatus.PENDING and ai_calls


# ---- submission needs every document clear ----


def _ready(client: TestClient, db: Session) -> tuple[str, dict[str, str]]:
    h = _operator(client, db)
    app_id = complete_draft(client, h)
    return app_id, h


def _submit(client: TestClient, h: dict[str, str], app_id: str) -> object:
    return client.post(f"{API}/applications/{app_id}/submit", headers=h)


@pytest.mark.parametrize("state", [SCANNING, INFECTED])
def test_submission_is_refused_while_a_document_is_scanning_or_blocked(
    client: TestClient, db: Session, scanner: FakeScanner, state: str
) -> None:
    app_id, h = _ready(client, db)
    doc = db.scalars(select(Document).order_by(Document.uploaded_at)).first()
    assert doc is not None and doc.scan_state == CLEAN
    db.execute(update(Document).where(Document.id == doc.id).values(scan_state=state))
    db.commit()
    r = _submit(client, h, app_id)
    assert r.status_code == 409  # type: ignore[attr-defined]
    error = r.json()["error"]  # type: ignore[attr-defined]
    assert error["code"] == "documents_not_clear"
    assert error["message"] == "Review and submit opens when no document is blocked or being scanned."
    db.execute(update(Document).where(Document.id == doc.id).values(scan_state=CLEAN))
    db.commit()
    assert _submit(client, h, app_id).status_code == 200  # type: ignore[attr-defined]


def test_submission_is_unchanged_with_the_scan_off(client: TestClient, db: Session) -> None:
    app_id, h = _ready(client, db)
    assert get_settings().scan_mode == "off"
    db.execute(update(Document).values(scan_state=SCANNING))  # nothing reads it with the scan off
    db.commit()
    assert _submit(client, h, app_id).status_code == 200  # type: ignore[attr-defined]


# ---- clarification attachments ----


def _response_id(client: TestClient, op: dict[str, str], app_id: str) -> str:
    view = client.get(f"{API}/applications/{app_id}/clarifications", headers=op).json()
    item = next(i for i in view["items"] if i["key"] == "coved_edges")
    r = _respond(client, op, app_id, item["item_id"], "Coving done on 24 Sep.")
    assert r.status_code == 200, r.text
    return str(next(i for i in r.json()["items"] if i["key"] == "coved_edges")["responses"][0]["id"])


def test_attachment_is_scanned_in_its_upload_request(
    client: TestClient, db: Session, scanner: FakeScanner
) -> None:
    app_id, op, off = _submitted(client, db)
    response_id = _response_id(client, op, app_id)
    r = _attach(client, op, app_id, response_id, "coving.pdf", PDF)
    assert r.status_code == 201, r.text
    row = db.scalar(select(ClarificationAttachment))
    assert row is not None and row.scan_state == CLEAN and not row.stored_key.startswith("quarantine/")
    assert _stored(row.stored_key) and not _stored("quarantine/" + row.stored_key)
    url = f"{API}/applications/{app_id}/clarifications/attachments/{row.id}/download"
    assert client.get(url, headers=op).status_code == 200
    assert client.get(url, headers=off).status_code == 200


def test_infected_attachment_is_rejected_kept_quarantined_and_blocks_the_send(
    client: TestClient, db: Session, scanner: FakeScanner, alerts: list[str]
) -> None:
    app_id, op, off = _submitted(client, db)
    response_id = _response_id(client, op, app_id)
    scanner.mode = "infected"
    r = _attach(client, op, app_id, response_id, "private.pdf", PDF)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "file_infected" and r.json()["error"]["message"] == INFECTED_MESSAGE
    row = db.scalar(select(ClarificationAttachment))
    assert row is not None and row.scan_state == INFECTED and row.stored_key.startswith("quarantine/")
    assert _stored(row.stored_key)
    url = f"{API}/applications/{app_id}/clarifications/attachments/{row.id}/download"
    for h in (op, off):
        assert client.get(url, headers=h).status_code == 403
    assert db.scalar(select(AuditEvent).where(AuditEvent.event_type == "clarification.attachment_infected"))
    assert len(alerts) == 1 and "private" not in alerts[0]
    view = client.get(f"{API}/applications/{app_id}/clarifications", headers=op).json()
    coved = next(i for i in view["items"] if i["key"] == "coved_edges")
    assert coved["responses"][0]["attachments"][0]["scan_state"] == INFECTED
    # the answers cannot be sent with a blocked file on them, until it is removed
    for item in view["items"]:
        if item["key"] != "coved_edges":
            _respond(client, op, app_id, item["item_id"], "Done.")
    sent = client.post(f"{API}/applications/{app_id}/clarifications/send", headers=op)
    assert sent.status_code == 422 and sent.json()["error"]["code"] == "file_infected"
    removed = client.delete(
        f"{API}/applications/{app_id}/clarifications/responses/{response_id}/attachments/{row.id}", headers=op
    )
    assert removed.status_code == 200 and not _stored(row.stored_key)
    assert client.post(f"{API}/applications/{app_id}/clarifications/send", headers=op).status_code == 200


def test_attachment_with_the_scanner_down_is_refused_and_nothing_is_kept(
    client: TestClient, db: Session, scanner: FakeScanner
) -> None:
    app_id, op, _ = _submitted(client, db)
    response_id = _response_id(client, op, app_id)
    scanner.mode = "down"
    r = _attach(client, op, app_id, response_id, "coving.pdf", PDF)
    assert r.status_code == 503 and r.json()["error"]["code"] == "scanner_unavailable"
    assert db.scalar(select(ClarificationAttachment)) is None
    root = Path(get_settings().upload_dir)
    assert not any("quarantine" in str(p) for p in root.rglob("*") if p.is_file())


# ---- the migration ----


def test_migration_0018_downgrades_cleanly_and_upgrades_back(client: TestClient, db: Session) -> None:
    h = _operator(client, db)
    upload(client, h, draft(client, h), "floor_plan", "plan.pdf", PDF)
    db.close()
    dbmod.reset_engine()

    def alembic(*args: str) -> None:
        subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=BACKEND_DIR,
            env={**os.environ, "APP_ENV": "test"},
            check=True,
            capture_output=True,
        )

    def columns() -> set[str]:
        with dbmod.get_engine().connect() as conn:
            rows = conn.execute(
                text(
                    "select table_name || '.' || column_name from information_schema.columns "
                    "where column_name in ('scan_state', 'scan_signature', 'active_content')"
                )
            )
            return {r[0] for r in rows}

    wanted = {
        f"{t}.{c}"
        for t in ("documents", "clarification_attachments")
        for c in ("scan_state", "scan_signature", "active_content")
    }
    assert columns() == wanted
    admin = make_user(db, "adm-mig@example.sg", Role.ADMIN)
    for key, value in (("scanner_fail_mode", "hold"), ("rate_limit_per_minute", 100)):
        db.add(PlatformSetting(key=key, value=value, updated_by=admin.id, reason="t"))
    db.commit()
    db.close()
    dbmod.reset_engine()

    def stored() -> dict[str, object]:
        with dbmod.get_engine().connect() as conn:
            return {r[0]: r[1] for r in conn.execute(text("select key, value from platform_settings"))}

    alembic("downgrade", "0016")
    try:
        dbmod.reset_engine()
        assert columns() == set()
        assert stored() == {"scanner_fail_mode": "open", "rate_limit_per_minute": 100}  # the old words
    finally:
        dbmod.reset_engine()
        alembic("upgrade", "head")
        dbmod.reset_engine()
    assert columns() == wanted
    assert stored()["scanner_fail_mode"] == "hold"


# ---- the real scanner ----


@pytest.mark.skipif(
    not os.environ.get("CLAMD_HOST"), reason="needs a running clamd: set CLAMD_HOST (and CLAMD_PORT)"
)
def test_eicar_is_rejected_end_to_end_against_a_real_clamd(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, alerts: list[str]
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "scan_mode", "enforce")
    monkeypatch.setattr(settings, "clamd_host", os.environ["CLAMD_HOST"])
    monkeypatch.setattr(settings, "clamd_port", int(os.environ.get("CLAMD_PORT", "3310")))
    h = _operator(client, db, "eicar-op@example.sg")
    app_id = draft(client, h)
    # a clean text file passes through the real scanner and is served
    upload(client, h, app_id, "business_profile", "profile.txt", TXT, "text/plain")
    clean = _doc(db)
    assert clean.scan_state == CLEAN
    assert _download(client, h, app_id, clean.id).status_code == 200  # type: ignore[attr-defined]
    # the EICAR test string is blocked
    upload(client, h, app_id, "floor_plan", "eicar.txt", EICAR, "text/plain")
    infected = db.scalar(select(Document).where(Document.original_filename == "eicar.txt"))
    assert infected is not None and infected.scan_state == INFECTED
    assert infected.scan_signature and "eicar" in infected.scan_signature.lower()
    assert infected.stored_key.startswith("quarantine/")
    got = _download(client, h, app_id, infected.id)
    assert got.status_code == 403 and got.json()["error"]["code"] == "file_infected"  # type: ignore[attr-defined]
    assert len(alerts) == 1
    # the same string as clarification evidence
    clar_app, op, _ = _submitted(client, db)
    r = _attach(client, op, clar_app, _response_id(client, op, clar_app), "eicar.txt", EICAR, "text/plain")
    assert r.status_code == 422 and r.json()["error"]["code"] == "file_infected"
