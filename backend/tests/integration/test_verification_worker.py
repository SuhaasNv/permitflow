"""US-098 / ADR-016: the verification queue and worker, against the real Postgres test database.

`VERIFICATION_MODE=worker` is switched on per test; the rest of the suite runs in the default `inline` mode
and is the proof that inline behaviour is unchanged.
"""

import os
import signal
import subprocess
import sys
import threading
import time
import uuid
import zlib
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app import worker as worker_module
from app.core.settings import get_settings
from app.domain.verification_rules import VerificationRequest, VerificationResult
from app.infra import db as dbmod
from app.infra.ai.mock import MockProvider
from app.infra.extraction import Extracted, extract_text
from app.models import AuditEvent, Document, PlatformSetting, User, VerificationRun
from app.models.enums import Role, VerificationStatus
from app.services import verification as module
from app.services.metrics import refresh_queue_gauges
from app.services.platform_settings import live
from app.services.verification import (
    MAX_ATTEMPTS,
    claim_next_run,
    execute_run,
    reap_expired_runs,
    start_run,
)
from app.worker import Worker
from tests.conftest import BACKEND_DIR
from tests.factories import login, make_user
from tests.journeys import VALID_BUSINESS, upload

PROFILE_TXT = (
    "ACRA Business Profile. Entity name: Kopi & Kaya Toast House Pte. Ltd. UEN: 202312345K. Registered 2023. "
    * 4
).encode()


@pytest.fixture
def worker_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(get_settings(), "verification_mode", "worker")
    yield


def _queued(client: TestClient, db: Session, name: str = "profile.txt", data: bytes = PROFILE_TXT,
            mime: str = "text/plain") -> tuple[uuid.UUID, str, dict[str, str]]:  # fmt: skip
    """An operator uploads a document in worker mode: the API only queues the check. Returns the run id,
    the application id and the operator's headers."""
    if db.scalar(select(User).where(User.email == "op@example.sg")) is None:
        make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = str(client.post("/api/v1/applications", headers=h).json()["id"])
    client.patch(f"/api/v1/applications/{app_id}/sections/business", headers=h, json=VALID_BUSINESS)
    r = upload(client, h, app_id, "business_profile", name, data, mime)
    assert r.status_code == 201, r.text
    run = db.scalars(select(VerificationRun).order_by(VerificationRun.created_at.desc())).first()
    assert run is not None
    return run.id, app_id, h


def _run(db: Session, run_id: uuid.UUID) -> VerificationRun:
    db.expire_all()
    run = db.get(VerificationRun, run_id)
    assert run is not None
    return run


def _expire(db: Session, run_id: uuid.UUID) -> None:
    db.execute(
        update(VerificationRun)
        .where(VerificationRun.id == run_id)
        .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
    )
    db.commit()


