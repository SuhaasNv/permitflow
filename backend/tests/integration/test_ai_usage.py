"""US-100: what each automatic check cost and who ran it. The row is written with the run's result in both
modes, the price is the one in force at run time, the administrator reads and exports it, and the counters,
the Telegram line and the LangSmith metadata carry no personal data."""

import os
import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.domain.ai_usage import DOCUMENT_TYPE_LABELS, OUTCOME_LABELS, pseudonym
from app.domain.enums import DocumentType
from app.domain.verification_rules import VerificationRequest, VerificationResult
from app.infra import db as dbmod
from app.infra import notifier
from app.infra.ai import ProviderError
from app.infra.ai.mock import MockProvider
from app.models import AiPrice, AiUsage, Application, AuditEvent, Document, User, VerificationRun
from app.models.enums import Role, VerificationStatus
from app.repositories.ai_usage import AiUsageRepository
from app.repositories.audit import AuditRepository
from app.services import ai_usage as ai_usage_module
from app.services import verification as module
from app.services.ai_usage import publish, record_usage
from app.services.verification import (
    MAX_ATTEMPTS,
    claim_next_run,
    execute_run,
    mark_stale_runs_failed,
    reap_expired_runs,
)
from tests.conftest import BACKEND_DIR
from tests.factories import DEFAULT_PASSWORD, login, make_user
from tests.journeys import TXT, VALID_BUSINESS, submitted, upload

API = "/api/v1"
PROFILE_TXT = (
    "ACRA Business Profile. Entity name: Kopi & Kaya Toast House Pte. Ltd. UEN: 202312345K. Registered 2023. "
    * 4
).encode()
MODEL = "gpt-4.1-mini"
OLD = datetime(2025, 1, 1, tzinfo=UTC)


class Billing(MockProvider):
    """The mock's answers, billed like the live model: 1200 tokens in, 80 out."""

    name = "openai"
    model = MODEL

    def verify(self, request: VerificationRequest) -> VerificationResult:
        self.input_tokens, self.output_tokens = 1200, 80
        return super().verify(request)


@pytest.fixture(autouse=True)
def no_seeded_price() -> None:
    """The migration seeds the current model's price, and the suite truncates tables only after a test: the
    first test of a session would otherwise see it. Each test here sets the prices it needs."""
    with dbmod.session_factory()() as session:
        session.execute(delete(AiPrice))
        session.commit()


@pytest.fixture
def billing(monkeypatch: pytest.MonkeyPatch) -> Billing:
    provider = Billing()
    monkeypatch.setattr(module, "get_provider", lambda: provider)
    return provider


@pytest.fixture
def worker_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(get_settings(), "verification_mode", "worker")
    yield


def _price(
    db: Session, frm: datetime = OLD, inp: str = "0.40", out: str = "1.60", model: str = MODEL
) -> AiPrice:
    row = AiPrice(
        model=model, input_per_million=Decimal(inp), output_per_million=Decimal(out), effective_from=frm
    )
    db.add(row)
    db.commit()
    return row


def _operator_upload(
    client: TestClient, db: Session, email: str = "op@example.sg", name: str = "profile.txt"
) -> tuple[User, str, dict[str, str]]:
    user = db.scalar(select(User).where(User.email == email)) or make_user(db, email, Role.OPERATOR)
    h = login(client, email)
    app_id = str(client.post(f"{API}/applications", headers=h).json()["id"])
    client.patch(f"{API}/applications/{app_id}/sections/business", headers=h, json=VALID_BUSINESS)
    r = upload(client, h, app_id, "business_profile", name, PROFILE_TXT, "text/plain")
    assert r.status_code == 201, r.text
    return user, app_id, h


def _usage(db: Session) -> list[AiUsage]:
    db.expire_all()
    return list(db.scalars(select(AiUsage).order_by(AiUsage.created_at)))


def _admin(client: TestClient, db: Session) -> dict[str, str]:
    make_user(db, "adm@example.sg", Role.ADMIN)
    return login(client, "adm@example.sg")


# ---- the row, inline ----


def test_inline_check_records_who_what_tokens_and_cost(
    client: TestClient, db: Session, billing: Billing
) -> None:
    price = _price(db)
    user, app_id, _ = _operator_upload(client, db)
    run = db.scalar(select(VerificationRun))
    assert run is not None
    (row,) = _usage(db)
    assert row.run_id == run.id and row.document_id == run.document_id
    assert row.application_id == uuid.UUID(app_id) and row.user_id == user.id
    assert row.document_type == "business_profile" and row.provider == "openai" and row.model == MODEL
    assert (row.input_tokens, row.output_tokens) == (1200, 80)
    assert row.cost_usd == Decimal("0.00060800") and row.price_id == price.id
    assert row.outcome == run.status.value and row.latency_ms == run.latency_ms


def test_mock_provider_still_leaves_a_row_with_zero_tokens(client: TestClient, db: Session) -> None:
    _price(db)
    user, _, _ = _operator_upload(client, db)
    (row,) = _usage(db)
    assert row.provider == "mock" and row.model is None and row.user_id == user.id
    assert (row.input_tokens, row.output_tokens, row.cost_usd, row.price_id) == (0, 0, Decimal(0), None)
    assert row.outcome in {"verified", "issues_found", "needs_review"}


def test_the_price_used_is_the_one_in_force_when_the_check_ran(
    client: TestClient, db: Session, billing: Billing
) -> None:
    _price(db, OLD, "0.40", "1.60")
    _price(db, datetime(2026, 1, 1, tzinfo=UTC), "1.00", "2.00")
    future = _price(db, datetime.now(UTC) + timedelta(days=30), "9.00", "9.00")
    _operator_upload(client, db)
    (row,) = _usage(db)
    assert row.cost_usd == Decimal("0.00136000")  # (1200 x 1.00 + 80 x 2.00) / 1e6
    assert row.price_id != future.id


def test_price_lookup_by_model_and_date(db: Session) -> None:
    first = _price(db, datetime(2025, 1, 1, tzinfo=UTC), "0.40", "1.60")
    second = _price(db, datetime(2026, 1, 1, tzinfo=UTC), "1.00", "2.00")
    other = _price(db, datetime(2025, 6, 1, tzinfo=UTC), "5.00", "5.00", model="other-model")
    repo = AiUsageRepository(db)
    assert repo.price_at(MODEL, datetime(2024, 12, 31, tzinfo=UTC)) is None  # before any price
    assert repo.price_at(MODEL, datetime(2025, 1, 1, tzinfo=UTC)) == first  # the day it takes effect
    assert repo.price_at(MODEL, datetime(2025, 12, 31, 23, 59, tzinfo=UTC)) == first
    assert repo.price_at(MODEL, datetime(2026, 1, 1, tzinfo=UTC)) == second
    assert repo.price_at("other-model", datetime(2026, 1, 1, tzinfo=UTC)) == other
    assert repo.price_at("unpriced", datetime(2026, 1, 1, tzinfo=UTC)) is None


