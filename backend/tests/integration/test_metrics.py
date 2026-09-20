"""US-077: the Prometheus endpoint is off without a token, refuses a wrong one, and reports the counters
the dashboards read."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import complete_draft

TOKEN = "metrics-secret-for-tests"


@pytest.fixture
def token(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("METRICS_TOKEN", TOKEN)
    settings_module.get_settings.cache_clear()
    yield TOKEN
    settings_module.get_settings.cache_clear()


def _sample(body: str, name: str, **labels: str) -> float | None:
    """The value of the first sample of `name` whose label set contains `labels`."""
    for line in body.splitlines():
        if not line.startswith(name):
            continue
        head, _, value = line.rpartition(" ")
        if head == name and not labels:
            return float(value)
        if head.startswith(name + "{") and all(f'{k}="{v}"' in head for k, v in labels.items()):
            return float(value)
    return None


def test_metrics_is_off_without_a_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METRICS_TOKEN", "")  # the environment wins over a developer's .env
    settings_module.get_settings.cache_clear()
    r = client.get("/api/v1/metrics", headers={"Authorization": "Bearer anything"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    settings_module.get_settings.cache_clear()


def test_metrics_requires_the_bearer_token(client: TestClient, token: str) -> None:
    assert client.get("/api/v1/metrics").status_code == 401
    assert client.get("/api/v1/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    r = client.get("/api/v1/metrics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert "permitflow_http_requests_total" in r.text


def test_metrics_report_requests_transitions_checks_and_gauges(
    client: TestClient, db: Session, token: str
) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = complete_draft(client, op)  # four uploads, each verified by the mock provider in the background
    client.post("/api/v1/applications", headers=op)  # a second, open draft
    assert client.post(f"/api/v1/applications/{app_id}/submit", headers=op).status_code == 200

    body = client.get("/api/v1/metrics", headers={"Authorization": f"Bearer {token}"}).text
    assert (
        _sample(
            body, "permitflow_http_requests_total", method="POST", route="/api/v1/applications", status="201"
        )
        or 0
    ) >= 2
    assert (
        _sample(body, "permitflow_transitions_total", target="application_received", actor="operator") or 0
    ) >= 1
    assert (
        _sample(body, "permitflow_verification_runs_total", outcome="verified", provider="mock") or 0
    ) >= 1
    assert _sample(body, "permitflow_applications", status="draft") == 1.0
    assert _sample(body, "permitflow_applications", status="application_received") == 1.0
    assert "permitflow_verification_run_seconds_bucket" in body
    # the scrape does not count itself
    assert _sample(body, "permitflow_http_requests_total", route="/api/v1/metrics") is None


def test_layering_metrics_module_is_not_imported_by_domain() -> None:
    from pathlib import Path

    domain = Path(__file__).resolve().parents[2] / "app" / "domain"
    assert not any("metrics" in f.read_text() for f in domain.glob("*.py"))


def test_use_case_3_counters_and_the_storage_gauge(client: TestClient, db: Session, token: str) -> None:
    """US-089: a checklist submit, a released round, an answered round and the evidence bytes each move
    their counter; the storage gauge reports the database sums and the volume."""
    from tests.integration.test_clarification import _attach, _respond, _submitted
    from tests.journeys import PDF

    def scrape() -> str:
        return client.get("/api/v1/metrics", headers={"Authorization": f"Bearer {token}"}).text

    before = scrape()
    submitted_before = _sample(before, "permitflow_checklists_submitted_total") or 0
    released_before = _sample(before, "permitflow_clarification_rounds_total", event="released") or 0
    answered_before = _sample(before, "permitflow_clarification_rounds_total", event="answered") or 0
    bytes_before = _sample(before, "permitflow_attachment_bytes_total") or 0

    app_id, op, off = _submitted(client, db)
    after_submit = scrape()
    assert _sample(after_submit, "permitflow_checklists_submitted_total") == submitted_before + 1
    assert (
        _sample(after_submit, "permitflow_clarification_rounds_total", event="released")
        == released_before + 1
    )

    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    for item in view["items"]:
        rid = _respond(client, op, app_id, item["item_id"], "Done.").json()
        response_id = next(i for i in rid["items"] if i["item_id"] == item["item_id"])["responses"][0]["id"]
        assert _attach(client, op, app_id, response_id, "proof.pdf", PDF).status_code == 201
    assert client.post(f"/api/v1/applications/{app_id}/clarifications/send", headers=op).status_code == 200

    body = scrape()
    assert _sample(body, "permitflow_clarification_rounds_total", event="answered") == answered_before + 1
    assert _sample(body, "permitflow_attachment_bytes_total") == bytes_before + len(PDF) * len(view["items"])
    assert (_sample(body, "permitflow_storage_bytes", kind="attachments") or 0) >= len(PDF) * len(
        view["items"]
    )
    assert (_sample(body, "permitflow_storage_bytes", kind="documents") or 0) > 0
    assert (_sample(body, "permitflow_storage_bytes", kind="volume_total") or 0) > 0
    assert (_sample(body, "permitflow_storage_bytes", kind="volume_used") or 0) > 0
    assert _sample(body, "permitflow_sessions_active") is not None
