"""US-099: the scan states, the quarantine keys and the PDF active-content rule (pure rules)."""

import pytest

from app.core.settings import Settings
from app.domain.scan import (
    CLEAN,
    INFECTED,
    SCANNING,
    pdf_active_content,
    quarantine_key,
    released_key,
    servable,
)


def test_only_unscanned_legacy_and_clean_files_are_served() -> None:
    assert servable(None) and servable(CLEAN)
    assert not servable(SCANNING) and not servable(INFECTED)


def test_quarantine_key_round_trip() -> None:
    assert quarantine_key("abc/d.pdf") == "quarantine/abc/d.pdf"
    first, second = released_key("quarantine/abc/d.pdf"), released_key("quarantine/abc/d.pdf")
    assert first != second and first.startswith("abc/") and first.endswith(".pdf")  # unique on every call
    assert not first.startswith("quarantine/")
    assert released_key("abc/d.pdf") == "abc/d.pdf"  # never quarantined: unchanged


@pytest.mark.parametrize(
    "body",
    [
        b"<< /OpenAction << /S /JavaScript /JS (app.alert(1)) >> >>",
        b"<< /AA << /O << /S /JavaScript >> >> >>",
        b"<< /OpenAction 5 0 R >> << /S /JS >>",
        b"<< /S /Launch /F (cmd.exe) >>",
        b"<< /Type /EmbeddedFile /Length 3 >>",
        b"<< /Names << /EmbeddedFiles 7 0 R >> >>",
        b"<< /OpenAction 5 0 R >> << /S /Java#53cript >>",  # a name written with a hex escape
    ],
)
def test_pdf_active_content_is_flagged(body: bytes) -> None:
    assert pdf_active_content(b"%PDF-1.4\n" + body + b"\n%%EOF")


@pytest.mark.parametrize(
    "body",
    [
        b"<< /Type /Catalog >>",
        b"<< /OpenAction [3 0 R /Fit] >>",  # an automatic action alone is not active content
        b"<< /S /JavaScript >>",  # a script nobody runs automatically
        b"<< /AAPL 1 >> << /JSON 2 >>",  # names that only start like /AA and /JS
        b"<< /Launcher 1 >>",
    ],
)
def test_ordinary_pdfs_are_not_flagged(body: bytes) -> None:
    assert not pdf_active_content(b"%PDF-1.4\n" + body + b"\n%%EOF")


def test_enforce_without_a_scanner_host_refuses_to_start() -> None:
    ok = Settings(jwt_secret="x" * 32, scan_mode="enforce", clamd_host="clamav")
    ok.validate_for_startup()
    with pytest.raises(RuntimeError, match="CLAMD_HOST"):
        Settings(jwt_secret="x" * 32, scan_mode="enforce", clamd_host=" ").validate_for_startup()
    Settings(jwt_secret="x" * 32, scan_mode="off", clamd_host="").validate_for_startup()