def test_a_model_with_no_price_costs_nothing_and_is_logged(
    client: TestClient, db: Session, billing: Billing, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("WARNING", logger="permitflow.ai_usage"):
        _operator_upload(client, db)
    (row,) = _usage(db)
    assert (row.input_tokens, row.output_tokens, row.cost_usd, row.price_id) == (1200, 80, Decimal(0), None)
    assert any(r.message == "ai_price_missing" for r in caplog.records)


def test_an_officer_rerun_is_charged_to_the_officer(
    client: TestClient, db: Session, billing: Billing
) -> None:
    app_id, op, off = submitted(client, db)
    officer = db.scalar(select(User).where(User.email == "off@example.sg"))
    operator = db.scalar(select(User).where(User.email == "op@example.sg"))
    assert officer is not None and operator is not None
    before = len(_usage(db))
    doc_id = db.scalars(select(VerificationRun.document_id)).first()
    r = client.post(f"{API}/officer/applications/{app_id}/documents/{doc_id}/verify", headers=off)
    assert r.status_code == 202, r.text
    rows = _usage(db)
    assert len(rows) == before + 1
    assert rows[-1].user_id == officer.id
    assert {u.user_id for u in rows[:before]} == {operator.id}  # the four uploads were the operator's
    assert len(rows) == db.scalar(select(func.count()).select_from(VerificationRun))  # one row per run


# ---- runs that never reached the provider ----


def test_a_check_stopped_by_the_pause_switch_is_recorded_with_zeros(client: TestClient, db: Session) -> None:
    adm = _admin(client, db)
    r = client.put(
        f"{API}/admin/settings/ai_paused",
        headers=adm,
        json={"value": True, "reason": "Spend review", "password": DEFAULT_PASSWORD},
    )
    assert r.status_code == 200, r.text
    user, _, _ = _operator_upload(client, db)
    (row,) = _usage(db)
    assert (row.outcome, row.provider, row.model) == ("unavailable", "none", None)
    assert (row.input_tokens, row.output_tokens, row.cost_usd, row.user_id) == (0, 0, Decimal(0), user.id)


def test_a_check_over_the_daily_quota_is_recorded_with_zeros(client: TestClient, db: Session) -> None:
    adm = _admin(client, db)
    client.put(
        f"{API}/admin/settings/ai_runs_per_user_per_day",
        headers=adm,
        json={"value": 1, "reason": "Quota test", "password": DEFAULT_PASSWORD},
    )
    user, app_id, h = _operator_upload(client, db)
    assert upload(client, h, app_id, "floor_plan", "plan.txt", TXT, "text/plain").status_code == 201
    first, second = _usage(db)
    assert first.outcome != "unavailable" and (second.outcome, second.cost_usd) == ("unavailable", Decimal(0))
    assert second.user_id == user.id and second.document_type == "floor_plan"


def test_an_unreadable_file_is_recorded_with_zeros(client: TestClient, db: Session, billing: Billing) -> None:
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = str(client.post(f"{API}/applications", headers=h).json()["id"])
    assert upload(client, h, app_id, "floor_plan", "empty.txt", b" \n " * 20, "text/plain").status_code == 201
    (row,) = _usage(db)
    assert row.outcome == "unreadable" and row.provider == "none" and row.user_id == user.id
    assert row.input_tokens == 0 and row.cost_usd == Decimal(0)


# ---- the same transaction ----


def test_a_failed_commit_leaves_no_orphan_row(
    client: TestClient, db: Session, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first attempt to store the result fails after the usage row was added to the session. The
    rollback takes the row with it: the retry writes the same run id again without a unique violation, and
    exactly one row survives."""
    real = module.record_usage
    calls: list[int] = []

    def flaky(*args: object, **kwargs: object) -> AiUsage:
        row = real(*args, **kwargs)  # type: ignore[arg-type]
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("the connection dropped")
        return row

    monkeypatch.setattr(module, "record_usage", flaky)
    _operator_upload(client, db)
    run = db.scalar(select(VerificationRun))
    assert run is not None and run.status == VerificationStatus.FAILED  # the crash handler's outcome
    (row,) = _usage(db)
    assert row.outcome == "failed" and row.run_id == run.id and len(calls) == 2


def test_the_row_and_the_result_are_in_one_transaction(
    client: TestClient, db: Session, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Seen from another connection right after the commit, the result and its usage row are both there."""
    seen: list[tuple[int, int]] = []
    real = module.publish

    def look(row: AiUsage, ref: str | None, *, announce: bool) -> None:
        with dbmod.session_factory()() as other:
            done = other.scalar(
                select(func.count()).select_from(VerificationRun).where(VerificationRun.status != "pending")
            )
            seen.append((int(done or 0), int(other.scalar(select(func.count()).select_from(AiUsage)) or 0)))
        real(row, ref, announce=announce)

    monkeypatch.setattr(module, "publish", look)
    _operator_upload(client, db)
    assert seen == [(1, 1)]  # after the commit the result and the usage row are both there


def test_worker_mode_writes_the_row_with_the_result(
    client: TestClient, db: Session, worker_mode: None, billing: Billing
) -> None:
    _price(db)
    user, _, _ = _operator_upload(client, db)
    assert _usage(db) == []  # queued: nothing has run
    run_id = claim_next_run("w")
    assert run_id is not None
    execute_run(run_id, "w")
    (row,) = _usage(db)
    assert row.run_id == run_id and row.user_id == user.id and row.cost_usd == Decimal("0.00060800")


def test_a_run_the_workers_gave_up_on_is_recorded_as_dead(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    user, _, _ = _operator_upload(client, db)
    for _ in range(MAX_ATTEMPTS):
        run_id = claim_next_run("doomed")
        assert run_id is not None
        db.execute(
            update(VerificationRun)
            .where(VerificationRun.id == run_id)
            .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
        )
        db.commit()
        reap_expired_runs()
    (row,) = _usage(db)
    assert (row.run_id, row.outcome, row.user_id) == (run_id, "dead", user.id)
    assert (row.input_tokens, row.cost_usd) == (0, Decimal(0))


def test_a_queued_check_swept_on_startup_is_recorded_once(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    _operator_upload(client, db)
    assert mark_stale_runs_failed() == 1
    assert mark_stale_runs_failed() == 0
    (row,) = _usage(db)
    assert row.outcome == "failed"


# ---- the administrator's page ----


def _seed_rows(client: TestClient, db: Session) -> tuple[User, str]:
    """Three checks: operator A ran two on one application, operator B one on another. Returns A and B's
    application id."""
    a, a_app, ha = _operator_upload(client, db, "a@example.sg")
    assert upload(client, ha, a_app, "floor_plan", "plan.txt", TXT, "text/plain").status_code == 201
    _, b_app, _ = _operator_upload(client, db, "b@example.sg")
    return a, b_app


def test_the_page_lists_filters_and_totals(client: TestClient, db: Session, billing: Billing) -> None:
    _price(db)
    a, b_app = _seed_rows(client, db)
    adm = _admin(client, db)
    body = client.get(f"{API}/admin/ai-usage", headers=adm).json()
    assert len(body["items"]) == 3 and body["next_cursor"] is None
    totals = body["totals"]
    assert "avg_latency_ms" in totals  # its own tests below
    assert {k: v for k, v in totals.items() if k != "avg_latency_ms"} == {
        "runs": 3,
        "input_tokens": 3600,
        "output_tokens": 240,
        "cost_usd": "0.00182400",
    }
    first = body["items"][0]
    assert first["user_name"] == "B" and first["reference_no"].startswith("PF-")
    assert first["document_type"] == "business_profile" and first["cost_usd"] == "0.00060800"

    by_user = client.get(f"{API}/admin/ai-usage", headers=adm, params={"user_id": str(a.id)}).json()
    assert len(by_user["items"]) == 2 and by_user["totals"]["runs"] == 2
    by_app = client.get(f"{API}/admin/ai-usage", headers=adm, params={"application_id": b_app}).json()
    assert len(by_app["items"]) == 1 and by_app["items"][0]["application_id"] == b_app
    nobody = client.get(f"{API}/admin/ai-usage", headers=adm, params={"user_id": str(uuid.uuid4())}).json()
    assert nobody["items"] == [] and nobody["totals"]["runs"] == 0 and nobody["totals"]["cost_usd"] == "0"


def test_the_day_range_uses_singapore_days_both_ends_included(
    client: TestClient, db: Session, billing: Billing
) -> None:
    _seed_rows(client, db)
    adm = _admin(client, db)
    rows = _usage(db)
    old = datetime(2026, 3, 10, 18, 30, tzinfo=UTC)  # 11 March 02:30 in Singapore
    db.execute(update(AiUsage).where(AiUsage.id == rows[0].id).values(created_at=old))
    db.commit()

    def count(**params: str) -> int:
        r = client.get(f"{API}/admin/ai-usage", headers=adm, params=params)
        assert r.status_code == 200, r.text
        return len(r.json()["items"])

    assert count(**{"from": "2026-03-11", "to": "2026-03-11"}) == 1
    assert count(**{"from": "2026-03-10", "to": "2026-03-10"}) == 0  # still the 10th in UTC, not in Singapore
    assert count(**{"from": "2026-03-12"}) == 2
    assert count(**{"to": "2026-03-11"}) == 1
    bad = client.get(f"{API}/admin/ai-usage", headers=adm, params={"from": "2026-03-12", "to": "2026-03-11"})
    assert bad.status_code == 400 and bad.json()["error"]["details"]["reason"] == "bad_range"
    assert client.get(f"{API}/admin/ai-usage", headers=adm, params={"from": "not-a-date"}).status_code == 422


def test_pages_follow_the_cursor_without_gaps_and_totals_cover_every_page(
    client: TestClient, db: Session, billing: Billing
) -> None:
    _seed_rows(client, db)
    adm = _admin(client, db)
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(5):
        params = {"limit": "2", **({"before": cursor} if cursor else {})}
        body = client.get(f"{API}/admin/ai-usage", headers=adm, params=params).json()
        seen += [i["id"] for i in body["items"]]
        assert body["totals"]["runs"] == 3
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert len(seen) == len(set(seen)) == 3
    assert client.get(f"{API}/admin/ai-usage", headers=adm, params={"before": "junk"}).status_code == 400
    assert client.get(f"{API}/admin/ai-usage", headers=adm, params={"limit": "101"}).status_code == 422


def test_today_is_shown_against_the_live_daily_cap(client: TestClient, db: Session, billing: Billing) -> None:
    _price(db)
    _seed_rows(client, db)
    adm = _admin(client, db)
    today = client.get(f"{API}/admin/ai-usage", headers=adm).json()["today"]
    assert today == {
        "runs": 3,
        "input_tokens": 3600,
        "output_tokens": 240,
        "cost_usd": "0.00182400",
        "daily_cap": get_settings().ai_runs_per_day,
    }
    client.put(
        f"{API}/admin/settings/ai_runs_per_day",
        headers=adm,
        json={"value": 50, "reason": "Spend review", "password": DEFAULT_PASSWORD},
    )
    assert client.get(f"{API}/admin/ai-usage", headers=adm).json()["today"]["daily_cap"] == 50


@pytest.mark.parametrize("path", ["/admin/ai-usage", "/admin/ai-usage.csv"])
def test_only_administrators_may_read_it(client: TestClient, db: Session, path: str) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    make_user(db, "off@example.sg", Role.OFFICER)
    assert client.get(f"{API}{path}").status_code == 401
    for email in ("op@example.sg", "off@example.sg"):
        r = client.get(f"{API}{path}", headers=login(client, email))
        assert r.status_code == 403, (email, r.text)
    assert client.get(f"{API}{path}", headers=_admin(client, db)).status_code == 200


# ---- the fields the admin screen needs ----


def _ledger_row(db: Session, **fields: object) -> AiUsage:
    values: dict[str, object] = {
        "run_id": uuid.uuid4(),
        "document_id": uuid.uuid4(),
        "document_type": "floor_plan",
        "provider": "openai",
        "outcome": "verified",
        **fields,
    }
    row = AiUsage(**values)
    db.add(row)
    db.commit()
    return row


def test_average_latency_counts_only_checks_that_reached_a_provider(client: TestClient, db: Session) -> None:
    adm = _admin(client, db)
    empty = client.get(f"{API}/admin/ai-usage", headers=adm).json()["totals"]
    assert empty["avg_latency_ms"] is None  # no rows at all
    _ledger_row(db, latency_ms=1000)
    _ledger_row(db, latency_ms=3000, provider="mock")
    _ledger_row(db, latency_ms=0, provider="none", outcome="unavailable")  # quota refusal or pause
    _ledger_row(db, latency_ms=0, provider="openai", outcome="dead")  # a dead run has no latency
    _ledger_row(db, latency_ms=450, provider="none", outcome="unreadable")  # never reached a provider
    body = client.get(f"{API}/admin/ai-usage", headers=adm).json()
    assert body["totals"]["runs"] == 5 and body["totals"]["avg_latency_ms"] == 2000


def test_average_latency_is_null_when_nothing_reached_a_provider(client: TestClient, db: Session) -> None:
    adm = _admin(client, db)
    _ledger_row(db, latency_ms=0, provider="none", outcome="unavailable")
    totals = client.get(f"{API}/admin/ai-usage", headers=adm).json()["totals"]
    assert totals["runs"] == 1 and totals["avg_latency_ms"] is None


def test_each_row_names_the_business_from_the_application_and_a_deleted_draft_has_none(
    client: TestClient, db: Session, billing: Billing
) -> None:
    _, kept_app, _ = _operator_upload(client, db, "a@example.sg")
    _, gone_app, h = _operator_upload(client, db, "b@example.sg")
    adm = _admin(client, db)
    items = {i["application_id"]: i for i in client.get(f"{API}/admin/ai-usage", headers=adm).json()["items"]}
    assert items[kept_app]["business_name"] == VALID_BUSINESS["business_name"]
    assert "business_name" not in {c.name for c in AiUsage.__table__.columns}  # display only, not stored
    assert client.delete(f"{API}/applications/{gone_app}", headers=h).status_code in (200, 204)
    after = {i["application_id"]: i for i in client.get(f"{API}/admin/ai-usage", headers=adm).json()["items"]}
    assert after[gone_app]["business_name"] is None and after[gone_app]["reference_no"] is None
    assert after[kept_app]["business_name"] == VALID_BUSINESS["business_name"]
    import csv
    import io

    rows = list(
        csv.reader(io.StringIO(client.get(f"{API}/admin/ai-usage.csv", headers=adm).text, newline=""))
    )
    col = rows[0].index("business_name")
    assert rows[0][1:3] == ["reference_no", "business_name"]
    assert {r[col] for r in rows[1:]} == {VALID_BUSINESS["business_name"], ""}


def test_the_reference_filter_is_exact_on_both_routes_and_unknown_means_empty(
    client: TestClient, db: Session, billing: Billing
) -> None:
    a, b_app = _seed_rows(client, db)
    adm = _admin(client, db)
    b_row = db.get(Application, uuid.UUID(b_app))
    other_row = db.scalar(select(Application).where(Application.operator_id == a.id))
    assert b_row is not None and other_row is not None
    ref, other = b_row.reference_no, str(other_row.id)
    body = client.get(f"{API}/admin/ai-usage", headers=adm, params={"reference": ref}).json()
    assert body["items"] and {i["reference_no"] for i in body["items"]} == {ref}
    assert body["totals"]["runs"] == len(body["items"])
    csv_lines = client.get(f"{API}/admin/ai-usage.csv", headers=adm, params={"reference": ref}).text.strip()
    assert len(csv_lines.split("\r\n")) == 1 + len(body["items"]) and ref in csv_lines
    for unknown in ("PF-1999-000001", ref[:-1], ref.lower(), "%"):  # no prefix, case or wildcard match
        r = client.get(f"{API}/admin/ai-usage", headers=adm, params={"reference": unknown})
        assert r.status_code == 200 and r.json()["items"] == [] and r.json()["totals"]["runs"] == 0
        c = client.get(f"{API}/admin/ai-usage.csv", headers=adm, params={"reference": unknown})
        assert c.status_code == 200 and len(c.text.strip().split("\r\n")) == 1  # the header only
    # alongside application_id: both must hold
    both = client.get(
        f"{API}/admin/ai-usage", headers=adm, params={"reference": ref, "application_id": other}
    )
    assert both.json()["items"] == []
    assert client.get(f"{API}/admin/ai-usage", headers=adm, params={"reference": "x" * 21}).status_code == 422


# ---- the CSV ----


def test_csv_is_streamed_with_every_column_and_the_filters(
    client: TestClient, db: Session, billing: Billing
) -> None:
    _price(db)
    _, b_app = _seed_rows(client, db)
    adm = _admin(client, db)
    r = client.get(f"{API}/admin/ai-usage.csv", headers=adm)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="ai-usage.csv"' in r.headers["content-disposition"]
    assert r.headers["cache-control"] == "no-store"
    lines = r.text.strip().split("\r\n")
    assert lines[0].split(",")[:4] == ["created_at", "reference_no", "business_name", "application_id"]
    assert len(lines) == 4 and "0.00060800" in lines[1] and "1200,80" in lines[1]
    one = client.get(f"{API}/admin/ai-usage.csv", headers=adm, params={"application_id": b_app})
    assert len(one.text.strip().split("\r\n")) == 2
    assert (
        client.get(
            f"{API}/admin/ai-usage.csv", headers=adm, params={"from": "2026-03-12", "to": "2026-03-11"}
        ).status_code
        == 400
    )


@pytest.mark.parametrize("lead", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_cells_that_look_like_formulas_are_quoted(
    client: TestClient, db: Session, billing: Billing, lead: str
) -> None:
    user, _, _ = _operator_upload(client, db)
    evil = f'{lead}HYPERLINK("http://evil.example","click")'
    db.execute(update(User).where(User.id == user.id).values(full_name=evil))
    db.commit()
    r = client.get(f"{API}/admin/ai-usage.csv", headers=_admin(client, db))
    import csv
    import io

    rows = list(csv.reader(io.StringIO(r.text, newline="")))
    cell = rows[1][rows[0].index("user_name")]
    assert cell == "'" + evil  # shown as text, never evaluated
    assert not any(c.startswith(("=", "+", "-", "@", "\t", "\r")) for row in rows for c in row)


# ---- Prometheus ----


def _families() -> dict[str, set[tuple[tuple[str, str], ...]]]:
    out: dict[str, set[tuple[tuple[str, str], ...]]] = {}
    for family in REGISTRY.collect():
        if family.name.startswith("permitflow_ai_"):
            for s in family.samples:
                out.setdefault(family.name, set()).add(tuple(sorted(s.labels.items())))
    return out


def _sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_counters_move_by_document_type_and_outcome_with_bounded_labels(
    client: TestClient, db: Session, billing: Billing
) -> None:
    _price(db)
    labels = {"document_type": "business_profile"}
    _operator_upload(client, db)
    outcome = _usage(db)[0].outcome
    assert _sample("permitflow_ai_checks_total", **labels, outcome=outcome) >= 1
    assert _sample("permitflow_ai_tokens_total", kind="input", **labels, outcome=outcome) >= 1200
    assert _sample("permitflow_ai_tokens_total", kind="output", **labels, outcome=outcome) >= 80
    assert _sample("permitflow_ai_cost_usd_total", **labels, outcome=outcome) >= 0.000608
    for series in _families().values():
        for labelset in series:
            d = dict(labelset)
            if set(d) == {"kind"}:  # the unrecorded-tokens counter has no other label
                assert d["kind"] in {"input", "output"}
                continue
            assert set(d) <= {"document_type", "outcome", "kind"}  # never a user or an application
            assert d["document_type"] in DOCUMENT_TYPE_LABELS | {"other"}
            assert d["outcome"] in OUTCOME_LABELS | {"other"}
            assert d.get("kind", "input") in {"input", "output"}


def _counter_total(name: str) -> float:
    return sum(
        sample.value for family in REGISTRY.collect() for sample in family.samples if sample.name == name
    )


def test_the_counters_add_up_to_the_ledger(client: TestClient, db: Session, billing: Billing) -> None:
    _price(db)
    before = {n: _counter_total(n) for n in ("permitflow_ai_cost_usd_total", "permitflow_ai_checks_total")}
    _seed_rows(client, db)
    rows = _usage(db)
    cost = float(sum(r.cost_usd for r in rows))
    assert cost > 0
    assert _counter_total("permitflow_ai_cost_usd_total") - before["permitflow_ai_cost_usd_total"] == (
        pytest.approx(cost)
    )
    assert _counter_total("permitflow_ai_checks_total") - before["permitflow_ai_checks_total"] == len(rows)


def test_a_hostile_value_cannot_widen_the_label_set(db: Session) -> None:
    hostile = AiUsage(
        run_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_type="ops@example.sg",
        provider="none",
        outcome=str(uuid.uuid4()),
        input_tokens=1,
        output_tokens=1,
        cost_usd=Decimal("0.5"),
        latency_ms=1,
    )
    publish(hostile, None, announce=False)
    assert _sample("permitflow_ai_checks_total", document_type="other", outcome="other") >= 1
    flat = str(_families())
    assert "ops@example.sg" not in flat and str(hostile.outcome) not in flat


# ---- Telegram ----


class _Sent:
    def __init__(self) -> None:
        self.texts: list[str] = []

    def __call__(self, text: str) -> None:
        self.texts.append(text)


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> _Sent:
    spy = _Sent()
    monkeypatch.setattr(notifier, "notify", spy)
    return spy


def _switch(client: TestClient, adm: dict[str, str], on: bool) -> None:
    r = client.put(
        f"{API}/admin/settings/telegram_per_check_messages",
        headers=adm,
        json={"value": on, "reason": "Watching spend", "password": DEFAULT_PASSWORD},
    )
    assert r.status_code == 200, r.text


def test_no_per_check_message_while_the_switch_is_off(
    client: TestClient, db: Session, billing: Billing, sent: _Sent
) -> None:
    _operator_upload(client, db)
    assert sent.texts == []  # the setting is off by default
    assert len(_usage(db)) == 1


def test_one_message_per_check_with_no_personal_data_when_on(
    client: TestClient, db: Session, billing: Billing, sent: _Sent
) -> None:
    _price(db)
    adm = _admin(client, db)
    _switch(client, adm, True)
    sent.texts.clear()  # the settings change is announced by its own code, not by this story
    _operator_upload(client, db, name="Tan-Wei-Ling-passport.txt")
    (text,) = sent.texts
    app = db.scalar(select(Application))
    assert app is not None
    assert text.startswith("Document check: business profile · ") and "USD 0.0006" in text
    assert f"case {app.reference_no}" in text
    for private in ("op@example", "Tan", "Wei", "Kopi", "202312345K", "passport", "9123", "Op"):
        assert private not in text
    _switch(client, adm, False)
    sent.texts.clear()
    _operator_upload(client, db, "op2@example.sg")
    assert sent.texts == []


def test_a_failing_notifier_never_fails_the_check(
    client: TestClient, db: Session, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    adm = _admin(client, db)
    _switch(client, adm, True)

    def boom(text: str) -> None:
        raise OSError("telegram is down")

    monkeypatch.setattr(notifier, "notify", boom)
    _operator_upload(client, db)
    run = db.scalar(select(VerificationRun))
    assert run is not None and run.status != VerificationStatus.FAILED
    assert len(_usage(db)) == 1


def test_refused_and_swept_runs_send_no_message(client: TestClient, db: Session, sent: _Sent) -> None:
    adm = _admin(client, db)
    _switch(client, adm, True)
    client.put(
        f"{API}/admin/settings/ai_paused",
        headers=adm,
        json={"value": True, "reason": "Spend review", "password": DEFAULT_PASSWORD},
    )
    sent.texts.clear()
    _operator_upload(client, db)
    assert sent.texts == [] and len(_usage(db)) == 1


# ---- LangSmith metadata ----


class _Recorder(MockProvider):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[VerificationRequest] = []

    def verify(self, request: VerificationRequest) -> VerificationResult:
        self.requests.append(request)
        return super().verify(request)


def test_trace_metadata_carries_keyed_hashes_never_the_ids_or_the_email(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    rec = _Recorder()
    monkeypatch.setattr(module, "get_provider", lambda: rec)
    user, app_id, _ = _operator_upload(client, db)
    (request,) = rec.requests
    secret = get_settings().jwt_secret
    assert request.extra["user_pseudonym"] == pseudonym(secret, "user", user.id)
    assert request.extra["application_hash"] == pseudonym(secret, "application", uuid.UUID(app_id))
    flat = " ".join(str(v) for v in request.extra.values())
    assert str(user.id) not in flat and app_id not in flat and "op@example.sg" not in flat
    assert "application_id" not in request.extra and "user_id" not in request.extra
    assert request.document_type == "business_profile"


# ---- review fixes: undercounts, the export bound, rollbacks, ranges ----


def _unrecorded(kind: str) -> float:
    return _sample("permitflow_ai_unrecorded_tokens_total", kind=kind)


class _TwoAttempts(MockProvider):
    """Billed 1200/80 the first time it is asked and 900/50 the second: tells whose tokens a row holds."""

    name = "openai"
    model = MODEL
    calls = 0
    between: Callable[[], None] | None = None

    def verify(self, request: VerificationRequest) -> VerificationResult:
        type(self).calls += 1
        first = type(self).calls == 1
        self.input_tokens, self.output_tokens = (1200, 80) if first else (900, 50)
        if first and type(self).between is not None:
            type(self).between()  # while the first attempt is "in flight"
        return super().verify(request)


def test_a_lost_lease_leaves_one_row_with_the_new_holders_tokens_and_counts_the_dropped_ones(
    client: TestClient, db: Session, worker_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _price(db)
    _TwoAttempts.calls = 0
    monkeypatch.setattr(module, "get_provider", lambda: _TwoAttempts())
    _operator_upload(client, db)
    run_id = claim_next_run("a")
    assert run_id is not None

    def lose_the_lease() -> None:
        with dbmod.session_factory()() as other:
            other.execute(
                update(VerificationRun)
                .where(VerificationRun.id == run_id)
                .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
            )
            other.commit()
        assert reap_expired_runs() == (1, 0)
        assert claim_next_run("b") == run_id

    _TwoAttempts.between = staticmethod(lose_the_lease)  # type: ignore[assignment]
    before = (_unrecorded("input"), _unrecorded("output"))
    execute_run(run_id, "a")  # finishes after losing the lease: dropped
    (reserved,) = _usage(db)  # only the reservation: it holds no tokens until the new holder finishes
    assert reserved.input_tokens == 0
    assert (_unrecorded("input") - before[0], _unrecorded("output") - before[1]) == (1200, 80)
    execute_run(run_id, "b")
    (row,) = _usage(db)
    assert (row.input_tokens, row.output_tokens) == (900, 50)
    assert row.cost_usd == Decimal("0.00044000")  # (900 x 0.40 + 50 x 1.60) / 1e6


def test_a_draft_deleted_during_the_call_still_counts_toward_the_daily_quota(
    client: TestClient, db: Session, worker_mode: None, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Security audit run 7: the usage row exists before the provider is called, so deleting the draft while
    the call is in flight cannot hand the operator a free run (per-operator and platform count alike)."""
    adm = _admin(client, db)
    for key in ("ai_runs_per_user_per_day", "ai_runs_per_day"):
        r = client.put(
            f"{API}/admin/settings/{key}",
            headers=adm,
            json={"value": 1, "reason": "Quota test", "password": DEFAULT_PASSWORD},
        )
        assert r.status_code == 200, r.text
    user, app_id, h = _operator_upload(client, db)
    real = billing.verify

    def delete_while_in_flight(request: VerificationRequest) -> VerificationResult:
        assert client.delete(f"{API}/applications/{app_id}", headers=h).status_code == 204
        return real(request)

    monkeypatch.setattr(billing, "verify", delete_while_in_flight)
    run_id = claim_next_run("w")
    assert run_id is not None
    execute_run(run_id, "w")
    (row,) = _usage(db)
    assert row.run_id == run_id and row.quota_operator_id == user.id
    again = client.post(f"{API}/applications", headers=h).json()["id"]
    refused = upload(client, h, again, "business_profile", "again.txt", PROFILE_TXT, "text/plain").json()
    assert refused["document"]["verification"]["error_reason"] == "daily_limit_reached"


def test_a_run_ended_by_the_reaper_settles_its_reserved_usage_row(
    client: TestClient, db: Session, worker_mode: None, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, _ = _operator_upload(client, db)
    run_id = claim_next_run("w")
    assert run_id is not None
    monkeypatch.setattr(billing, "verify", lambda request: (_ for _ in ()).throw(SystemExit()))
    with pytest.raises(SystemExit):
        execute_run(run_id, "w")  # the process dies in the call: only the reservation is left
    (row,) = _usage(db)
    assert row.outcome == "running"
    db.execute(update(VerificationRun).where(VerificationRun.id == run_id).values(attempts=MAX_ATTEMPTS))
    db.execute(
        update(VerificationRun)
        .where(VerificationRun.id == run_id)
        .values(lease_until=datetime.now(UTC) - timedelta(seconds=1))
    )
    db.commit()
    assert reap_expired_runs() == (0, 1)
    (row,) = _usage(db)
    assert row.outcome == "dead"


def test_a_draft_deleted_after_the_call_counts_its_billed_tokens_as_unrecorded(
    client: TestClient, db: Session, worker_mode: None, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, app_id, h = _operator_upload(client, db)
    real = billing.verify

    def verify_then_delete(request: VerificationRequest) -> VerificationResult:
        out = real(request)
        client.delete(f"{API}/applications/{app_id}", headers=h)
        return out

    monkeypatch.setattr(billing, "verify", verify_then_delete)
    before = _unrecorded("input")
    run_id = claim_next_run("w")
    assert run_id is not None
    execute_run(run_id, "w")
    (reserved,) = _usage(db)  # the reservation made before the call; the dropped result adds no tokens to it
    assert reserved.input_tokens == 0 and _unrecorded("input") - before == 1200


class _BilledThenRefused(MockProvider):
    name = "openai"
    model = MODEL

    def verify(self, request: VerificationRequest) -> VerificationResult:
        self.input_tokens, self.output_tokens = 1200, 80
        raise ProviderError("the answer did not match the schema")


def test_billed_then_a_provider_error_records_the_billed_tokens(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _price(db)
    monkeypatch.setattr(module, "get_provider", lambda: _BilledThenRefused())
    _operator_upload(client, db)
    (row,) = _usage(db)
    assert (row.outcome, row.provider, row.model) == ("failed", "openai", MODEL)
    assert (row.input_tokens, row.output_tokens, row.cost_usd) == (1200, 80, Decimal("0.00060800"))


def test_a_crash_after_the_provider_answered_keeps_the_billed_tokens(
    client: TestClient, db: Session, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    _price(db)

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("the rules crashed")

    monkeypatch.setattr(module, "apply_rules", boom)
    _operator_upload(client, db)
    (row,) = _usage(db)
    assert (row.outcome, row.provider) == ("failed", "openai")
    assert (row.input_tokens, row.output_tokens) == (1200, 80)


def test_the_stranded_inline_sweep_writes_one_failed_row(
    client: TestClient, db: Session, worker_mode: None
) -> None:
    user, _, _ = _operator_upload(client, db)
    run = db.scalar(select(VerificationRun))
    assert run is not None
    db.execute(
        update(VerificationRun)
        .where(VerificationRun.id == run.id)
        .values(status=VerificationStatus.RUNNING, started_at=datetime.now(UTC) - timedelta(days=1))
    )
    db.commit()
    reap_expired_runs()
    reap_expired_runs()
    (row,) = _usage(db)
    assert (row.run_id, row.outcome, row.user_id) == (run.id, "failed", user.id)
    assert (row.input_tokens, row.cost_usd) == (0, Decimal(0))


def test_a_sweep_that_meets_an_existing_row_changes_nothing(client: TestClient, db: Session) -> None:
    _operator_upload(client, db)
    (before,) = _usage(db)
    db.execute(update(VerificationRun).values(status=VerificationStatus.PENDING))  # as the edge test does
    db.commit()
    assert mark_stale_runs_failed() == 1
    (after,) = _usage(db)
    assert (after.id, after.outcome) == (before.id, before.outcome)


def test_a_price_change_after_the_check_started_does_not_reprice_it(db: Session) -> None:
    """Priced at the moment the run started, not at the moment the row is written."""
    _price(db, datetime(2025, 1, 1, tzinfo=UTC), "0.40", "1.60")
    _price(db, datetime(2026, 1, 1, tzinfo=UTC), "1.00", "2.00")
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    app = Application(operator_id=user.id, reference_no="PF-2026-009999")
    db.add(app)
    db.flush()
    doc = Document(
        application_id=app.id,
        document_type=DocumentType.FLOOR_PLAN,
        original_filename="p.txt",
        stored_key="k-us100-price",
        content_type="text/plain",
        size_bytes=1,
        sha256="0" * 64,
        uploaded_by=user.id,
    )
    db.add(doc)
    db.flush()
    run = VerificationRun(id=uuid.uuid4(), document_id=doc.id, started_at=datetime(2025, 6, 1, tzinfo=UTC))
    row = record_usage(
        db,
        run=run,
        doc=doc,
        outcome=VerificationStatus.VERIFIED,
        provider="openai",
        model=MODEL,
        input_tokens=1200,
        output_tokens=80,
    )
    db.commit()
    assert row.cost_usd == Decimal("0.00060800")  # the 2025 price, not the 2026 one in force today
    never_started = VerificationRun(
        id=uuid.uuid4(), document_id=doc.id, created_at=datetime(2026, 5, 1, tzinfo=UTC)
    )
    later = record_usage(
        db, run=never_started, doc=doc, outcome=VerificationStatus.FAILED, provider="openai", model=MODEL,
        input_tokens=1000, output_tokens=0,
    )  # fmt: skip
    assert later.cost_usd == Decimal("0.00100000")  # no start: priced when it was created


def test_a_run_held_then_retried_keeps_one_row_with_the_final_outcome_and_summed_tokens(db: Session) -> None:
    _price(db, datetime(2025, 1, 1, tzinfo=UTC), "0.40", "1.60")
    user = make_user(db, "op@example.sg", Role.OPERATOR)
    app = Application(operator_id=user.id, reference_no="PF-2026-009998")
    db.add(app)
    db.flush()
    doc = Document(
        application_id=app.id,
        document_type=DocumentType.FLOOR_PLAN,
        original_filename="p.txt",
        stored_key="k-us100-retry",
        content_type="text/plain",
        size_bytes=1,
        sha256="0" * 64,
        uploaded_by=user.id,
    )
    db.add(doc)
    db.flush()
    run = VerificationRun(id=uuid.uuid4(), document_id=doc.id, started_at=datetime(2025, 6, 1, tzinfo=UTC))
    first = (VerificationStatus.UNAVAILABLE, 100, 10, 0)
    final = (VerificationStatus.VERIFIED, 1200, 80, 5)
    for outcome, tin, tout, ms in (first, final):
        last = record_usage(
            db, run=run, doc=doc, outcome=outcome, provider="openai", model=MODEL,
            input_tokens=tin, output_tokens=tout, latency_ms=ms,
        )  # fmt: skip
        db.commit()
    db.commit()
    (row,) = db.scalars(select(AiUsage).where(AiUsage.run_id == run.id))
    assert (row.outcome, row.input_tokens, row.output_tokens, row.latency_ms) == ("verified", 1300, 90, 5)
    assert row.cost_usd == Decimal("0.00066400")  # 0.000056 (held) + 0.000608 (final)
    assert (last.input_tokens, last.output_tokens) == (1200, 80)  # what publish counts: this attempt only


def test_extreme_and_invalid_ranges_are_400_not_500(client: TestClient, db: Session) -> None:
    adm = _admin(client, db)
    for path in ("ai-usage", "ai-usage.csv"):
        for params in (
            {"from": "0001-01-01"},
            {"from": "0001-01-01", "to": "9999-12-31"},
            {"from": "2026-03-12", "to": "2026-03-11"},
        ):
            r = client.get(f"{API}/admin/{path}", headers=adm, params=params)
            assert r.status_code == 400, (path, params, r.status_code)
            assert r.json()["error"]["details"]["reason"] == "bad_range"
        for params in ({"to": "9999-12-31"}, {"from": "9999-12-31"}, {"from": "0001-01-02"}):
            assert client.get(f"{API}/admin/{path}", headers=adm, params=params).status_code in (200, 400)
        assert client.get(f"{API}/admin/{path}", headers=adm, params={"to": "2026-13-45"}).status_code == 422
    assert client.get(f"{API}/admin/ai-usage", headers=adm, params={"before": "junk"}).status_code == 400
    assert (
        client.get(f"{API}/admin/ai-usage", headers=adm, params={"before": "9" * 50 + ",x"}).status_code
        == 400
    )


def test_the_csv_follows_the_day_range(client: TestClient, db: Session, billing: Billing) -> None:
    _seed_rows(client, db)
    adm = _admin(client, db)
    rows = _usage(db)
    db.execute(
        update(AiUsage)
        .where(AiUsage.id == rows[0].id)
        .values(created_at=datetime(2026, 3, 10, 18, 30, tzinfo=UTC))
    )
    db.commit()

    def lines(**params: str) -> int:
        r = client.get(f"{API}/admin/ai-usage.csv", headers=adm, params=params)
        assert r.status_code == 200, r.text
        return len(r.text.strip().split("\r\n")) - 1

    assert lines(**{"from": "2026-03-11", "to": "2026-03-11"}) == 1  # 11 March in Singapore
    assert lines(**{"from": "2026-03-10", "to": "2026-03-10"}) == 0
    assert lines(**{"from": "2026-03-12"}) == 2
    assert lines() == 3


def test_the_export_is_cut_at_the_cap_with_a_notice_and_is_audited(
    client: TestClient, db: Session, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = _seed_rows(client, db)[0]
    adm = _admin(client, db)
    monkeypatch.setattr(ai_usage_module, "CSV_MAX_ROWS", 2)
    r = client.get(f"{API}/admin/ai-usage.csv", headers=adm, params={"user_id": str(user.id)})
    lines = r.text.strip().split("\r\n")
    assert len(lines) == 1 + 2  # the header and the user's two rows: exactly at the cap, so not cut
    r = client.get(f"{API}/admin/ai-usage.csv", headers=adm)
    lines = r.text.strip().split("\r\n")
    assert len(lines) == 1 + 2 + 1  # header, two rows, then the notice
    assert lines[-1].startswith('"Export cut at 2 rows. Narrow it with from, to, user_id')
    events = [e for e in db.scalars(select(AuditEvent)) if e.event_type == "admin.ai_usage_exported"]
    assert [(e.payload["rows"], e.payload["cut"]) for e in events] == [(2, False), (2, True)]
    assert events[-1].payload["user_id"] is None and events[-1].actor_id is not None
    assert set(events[-1].payload) == {
        "user_id",
        "application_id",
        "reference",
        "since",
        "until",
        "rows",
        "cut",
    }
    assert user.full_name not in str(events[0].payload) and "@example" not in str(events[0].payload)


def test_the_export_runs_under_a_statement_timeout(
    client: TestClient, db: Session, billing: Billing, monkeypatch: pytest.MonkeyPatch
) -> None:
    _operator_upload(client, db)
    seen: list[str] = []
    real = AiUsageRepository.limit_statement_time

    def spy(self: AiUsageRepository, timeout: str) -> None:
        seen.append(timeout)
        real(self, timeout)

    monkeypatch.setattr(AiUsageRepository, "limit_statement_time", spy)
    assert client.get(f"{API}/admin/ai-usage.csv", headers=_admin(client, db)).status_code == 200
    assert seen == ["60s"]


def test_nothing_is_counted_for_a_refused_run_whose_transaction_rolls_back(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    adm = _admin(client, db)
    client.put(
        f"{API}/admin/settings/ai_paused",
        headers=adm,
        json={"value": True, "reason": "Spend review", "password": DEFAULT_PASSWORD},
    )
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = str(client.post(f"{API}/applications", headers=h).json()["id"])
    labels = {"document_type": "business_profile", "outcome": "unavailable"}
    before = _sample("permitflow_ai_checks_total", **labels)
    real = AuditRepository.record

    def failing(self: AuditRepository, **kw: Any) -> AuditEvent:
        if kw["event_type"] == "document.uploaded":
            raise RuntimeError("the database went away")
        return real(self, **kw)

    with monkeypatch.context() as patched:
        patched.setattr(AuditRepository, "record", failing)
        failed = upload(client, h, app_id, "business_profile", "profile.txt", PROFILE_TXT, "text/plain")
        assert failed.status_code == 500
    assert _sample("permitflow_ai_checks_total", **labels) == before
    assert _usage(db) == []
    # and a committed one is counted once
    assert (
        upload(client, h, app_id, "business_profile", "profile.txt", PROFILE_TXT, "text/plain").status_code
        == 201
    )
    assert _sample("permitflow_ai_checks_total", **labels) == before + 1


# ---- Telegram: no line for a check that never reached a provider ----


def test_no_line_for_a_check_that_never_reached_a_provider_at_either_point(
    client: TestClient, db: Session, billing: Billing, sent: _Sent, monkeypatch: pytest.MonkeyPatch
) -> None:
    adm = _admin(client, db)
    _switch(client, adm, True)
    sent.texts.clear()
    # an unreadable file: the run ends at extraction
    make_user(db, "op@example.sg", Role.OPERATOR)
    h = login(client, "op@example.sg")
    app_id = str(client.post(f"{API}/applications", headers=h).json()["id"])
    assert upload(client, h, app_id, "floor_plan", "empty.txt", b" \n " * 20, "text/plain").status_code == 201
    assert sent.texts == []
    # paused after the check was created: stopped at execution, before any provider is chosen
    monkeypatch.setattr(get_settings(), "verification_mode", "worker")
    assert (
        upload(client, h, app_id, "business_profile", "profile.txt", PROFILE_TXT, "text/plain").status_code
        == 201
    )
    client.put(
        f"{API}/admin/settings/ai_paused",
        headers=adm,
        json={"value": True, "reason": "Spend review", "password": DEFAULT_PASSWORD},
    )
    sent.texts.clear()  # the settings announcement is not a check
    run_id = claim_next_run("w")
    assert run_id is not None
    monkeypatch.setattr(get_settings(), "verification_mode", "inline")
    execute_run(run_id, "w")
    assert sent.texts == []
    outcomes = [(u.outcome, u.provider) for u in _usage(db)]
    assert outcomes == [("unreadable", "none"), ("unavailable", "none")]


def test_a_check_that_reached_the_provider_and_failed_still_gets_its_line(
    client: TestClient, db: Session, sent: _Sent, monkeypatch: pytest.MonkeyPatch
) -> None:
    adm = _admin(client, db)
    _switch(client, adm, True)
    sent.texts.clear()
    monkeypatch.setattr(module, "get_provider", lambda: _BilledThenRefused())
    _operator_upload(client, db)
    (text,) = sent.texts
    assert text.startswith("Document check: business profile · failed ·")


# ---- the migration ----


def _alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={**os.environ, "APP_ENV": "test"},
        check=True,
        capture_output=True,
    )


def test_migration_0017_seeds_the_price_and_round_trips(db: Session) -> None:
    db.close()
    dbmod.reset_engine()
    _alembic("downgrade", "0016")
    try:
        with dbmod.get_engine().connect() as conn:
            names = {r[0] for r in conn.exec_driver_sql("select tablename from pg_tables")}
            assert not {"ai_usage", "ai_prices"} & names
            cols = {
                r[0]
                for r in conn.exec_driver_sql(
                    "select column_name from information_schema.columns "
                    "where table_name = 'verification_runs'"
                )
            }
            assert "requested_by" not in cols
    finally:
        dbmod.reset_engine()
        _alembic("upgrade", "head")
        dbmod.reset_engine()
    with dbmod.get_engine().connect() as conn:
        seed = conn.exec_driver_sql(
            "select model, input_per_million, output_per_million from ai_prices"
        ).all()
        assert [(m, Decimal(i), Decimal(o)) for m, i, o in seed] == [(MODEL, Decimal("0.4"), Decimal("1.6"))]
        assert conn.exec_driver_sql("select count(*) from ai_usage").scalar() == 0


# ---- nothing else about the check changed ----


def test_the_audit_trail_and_the_run_are_unchanged_by_the_record(
    client: TestClient, db: Session, billing: Billing
) -> None:
    _operator_upload(client, db)
    events = [e for e in db.scalars(select(AuditEvent)) if e.event_type == "verification.completed"]
    assert (
        len(events) == 1 and "cost" not in str(events[0].payload) and "tokens" not in str(events[0].payload)
    )
