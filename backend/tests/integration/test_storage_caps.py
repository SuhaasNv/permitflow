"""US-098: the platform-wide stored-bytes ceiling (507, nothing stored), the busy answer when no image slot
frees up (503), and the stored-bytes gauge the 80 % alert reads."""

import threading
from collections.abc import Iterator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.infra import images
from app.infra.storage import LocalDiskStorage
from app.models.enums import Role
from tests.factories import login, make_user
from tests.integration.test_metrics import TOKEN, _sample
from tests.journeys import PDF
from tests.journeys import draft as _draft
from tests.journeys import upload as _upload


def _operator(client: TestClient, db: Session) -> tuple[dict[str, str], str]:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    return h, _draft(client, h)


def _stored_files() -> list[str]:
    root = LocalDiskStorage().root
    return sorted(str(p) for p in root.rglob("*") if p.is_file()) if root.exists() else []


def _png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (8, 6), (10, 20, 30)).save(out, "PNG")
    return out.getvalue()


def test_a_file_over_the_platform_ceiling_is_refused_and_nothing_is_stored(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h, app_id = _operator(client, db)
    monkeypatch.setattr(settings_module.get_settings(), "storage_total_max_bytes", len(PDF) * 2 + 10)
    assert _upload(client, h, app_id, "business_profile", "one.pdf", PDF).status_code == 201
    assert _upload(client, h, app_id, "floor_plan", "two.pdf", PDF + b"2").status_code == 201
    before = _stored_files()
    r = _upload(client, h, app_id, "tenancy_agreement", "three.pdf", PDF + b"3")
    assert r.status_code == 507, r.text
    err = r.json()["error"]
    assert err["code"] == "storage_full" and err["details"]["reason"] == "platform_storage_full"
    assert _stored_files() == before  # no file, no partial file
    view = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    assert view["storage"]["used_bytes"] == len(PDF) * 2 + 1
    assert len([s for s in view["document_slots"] if s["present"]]) == 2


def test_an_image_over_the_platform_ceiling_is_refused_and_nothing_is_stored(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h, app_id = _operator(client, db)
    monkeypatch.setattr(settings_module.get_settings(), "storage_total_max_bytes", 20)
    before = _stored_files()
    r = _upload(client, h, app_id, "floor_plan", "kitchen.png", _png(), "image/png")
    assert r.status_code == 507 and r.json()["error"]["code"] == "storage_full"
    assert _stored_files() == before


def test_no_ceiling_outside_production_lets_uploads_through(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h, app_id = _operator(client, db)
    monkeypatch.setattr(settings_module.get_settings(), "storage_total_max_bytes", 0)
    assert _upload(client, h, app_id, "business_profile", "one.pdf", PDF).status_code == 201


def test_an_image_upload_is_answered_busy_when_no_decode_slot_frees_up(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h, app_id = _operator(client, db)
    slots = threading.BoundedSemaphore(1)
    slots.acquire()
    monkeypatch.setattr(images, "_SLOTS", slots)
    monkeypatch.setattr(images, "WAIT_SECONDS", 0.05)
    before = _stored_files()
    r = _upload(client, h, app_id, "floor_plan", "kitchen.png", _png(), "image/png")
    assert r.status_code == 503, r.text
    assert r.json()["error"]["code"] == "unavailable"
    assert _stored_files() == before
    slots.release()
    assert _upload(client, h, app_id, "floor_plan", "kitchen.png", _png(), "image/png").status_code == 201


@pytest.fixture
def token(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("METRICS_TOKEN", TOKEN)
    settings_module.get_settings.cache_clear()
    yield TOKEN
    settings_module.get_settings.cache_clear()


def test_the_gauge_reports_stored_bytes_and_the_ceiling(
    client: TestClient, db: Session, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    h, app_id = _operator(client, db)
    monkeypatch.setattr(settings_module.get_settings(), "storage_total_max_bytes", 1_000_000)
    assert _upload(client, h, app_id, "business_profile", "one.pdf", PDF).status_code == 201
    body = client.get("/api/v1/metrics", headers={"Authorization": f"Bearer {token}"}).text
    assert _sample(body, "permitflow_storage_bytes", kind="stored") == len(PDF)
    assert _sample(body, "permitflow_storage_bytes", kind="limit") == 1_000_000
