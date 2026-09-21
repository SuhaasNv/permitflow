"""US-085: images stored without metadata, the storage budget per application, the room shown before
an upload. The per-file rules (allowlist, magic bytes, 10 MB) stay the document rules."""

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image, PngImagePlugin
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.models.enums import Role
from tests.factories import login, make_user
from tests.integration.test_clarification import _attach, _respond, _submitted
from tests.journeys import PDF
from tests.journeys import draft as _draft
from tests.journeys import upload as _upload

# A 4-byte sRGB-looking profile is enough to prove the profile survives; Pillow passes it through.
ICC = b"fake-icc-profile-bytes"


def jpeg_with_gps(width: int = 8, height: int = 6) -> bytes:
    """A camera-style JPEG: EXIF with GPS, a comment, and orientation 6 (turn to display)."""
    image = Image.new("RGB", (width, height), (200, 40, 40))
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotate 90 CW to display
    exif[0x010F] = "PermitPhone"  # Make
    exif[0x0132] = "2026:09:21 10:05:00"  # DateTime
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (1.0, 17.0, 0.0)
    gps[3] = "E"
    gps[4] = (103.0, 51.0, 0.0)
    out = BytesIO()
    image.save(out, "JPEG", exif=exif.tobytes(), icc_profile=ICC, comment=b"taken at the kitchen")
    return out.getvalue()


def png_with_text() -> bytes:
    image = Image.new("RGBA", (5, 7), (0, 120, 0, 255))
    info = PngImagePlugin.PngInfo()
    info.add_text("Comment", "kitchen, 10 Jalan Besar")
    info.add_text("Software", "PermitPhone camera")
    out = BytesIO()
    image.save(out, "PNG", pnginfo=info, icc_profile=ICC)
    return out.getvalue()


def _operator(client: TestClient, db: Session) -> tuple[dict[str, str], str]:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    return h, _draft(client, h)


def test_jpeg_document_is_stored_without_exif_and_turned_upright(client: TestClient, db: Session) -> None:
    h, app_id = _operator(client, db)
    original = jpeg_with_gps()
    r = _upload(client, h, app_id, "floor_plan", "kitchen.jpg", original, "image/jpeg")
    assert r.status_code == 201, r.text
    doc = r.json()["document"]
    got = client.get(f"/api/v1/applications/{app_id}/documents/{doc['id']}/download", headers=h)
    assert got.status_code == 200
    stored = Image.open(BytesIO(got.content))
    assert stored.format == "JPEG"
    exif = stored.getexif()
    assert 0x8825 not in exif and 0x010F not in exif and 0x0132 not in exif, dict(exif)
    assert not stored.info.get("comment")
    # orientation 6 applied: the 8 x 6 photo is stored 6 x 8, no orientation tag left
    assert stored.size == (6, 8)
    assert 0x0112 not in exif
    assert stored.info.get("icc_profile") == ICC
    # the record describes the stored bytes, not the phone's original
    assert doc["size_bytes"] == len(got.content) and doc["size_bytes"] != len(original)
    from hashlib import sha256

    from sqlalchemy import select

    from app.models import Document

    row = db.scalar(select(Document))
    assert row is not None and row.sha256 == sha256(got.content).hexdigest()


def test_png_evidence_is_stored_without_text_chunks(client: TestClient, db: Session) -> None:
    app_id, op, _ = _submitted(client, db)
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    item = view["items"][0]
    rid = _respond(client, op, app_id, item["item_id"], "Photo attached.").json()["items"][0]["responses"][0][
        "id"
    ]
    r = _attach(client, op, app_id, rid, "coving.png", png_with_text(), "image/png")
    assert r.status_code == 201, r.text
    att = r.json()["view"]["items"][0]["responses"][0]["attachments"][0]
    got = client.get(
        f"/api/v1/applications/{app_id}/clarifications/attachments/{att['id']}/download", headers=op
    )
    assert got.status_code == 200
    stored = Image.open(BytesIO(got.content))
    assert stored.format == "PNG" and stored.size == (5, 7)
    assert "Comment" not in stored.info and "Software" not in stored.info
    assert stored.info.get("icc_profile") == ICC
    # the same photo again is the same stored bytes: no change
    again = _attach(client, op, app_id, rid, "coving-again.png", png_with_text(), "image/png")
    assert again.status_code == 201 and again.json()["unchanged"] is True