def _pdf(operators: int = 0) -> bytes:
    """A one-page PDF saying "hi", followed by `operators` drawing operators. With 5 million of them it is a
    5 KB file whose content stream inflates to 10 MB: pypdf needs several seconds and several hundred MB to
    walk it, far beyond any limit the tests set."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    fonts = DictionaryObject({NameObject("/F1"): writer._add_object(font)})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
    stream = StreamObject()
    stream._data = zlib.compress(b"BT /F1 12 Tf (hi) Tj ET\n" + b"q\n" * operators)
    stream[NameObject("/Filter")] = NameObject("/FlateDecode")
    page[NameObject("/Contents")] = writer._add_object(stream)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _bomb_pdf() -> bytes:
    return _pdf(5_000_000)


# ---- the API only queues ----


def test_worker_mode_queues_and_inline_does_not(client: TestClient, db: Session, worker_mode: None) -> None:
    run_id, app_id, h = _queued(client, db)
    run = _run(db, run_id)
    assert run.status == VerificationStatus.PENDING and run.attempts == 0 and run.lease_until is None
    view = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    slot = next(s for s in view["document_slots"] if s["type"] == "business_profile")
    assert slot["document"]["verification"]["status"] == "pending"  # the label operators already know


def test_start_run_notifies_a_listener(client: TestClient, db: Session, worker_mode: None) -> None:
    run_id, _, _ = _queued(client, db)
    with dbmod.listen_connection() as conn:
        conn.execute("LISTEN verification_runs")
        start_run(run_id)
        assert [n.channel for n in conn.notifies(timeout=3.0, stop_after=1)] == ["verification_runs"]


def test_listener_thread_wakes_the_worker(client: TestClient, db: Session, worker_mode: None) -> None:
    run_id, _, _ = _queued(client, db)
    w = Worker()
    thread = threading.Thread(target=w._listen, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not w.wake.is_set() and time.monotonic() < deadline:
            start_run(run_id)  # repeated until the listener has connected and LISTENs
            time.sleep(0.2)
        assert w.wake.is_set()
    finally:
        w.stop.set()
        thread.join(5)


# ---- claims ----


def test_two_workers_never_claim_the_same_run(client: TestClient, db: Session, worker_mode: None) -> None:
    first, _, _ = _queued(client, db)
    doc_id = _run(db, first).document_id
    ids = [first] + [uuid.uuid4() for _ in range(29)]
    db.add_all(VerificationRun(id=i, document_id=doc_id) for i in ids[1:])
    db.commit()

    claimed: dict[str, list[uuid.UUID]] = {f"w{n}": [] for n in range(6)}
    barrier = threading.Barrier(len(claimed))

    def drain(name: str) -> None:
        barrier.wait()
        while (run_id := claim_next_run(name)) is not None:
            claimed[name].append(run_id)

    threads = [threading.Thread(target=drain, args=(n,)) for n in claimed]
    [t.start() for t in threads]
    [t.join(30) for t in threads]

    everything = [r for runs in claimed.values() for r in runs]
    assert sorted(everything) == sorted(ids)  # all claimed, none twice
    for name, runs in claimed.items():
        for run_id in runs:
            run = _run(db, run_id)
            assert run.status == VerificationStatus.RUNNING and run.worker_id == name and run.attempts == 1
            assert run.lease_until is not None and run.lease_until > datetime.now(UTC)


def test_claim_takes_the_oldest_first_and_ignores_finished_runs(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    older, _, _ = _queued(client, db)
    doc_id = _run(db, older).document_id
    newer = VerificationRun(document_id=doc_id, created_at=datetime.now(UTC) + timedelta(seconds=5))
    done = VerificationRun(document_id=doc_id, status=VerificationStatus.VERIFIED)
    db.add_all([newer, done])
    db.commit()
    assert claim_next_run("w") == older
    assert claim_next_run("w") == newer.id
    assert claim_next_run("w") is None


# ---- lease, reaper, dead ----


def test_killed_worker_is_recovered_and_the_third_expiry_is_dead(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    run_id, app_id, h = _queued(client, db)
    for attempt in range(1, MAX_ATTEMPTS):
        assert claim_next_run("doomed") == run_id  # the worker takes it, then dies: nothing finishes it
        assert reap_expired_runs() == (0, 0)  # lease still good
        _expire(db, run_id)
        assert reap_expired_runs() == (1, 0)
        run = _run(db, run_id)
        assert run.status == VerificationStatus.PENDING and run.attempts == attempt
        assert run.lease_until is None and run.worker_id is None

    assert claim_next_run("doomed") == run_id
    _expire(db, run_id)
    assert reap_expired_runs() == (0, 1)
    run = _run(db, run_id)
    assert run.status == VerificationStatus.DEAD and run.attempts == MAX_ATTEMPTS
    assert run.error_reason == "worker_gave_up" and run.finished_at is not None
    assert claim_next_run("w") is None  # a dead run is never claimed again

    events = [e for e in db.scalars(select(AuditEvent)) if e.event_type == "verification.completed"]
    assert events[-1].payload["status"] == "dead"
    # Clients never see `dead`: it is a failed check, and the applicant may re-run it.
    slot = next(
        s
        for s in client.get(f"/api/v1/applications/{app_id}", headers=h).json()["document_slots"]
        if s["type"] == "business_profile"
    )
    assert slot["document"]["verification"]["status"] == "failed"
    assert slot["document"]["verification"]["error_reason"] == "unavailable"
    doc_id = slot["document"]["id"]
    assert (
        client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/verify", headers=h).status_code == 202
    )


def test_reaper_leaves_inline_runs_and_live_leases_alone(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    run_id, _, _ = _queued(client, db)
    doc_id = _run(db, run_id).document_id
    inline = VerificationRun(
        document_id=doc_id, status=VerificationStatus.RUNNING, started_at=datetime.now(UTC)
    )
    db.add(inline)
    db.commit()
    assert claim_next_run("w") == run_id
    assert reap_expired_runs() == (0, 0)
    assert _run(db, inline.id).status == VerificationStatus.RUNNING


def test_stale_result_from_a_taken_over_run_is_dropped(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    """At-least-once: the lease expired under a slow worker and another one took the run. The slow worker's
    late result must not overwrite anything."""
    run_id, _, _ = _queued(client, db)
    assert claim_next_run("slow") == run_id
    _expire(db, run_id)
    reap_expired_runs()
    assert claim_next_run("fast") == run_id
    execute_run(run_id, "slow")  # not the holder: returns at once, writes nothing
    assert _run(db, run_id).status == VerificationStatus.RUNNING
    execute_run(run_id, "fast")
    done = _run(db, run_id)
    assert done.status == VerificationStatus.VERIFIED and done.attempts == 2 and done.lease_until is None


def test_result_is_dropped_when_the_lease_changes_hands_mid_run(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, _, _ = _queued(client, db)
    assert claim_next_run("slow") == run_id
    real = module.extract_text

    def taken_over(content_type: str, data: bytes, *, max_chars: int) -> Extracted:
        db.execute(update(VerificationRun).where(VerificationRun.id == run_id).values(worker_id="fast"))
        db.commit()
        return real(content_type, data, max_chars=max_chars)

    monkeypatch.setattr(module, "extract_text", taken_over)
    execute_run(run_id, "slow")
    run = _run(db, run_id)
    assert run.status == VerificationStatus.RUNNING and run.worker_id == "fast" and run.summary is None


# ---- the lifecycle: nothing of a deleted draft reaches the provider ----


class _CountingProvider(MockProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def verify(self, request: VerificationRequest) -> VerificationResult:
        self.calls += 1
        return super().verify(request)


def _spy(monkeypatch: pytest.MonkeyPatch) -> _CountingProvider:
    provider = _CountingProvider()
    monkeypatch.setattr(module, "get_provider", lambda: provider)
    return provider


def _during_extraction(monkeypatch: pytest.MonkeyPatch, action: Callable[[], None]) -> None:
    real = module.extract_text

    def wrapped(content_type: str, data: bytes, *, max_chars: int) -> Extracted:
        out = real(content_type, data, max_chars=max_chars)
        action()  # the world changes while the file is being read
        return out

    monkeypatch.setattr(module, "extract_text", wrapped)


def test_draft_deleted_during_the_run_never_reaches_the_provider(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, app_id, h = _queued(client, db)
    provider = _spy(monkeypatch)
    assert claim_next_run("w") == run_id
    _during_extraction(monkeypatch, lambda: client.delete(f"/api/v1/applications/{app_id}", headers=h))
    execute_run(run_id, "w")
    assert provider.calls == 0
    assert db.get(VerificationRun, run_id) is None  # the draft took the run with it; nothing was written back
    assert db.scalars(select(AuditEvent).where(AuditEvent.event_type == "verification.completed")).all() == []


def test_draft_deleted_before_the_run_starts_is_skipped(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, app_id, h = _queued(client, db)
    provider = _spy(monkeypatch)
    assert claim_next_run("w") == run_id
    assert client.delete(f"/api/v1/applications/{app_id}", headers=h).status_code == 204
    execute_run(run_id, "w")
    assert provider.calls == 0


def test_document_replaced_during_the_run_is_finished_without_the_provider(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, app_id, h = _queued(client, db)
    provider = _spy(monkeypatch)
    assert claim_next_run("w") == run_id
    newer = PROFILE_TXT + b" Amended."
    _during_extraction(
        monkeypatch, lambda: upload(client, h, app_id, "business_profile", "v2.txt", newer, "text/plain")
    )
    execute_run(run_id, "w")
    assert provider.calls == 0
    run = _run(db, run_id)
    assert run.status == VerificationStatus.UNAVAILABLE and run.error_reason == module.REPLACED_REASON
    replaced = db.get(Document, run.document_id)
    assert replaced is not None and replaced.is_current is False


def test_result_is_not_written_for_a_draft_deleted_after_the_provider(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, app_id, h = _queued(client, db)
    provider = _spy(monkeypatch)
    real = provider.verify

    def verify_then_delete(request: VerificationRequest) -> VerificationResult:
        out = real(request)
        client.delete(f"/api/v1/applications/{app_id}", headers=h)
        return out

    monkeypatch.setattr(provider, "verify", verify_then_delete)
    assert claim_next_run("w") == run_id
    execute_run(run_id, "w")
    assert provider.calls == 1 and db.get(VerificationRun, run_id) is None
    assert db.scalars(select(AuditEvent).where(AuditEvent.event_type == "verification.completed")).all() == []


# ---- the PDF child process ----


def test_a_crafted_slow_pdf_is_killed_at_the_deadline_with_the_normal_reason(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "pdf_extract_timeout_seconds", 1.5)
    run_id, _, _ = _queued(client, db, "plan.pdf", _bomb_pdf(), "application/pdf")
    provider = _spy(monkeypatch)
    assert claim_next_run("w") == run_id
    started = time.monotonic()
    execute_run(run_id, "w")
    assert time.monotonic() - started < 10  # killed at the deadline, not parsed to the end
    run = _run(db, run_id)
    assert run.status == VerificationStatus.UNREADABLE and run.error_reason == "pdf_parse_error"
    assert provider.calls == 0


def test_pdf_over_the_cpu_cap_is_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "pdf_extract_cpu_seconds", 1)
    monkeypatch.setattr(get_settings(), "pdf_extract_timeout_seconds", 20.0)
    out = extract_text("application/pdf", _bomb_pdf(), max_chars=1000)
    assert out.reason == "pdf_parse_error" and out.text == ""


def test_a_normal_pdf_is_read_by_the_child() -> None:
    assert extract_text("application/pdf", _pdf(), max_chars=100) == Extracted("hi", None)


def test_pdf_child_survives_when_the_child_cannot_start(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.infra import extraction

    monkeypatch.setattr(extraction.sys, "executable", "/nonexistent/python")
    assert extraction.extract_text("application/pdf", b"%PDF-1.4", max_chars=10).reason == "pdf_parse_error"


def test_encrypted_pdf_is_reported_by_the_child() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("secret")
    out = BytesIO()
    writer.write(out)
    assert extract_text("application/pdf", out.getvalue(), max_chars=100).reason == "encrypted_pdf"


# ---- pause ----


def _pause(db: Session, paused: bool) -> None:
    admin = make_user(db, f"admin{uuid.uuid4().hex[:6]}@example.sg", Role.ADMIN)
    db.merge(
        PlatformSetting(
            key="ai_paused", value=paused, updated_by=admin.id, updated_at=datetime.now(UTC), reason="t"
        )
    )
    db.commit()
    live().refresh()


def _finish_threads(w: Worker) -> None:
    for t in list(w._active.values()):
        t.join(20)


def test_pause_holds_queued_runs_until_unpaused(client: TestClient, db: Session, worker_mode: None) -> None:
    run_id, _, _ = _queued(client, db)
    w = Worker()
    _pause(db, True)
    assert w.fill_slots() == 0
    assert _run(db, run_id).status == VerificationStatus.PENDING  # held, not failed
    _pause(db, False)
    assert w.fill_slots() == 1
    _finish_threads(w)
    assert _run(db, run_id).status == VerificationStatus.VERIFIED


def test_worker_runs_up_to_its_concurrency_and_no_more(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _, _ = _queued(client, db)
    doc_id = _run(db, first).document_id
    db.add_all(VerificationRun(document_id=doc_id) for _ in range(4))
    db.commit()
    release = threading.Event()
    seen: list[uuid.UUID] = []

    def slow(run_id: uuid.UUID, worker_id: str | None = None) -> None:
        seen.append(run_id)
        release.wait(20)

    monkeypatch.setattr(worker_module, "execute_run", slow)
    monkeypatch.setattr(get_settings(), "worker_concurrency", 2)
    w = Worker()
    assert w.fill_slots() == 2 and w.free_slots() == 0
    assert w.fill_slots() == 0  # both slots busy: the other three stay queued
    release.set()
    _finish_threads(w)
    assert w.fill_slots() == 2
    release.set()
    _finish_threads(w)
    assert len(set(seen)) == len(seen) == 4


def test_shutdown_hands_an_unfinished_run_back(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id, _, _ = _queued(client, db)
    started, release = threading.Event(), threading.Event()

    def stuck(_: uuid.UUID, __: str | None = None) -> None:
        started.set()
        release.wait(20)

    monkeypatch.setattr(worker_module, "execute_run", stuck)
    monkeypatch.setattr(worker_module, "SHUTDOWN_GRACE_SECONDS", 0.3)
    w = Worker()
    assert w.fill_slots() == 1 and started.wait(5)
    w.stop.set()
    w.drain()
    run = _run(db, run_id)
    assert run.status == VerificationStatus.PENDING and run.attempts == 0 and run.worker_id is None
    release.set()


def test_shutdown_lets_a_quick_run_finish(client: TestClient, db: Session, worker_mode: None) -> None:
    run_id, _, _ = _queued(client, db)
    w = Worker()
    assert w.fill_slots() == 1
    w.stop.set()
    w.drain()
    assert _run(db, run_id).status == VerificationStatus.VERIFIED


def test_a_database_error_does_not_stop_the_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_: str) -> uuid.UUID | None:
        raise RuntimeError("database away")

    monkeypatch.setattr(worker_module, "claim_next_run", boom)
    monkeypatch.setattr(
        worker_module, "reap_expired_runs", lambda: (_ for _ in ()).throw(RuntimeError("away"))
    )
    w = Worker()
    assert w.fill_slots() == 0
    w.reap()
    monkeypatch.setattr(worker_module, "session_factory", lambda: (_ for _ in ()).throw(RuntimeError("away")))
    w.publish_gauges()


# ---- metrics and the admin panel ----


def _sample(name: str) -> float:
    value = REGISTRY.get_sample_value(f"permitflow_verification_{name}")
    assert value is not None
    return value


def test_queue_gauges_and_the_admin_count(client: TestClient, db: Session, worker_mode: None) -> None:
    run_id, _, _ = _queued(client, db)
    doc_id = _run(db, run_id).document_id
    db.add_all(
        [
            VerificationRun(document_id=doc_id),
            VerificationRun(
                document_id=doc_id, status=VerificationStatus.DEAD, error_reason="worker_gave_up"
            ),
        ]
    )
    db.commit()
    assert claim_next_run("w") is not None
    refresh_queue_gauges(db)
    assert _sample("queue_depth") == 1 and _sample("active_leases") == 1 and _sample("dead_runs") == 1
    assert _sample("queue_oldest_seconds") >= 0

    make_user(db, "admin@example.sg", Role.ADMIN)
    body = client.get("/api/v1/admin/overview", headers=login(client, "admin@example.sg")).json()
    assert body["checks"]["dead"] == 1 and body["checks"]["still_running"] == 2


def test_empty_queue_gauges_are_zero(db: Session) -> None:
    refresh_queue_gauges(db)
    assert _sample("queue_depth") == 0 and _sample("queue_oldest_seconds") == 0


# ---- inline mode keeps its startup sweep, worker mode does not ----


def test_inline_startup_sweep_runs_only_in_inline_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main as main_module

    calls: list[str] = []
    monkeypatch.setattr(module, "mark_stale_runs_failed", lambda: calls.append("sweep") or 0)
    monkeypatch.setattr(main_module.live(), "refresh", lambda: None)
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "development")  # the lifespan skips the sweep in tests
    for mode, expected in (("inline", ["sweep"]), ("worker", [])):
        calls.clear()
        monkeypatch.setattr(settings, "verification_mode", mode)
        with TestClient(main_module.create_app()):
            pass
        assert calls == expected


# ---- the loop and the real process ----


def test_serve_runs_a_check_reaps_and_stops_on_sigterm(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`serve()` in this process: claim and run, publish the gauges, and shut down on a real SIGTERM."""
    run_id, _, _ = _queued(client, db)
    w = Worker()
    monkeypatch.setattr(worker_module, "start_http_server", lambda port: None)
    old = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}

    def stop_when_done() -> None:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and _run(db, run_id).status != VerificationStatus.VERIFIED:
            time.sleep(0.2)
        os.kill(os.getpid(), signal.SIGTERM)

    stopper = threading.Thread(target=stop_when_done, daemon=True)
    stopper.start()
    try:
        w.serve()
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
        dbmod._connect_args.clear()
        dbmod.reset_engine()
        stopper.join(5)
    assert w.stop.is_set() and _run(db, run_id).status == VerificationStatus.VERIFIED
    assert _sample("queue_depth") == 1  # published at start, when the check was still waiting


