"""US-058: the four "how I would ruin your life" scenarios, each answered by a limit with a test.

1. Hammer the sign-in endpoint: every attempt counts, not only failures, and the answer is 429.
2. Fill the database with drafts: an operator holds at most MAX_DRAFTS_PER_USER open drafts.
3. Hit the expensive endpoint: verification runs are counted per applicant and per platform per day; over
   the quota the run is stored `unavailable` and nothing reaches the model.
4. Scrape: every request per client is counted; the general bucket answers 429 with Retry-After.
Plus the response headers every API answer now carries.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.core.rate_limit import RequestLimiter
from app.models.enums import Role
from tests.factories import DEFAULT_PASSWORD, login, make_user
from tests.journeys import PDF, draft, upload


@pytest.fixture
def limited(client: TestClient) -> Iterator[TestClient]:
    """The test app runs without request limits; install small ones for these tests only."""
    previous = client.app.state.limiter  # type: ignore[attr-defined]
    client.app.state.limiter = RequestLimiter(per_minute=6, login_per_minute=3, trusted_proxies="")  # type: ignore[attr-defined]
    try:
        yield client
    finally:
        client.app.state.limiter = previous  # type: ignore[attr-defined]


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Iterator[None]:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    settings_module.get_settings.cache_clear()
    yield
    settings_module.get_settings.cache_clear()


def test_sign_in_attempts_of_any_outcome_are_limited_per_client(limited: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    db.commit()
    good = {"email": "op@example.sg", "password": DEFAULT_PASSWORD}
    assert limited.post("/api/v1/auth/login", json=good).status_code == 200
    assert limited.post("/api/v1/auth/login", json=good).status_code == 200
    assert limited.post("/api/v1/auth/login", json=good).status_code == 200
    r = limited.post("/api/v1/auth/login", json=good)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert r.headers["Retry-After"].isdigit()
    assert "request_id" in r.json()["error"]["details"]


def test_every_request_counts_against_the_general_bucket_but_health_does_not(limited: TestClient) -> None:
    for _ in range(6):
        assert limited.get("/api/v1/form-schema").status_code in (200, 401)
    r = limited.get("/api/v1/form-schema")
    assert r.status_code == 429 and r.headers["Retry-After"]
    for _ in range(20):
        assert limited.get("/api/v1/health").status_code == 200


def test_an_operator_may_hold_a_bounded_number_of_drafts(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    gen = _settings(monkeypatch, MAX_DRAFTS_PER_USER="2")
    next(gen)
    make_user(db, "op@example.sg", Role.OPERATOR)
    db.commit()
    h = login(client, "op@example.sg")
    draft(client, h)
    draft(client, h)
    r = client.post("/api/v1/applications", headers=h)
    assert r.status_code == 409
    assert r.json()["error"]["details"]["code"] == "draft_limit"
    assert "2 draft applications" in r.json()["error"]["message"]
    # Deleting one frees a slot.
    first = client.get("/api/v1/applications", headers=h).json()[0]["id"]
    assert client.delete(f"/api/v1/applications/{first}", headers=h).status_code == 204
    assert client.post("/api/v1/applications", headers=h).status_code == 201
    next(gen, None)


def test_verification_runs_over_the_daily_quota_are_stored_unavailable(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    gen = _settings(monkeypatch, AI_RUNS_PER_USER_PER_DAY="1")
    next(gen)
    make_user(db, "op@example.sg", Role.OPERATOR)
    db.commit()
    h = login(client, "op@example.sg")
    app_id = draft(client, h)
    first = upload(client, h, app_id, "business_profile", "a.pdf", PDF).json()
    assert first["document"]["verification"]["status"] in (
        "pending",
        "running",
        "verified",
        "issues_found",
        "unreadable",
    )
    second = upload(client, h, app_id, "floor_plan", "b.pdf", PDF).json()
    assert second["document"]["verification"]["status"] == "unavailable"
    assert second["document"]["verification"]["error_reason"] == "daily_limit_reached"
    # The operator is not blocked from proceeding: the slot is filled and the application can go on.
    view = client.get(f"/api/v1/applications/{app_id}", headers=h).json()
    assert view["completeness"]["documents_present"] == 2
    next(gen, None)


def test_api_answers_carry_the_hardening_headers(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert r.headers["Strict-Transport-Security"].startswith("max-age=31536000")
    assert "camera=()" in r.headers["Permissions-Policy"]
    assert r.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert r.headers["X-Frame-Options"] == "DENY"
    # The interactive docs (non-production only) load Swagger from a CDN and are exempt from the CSP.
    docs = client.get("/api/docs")
    assert docs.status_code == 200 and "Content-Security-Policy" not in docs.headers


def test_quota_refusals_do_not_count_toward_the_quota(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refused attempt is stored `unavailable` but must not extend the applicant's lock-out: only runs
    that could have reached the model are counted, so capacity returns a day after the last real run."""
    from datetime import UTC, datetime, timedelta

    from app.repositories.documents import DocumentRepository
    from app.services.quotas import DAILY_LIMIT_REASON

    gen = _settings(monkeypatch, AI_RUNS_PER_USER_PER_DAY="1")
    next(gen)
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    db.commit()
    h = login(client, "op@example.sg")
    app_id = draft(client, h)
    upload(client, h, app_id, "business_profile", "a.pdf", PDF)
    for dtype in ("floor_plan", "tenancy_agreement"):
        refused = upload(client, h, app_id, dtype, f"{dtype}.pdf", PDF).json()
        assert refused["document"]["verification"]["error_reason"] == "daily_limit_reached"
    since = datetime.now(UTC) - timedelta(days=1)
    repo = DocumentRepository(db)
    assert repo.count_runs_since(since, operator_id=user.id) == 3
    assert repo.count_runs_since(since, operator_id=user.id, exclude_reason=DAILY_LIMIT_REASON) == 1
    next(gen, None)


def test_oversized_upload_is_refused_by_the_middleware_with_cors_headers(
    client: TestClient, db: Session
) -> None:
    """The Content-Length gate answers inside CORS, so a browser can read the refusal (T7)."""
    make_user(db, "op@example.sg", Role.OPERATOR)
    db.commit()
    h = login(client, "op@example.sg")
    app_id = draft(client, h)
    r = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers={
            **h,
            "Origin": "http://localhost:3000",
            "Content-Length": str(50 * 1024 * 1024),
            "Content-Type": "multipart/form-data; boundary=x",
        },
        content=b"",
    )
    assert r.status_code == 400
    assert r.json()["error"]["details"]["reason"] == "too_large"
    assert r.json()["error"]["details"]["request_id"]
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