def test_an_unreadable_image_is_refused_and_nothing_is_kept(client: TestClient, db: Session) -> None:
    h, app_id = _operator(client, db)
    r = _upload(
        client, h, app_id, "floor_plan", "broken.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, "image/png"
    )
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "unreadable_image"
    view = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    assert view["storage"]["used_bytes"] == 0


def test_a_decompression_bomb_is_refused_before_it_is_decoded(client: TestClient, db: Session) -> None:
    """A 45-megapixel PNG of a few kilobytes: refused as unreadable from its header, never decoded
    (Pillow's own ceiling only warned below 80 megapixels; review finding, 21 Sep)."""
    import tracemalloc

    from app.infra.images import MAX_PIXELS, ImageUnreadableError, strip_metadata

    out = BytesIO()
    Image.new("1", (6800, 6700)).save(out, "PNG", optimize=True)  # 45.6 MP, one bit per pixel on the wire
    bomb = out.getvalue()
    assert 6800 * 6700 > MAX_PIXELS and len(bomb) < 50_000
    tracemalloc.start()
    try:
        strip_metadata(bomb, ".png")
    except ImageUnreadableError:
        pass
    else:
        raise AssertionError("the bomb was decoded")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 5_000_000  # the pixels were never allocated
    h, app_id = _operator(client, db)
    r = _upload(client, h, app_id, "floor_plan", "bomb.png", bomb, "image/png")
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "unreadable_image"


def test_budget_refuses_the_file_that_would_pass_it_and_names_the_room(
    client: TestClient,
    db: Session,
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    h, app_id = _operator(client, db)
    monkeypatch.setattr(settings_module.get_settings(), "storage_budget_bytes", len(PDF) * 2 + 10)
    first = _upload(client, h, app_id, "business_profile", "one.pdf", PDF)
    assert first.status_code == 201
    view = first.json()["application"]
    assert view["storage"] == {
        "used_bytes": len(PDF),
        "budget_bytes": len(PDF) * 2 + 10,
        "remaining_bytes": len(PDF) + 10,
    }
    # a second file of the same size fits; a third does not, and the answer names what is left
    assert _upload(client, h, app_id, "floor_plan", "two.pdf", PDF + b"2").status_code == 201
    r = _upload(client, h, app_id, "tenancy_agreement", "three.pdf", PDF + b"3")
    assert r.status_code == 422, r.text
    err = r.json()["error"]
    assert err["code"] == "validation_failed" and err["details"]["reason"] == "storage_budget"
    assert err["details"]["remaining_bytes"] == 9 and "storage room left" in err["message"]
    # nothing was kept for the refused file, and a replaced version still counts (it stays on disk)
    view = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    assert view["storage"]["used_bytes"] == len(PDF) * 2 + 1
    assert len([s for s in view["document_slots"] if s["present"]]) == 2


def test_budget_counts_every_version_and_the_evidence(client: TestClient, db: Session) -> None:
    app_id, op, _ = _submitted(client, db)
    before = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()["storage"]
    assert before["used_bytes"] > 0 and before["budget_bytes"] == 150 * 1024 * 1024
    item = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()["items"][0]
    rid = _respond(client, op, app_id, item["item_id"], "See file.").json()["items"][0]["responses"][0]["id"]
    r = _attach(client, op, app_id, rid, "evidence.pdf", PDF + b"evidence")
    assert r.status_code == 201
    after = r.json()["view"]["storage"]
    assert after["used_bytes"] == before["used_bytes"] + len(PDF + b"evidence")
    assert after["remaining_bytes"] == after["budget_bytes"] - after["used_bytes"]