def _worker_env() -> dict[str, str]:
    return {**os.environ, "VERIFICATION_MODE": "worker", "WORKER_METRICS_PORT": "0", "PYTHONUNBUFFERED": "1"}


def test_worker_process_runs_a_queued_check_and_stops_on_sigterm(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    run_id, _, _ = _queued(client, db)
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.worker"],
        cwd=BACKEND_DIR,
        env=_worker_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and _run(db, run_id).status != VerificationStatus.VERIFIED:
            time.sleep(0.3)
        assert _run(db, run_id).status == VerificationStatus.VERIFIED, "the worker did not run the check"
    finally:
        proc.send_signal(signal.SIGTERM)
        out, _ = proc.communicate(timeout=30)
    assert proc.returncode == 0, out
    assert "worker_stopped" in out


# ---- the migration ----


def _alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={**os.environ, "APP_ENV": "test"},
        check=True,
        capture_output=True,
    )


def test_migration_0016_downgrades_cleanly_and_upgrades_back(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    run_id, _, _ = _queued(client, db)
    doc_id = _run(db, run_id).document_id
    dead = VerificationRun(document_id=doc_id, status=VerificationStatus.DEAD, error_reason="worker_gave_up")
    db.add(dead)
    db.commit()
    dead_id = dead.id
    db.close()
    dbmod.reset_engine()
    _alembic("downgrade", "0015")
    try:
        with dbmod.get_engine().connect() as conn:
            cols = {
                r[0]
                for r in conn.execute(
                    text(
                        "select column_name from information_schema.columns "
                        "where table_name = 'verification_runs'"
                    )
                )
            }
            assert not {"attempts", "lease_until", "worker_id"} & cols
            row = conn.execute(
                text("select status, error_reason from verification_runs where id = :i"), {"i": dead_id}
            ).one()
            assert tuple(row) == ("failed", "interrupted")  # the older code never meets `dead`
    finally:
        dbmod.reset_engine()
        _alembic("upgrade", "head")
        dbmod.reset_engine()
    with dbmod.get_engine().connect() as conn:
        names = {
            r[0]
            for r in conn.execute(
                text("select indexname from pg_indexes where tablename='verification_runs'")
            )
        }
        assert {"ix_verification_runs_queued", "ix_verification_runs_lease"} <= names
