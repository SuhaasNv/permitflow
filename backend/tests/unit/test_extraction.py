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
