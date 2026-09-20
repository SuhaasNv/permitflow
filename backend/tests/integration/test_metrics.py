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
