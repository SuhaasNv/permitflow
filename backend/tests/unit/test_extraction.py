from app.infra.extraction import extract_text


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
