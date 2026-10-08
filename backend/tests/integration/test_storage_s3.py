"""US-097: with STORAGE_BACKEND=s3 the upload, the authorised download and the draft purge work end to end
through the API, the file lives in the bucket and not on the disk, and the stored key stays server-made."""

from collections.abc import Iterator
from pathlib import Path

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from mypy_boto3_s3.client import S3Client
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.infra import s3_storage
from app.models import Document
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import PDF
from tests.journeys import draft as _draft
from tests.journeys import upload as _upload

BUCKET = "permitflow-api-test"


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> Iterator[S3Client]:
    settings = settings_module.get_settings()
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", BUCKET)
    monkeypatch.setattr(settings, "s3_access_key_id", "test-key-id")
    monkeypatch.setattr(settings, "s3_secret_access_key", "test-secret")
    s3_storage._build.cache_clear()
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield client
    s3_storage._build.cache_clear()


def _keys(client: S3Client) -> list[str]:
    return [o["Key"] for o in client.list_objects_v2(Bucket=BUCKET).get("Contents", [])]


def test_upload_download_and_draft_deletion_use_the_bucket(
    client: TestClient, db: Session, bucket: S3Client
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = _draft(client, h)
    r = _upload(client, h, app_id, "floor_plan", "plan.pdf", PDF)
    assert r.status_code == 201, r.text
    doc_id = r.json()["document"]["id"]

    doc = db.scalar(select(Document))
    assert doc is not None
    assert _keys(bucket) == [doc.stored_key]  # server-made key, same shape as on disk
    assert doc.stored_key.startswith(f"{app_id}/") and "plan" not in doc.stored_key
    assert not Path(settings_module.get_settings().upload_dir, doc.stored_key).exists()

    url = f"/api/v1/applications/{app_id}/documents/{doc_id}/download"
    got = client.get(url, headers=h)
    assert got.status_code == 200 and got.content == PDF and "location" not in got.headers
    make_user(db, "other@example.sg", Role.OPERATOR)
    assert client.get(url, headers=login(client, "other@example.sg")).status_code == 404

    # Deleting the whole draft purges its files from the bucket.
    assert client.delete(f"/api/v1/applications/{app_id}", headers=h).status_code == 204
    assert _keys(bucket) == []
