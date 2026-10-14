import pytest

from app.infra import extraction
from app.infra.extraction import extract_text
from evals.redteam.render import Span, render_pdf


def test_text_and_caps() -> None:
    out = extract_text("text/plain", b"hello world " * 100, max_chars=50)
    assert out.reason is None and len(out.text) == 50
    assert extract_text("text/plain", b"   ", max_chars=100).reason == "no_text"


def test_images_and_broken_pdf() -> None:
    assert extract_text("image/png", b"\x89PNG", max_chars=100).reason == "image_not_supported"
    assert extract_text("application/pdf", b"%PDF-1.4 garbage", max_chars=100).reason in (
        "pdf_parse_error",
        "no_text",
    )


def test_real_pdf_text() -> None:
    from io import BytesIO

    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    buf = BytesIO()
    w.write(buf)
    out = extract_text("application/pdf", buf.getvalue(), max_chars=100)
    assert out.reason == "no_text"


def _hidden(*spans: Span) -> str:
    out = extract_text("application/pdf", render_pdf([Span("Visible line"), *spans]), max_chars=1000)
    assert out.reason is None and "Visible line" in out.text
    return out.hidden


def test_invisible_white_and_tiny_text_is_reported_and_kept() -> None:
    for span in (Span("planted", invisible=True), Span("planted", gray=1.0), Span("planted", size=1.0)):
        assert _hidden(span) == "planted"
    out = extract_text("application/pdf", render_pdf([Span("planted", invisible=True)]), max_chars=1000)
    assert "planted" in out.text


def test_ordinary_text_reports_nothing_hidden() -> None:
    assert _hidden(Span("small but legible", size=8.0), Span("dark grey", gray=0.4)) == ""


def test_pdf_children_are_bounded_by_the_process_wide_semaphore(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess
    import threading
    import time

    monkeypatch.setattr(extraction, "_SLOTS", threading.BoundedSemaphore(1))
    live = peak = 0
    lock = threading.Lock()

    def fake_run(*_a: object, **_k: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
        time.sleep(0.05)
        with lock:
            live -= 1
        return subprocess.CompletedProcess([], 0, b'{"encrypted": false, "text": "x", "hidden": ""}')

    monkeypatch.setattr(extraction.subprocess, "run", fake_run)
    threads = [
        threading.Thread(target=extract_text, args=("application/pdf", b"%PDF"), kwargs={"max_chars": 10})
        for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak == 1


def test_a_pdf_waiting_for_a_slot_gives_up_as_unreadable_instead_of_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security audit run 7: the wait for a slot is bounded by the extraction timeout, so queued checks cannot
    hold a threadpool thread (or a worker lease) for ever."""
    import threading

    slots = threading.BoundedSemaphore(1)
    slots.acquire()  # every slot is taken
    monkeypatch.setattr(extraction, "_SLOTS", slots)
    monkeypatch.setattr(extraction.get_settings(), "pdf_extract_timeout_seconds", 0.2)
    monkeypatch.setattr(extraction.subprocess, "run", lambda *a, **k: pytest.fail("no slot, no child"))
    out: list[extraction.Extracted] = []
    t = threading.Thread(
        target=lambda: out.append(extract_text("application/pdf", b"%PDF", max_chars=10)), daemon=True
    )
    t.start()
    t.join(5)
    assert out and out[0].reason == "pdf_parse_error"
    slots.release()  # the failed waiter must not have released a slot it never held
    with pytest.raises(ValueError):
        slots.release()
