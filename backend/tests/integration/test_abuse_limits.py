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
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core import settings as settings_module
from app.core.rate_limit import RequestLimiter
from app.infra import db as dbmod
from app.main import create_app
from app.models import User
from app.models.enums import Role
from app.services.quotas import ensure_draft_capacity
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
    good = {"email": "op@example.sg", "password": DEFAULT_PASSWORD, "take_over": True}
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


def test_draft_quota_holds_the_operator_row_lock_until_the_transaction_ends(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The count and the insert that follows it are serialised per operator: while one transaction is
    inside the quota check, a second one cannot take the same user row (readiness row 23, fixed US-076)."""
    gen = _settings(monkeypatch, MAX_DRAFTS_PER_USER="2")
    next(gen)
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    ensure_draft_capacity(db, user.id)  # takes SELECT ... FOR UPDATE on the user row, no commit yet
    other = dbmod.session_factory()()
    try:
        with pytest.raises(OperationalError):  # lock_not_available: the row is held by the first session
            other.execute(select(User).where(User.id == user.id).with_for_update(nowait=True))
        other.rollback()
        db.rollback()
        other.execute(select(User).where(User.id == user.id).with_for_update(nowait=True))  # free again
        other.rollback()
    finally:
        other.close()


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


def test_api_answers_carry_the_hardening_headers(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    r = client.get("/api/v1/health")
    assert r.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert r.headers["Strict-Transport-Security"].startswith("max-age=31536000")
    assert "camera=()" in r.headers["Permissions-Policy"]
    assert r.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert r.headers["X-Frame-Options"] == "DENY"
    # The interactive docs (EXPOSE_API_DOCS only) load Swagger from a CDN and are exempt from the CSP.
    gen = _settings(monkeypatch, EXPOSE_API_DOCS="true")
    next(gen)
    with TestClient(create_app()) as docs_client:
        docs = docs_client.get("/api/docs")
    assert docs.status_code == 200 and "Content-Security-Policy" not in docs.headers
    next(gen, None)


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
    assert repo.count_runs_since(since, operator_id=user.id, exclude_reasons=(DAILY_LIMIT_REASON,)) == 1
    next(gen, None)


def test_a_rerun_over_the_quota_is_refused_without_writing_a_run_or_an_audit_row(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Red-team R-4: a 429 before anything is inserted, so repeating it cannot grow the tables."""
    from sqlalchemy import func

    from app.models import AuditEvent, VerificationRun

    gen = _settings(monkeypatch, AI_RUNS_PER_USER_PER_DAY="1")
    next(gen)
    make_user(db, "op@example.sg", Role.OPERATOR)
    db.commit()
    h = login(client, "op@example.sg")
    app_id = draft(client, h)
    doc_id = upload(client, h, app_id, "business_profile", "a.pdf", PDF).json()["document"]["id"]
    db.expire_all()
    runs = db.scalar(select(func.count()).select_from(VerificationRun))
    audits = db.scalar(select(func.count()).select_from(AuditEvent))
    for _ in range(3):
        r = client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/verify", headers=h)
        assert r.status_code == 429 and r.json()["error"]["details"] == {"code": "daily_limit_reached"}
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(VerificationRun)) == runs
    assert db.scalar(select(func.count()).select_from(AuditEvent)) == audits
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


def test_deleting_a_draft_does_not_reset_the_daily_quota(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Security audit run 5: the quota counts the ai_usage ledger, which outlives the draft's runs. Both the
    per-user and the platform ceiling hold after the draft is deleted."""
    gen = _settings(monkeypatch, AI_RUNS_PER_USER_PER_DAY="1", AI_RUNS_PER_DAY="2")
    next(gen)
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "other@example.sg", Role.OPERATOR)
    db.commit()
    h = login(client, "op@example.sg")
    first = draft(client, h)
    assert (
        upload(client, h, first, "business_profile", "a.pdf", PDF).json()["document"]["verification"][
            "error_reason"
        ]
        is None
    )
    assert client.delete(f"/api/v1/applications/{first}", headers=h).status_code == 204
    second = draft(client, h)
    refused = upload(client, h, second, "business_profile", "b.pdf", PDF).json()
    assert refused["document"]["verification"]["error_reason"] == "daily_limit_reached"
    # The refusal is not counted: the platform has seen one real run, so another operator may still run.
    h2 = login(client, "other@example.sg")
    third = draft(client, h2)
    ok = upload(client, h2, third, "business_profile", "c.pdf", PDF).json()
    assert ok["document"]["verification"]["error_reason"] is None
    assert client.delete(f"/api/v1/applications/{third}", headers=h2).status_code == 204
    # Two real runs now: the platform ceiling (2) holds although both drafts are gone.
    make_user(db, "third@example.sg", Role.OPERATOR)
    db.commit()
    h3 = login(client, "third@example.sg")
    last = upload(client, h3, draft(client, h3), "business_profile", "d.pdf", PDF).json()
    assert last["document"]["verification"]["error_reason"] == "daily_limit_reached"
    next(gen, None)
