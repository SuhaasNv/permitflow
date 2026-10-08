"""US-101: platform settings. Authorization on every route, the bounds, the step-up, the audit row, the
history and revert, and every consumer reading the live value."""

import uuid
from collections.abc import Iterator
from typing import NoReturn

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response  # what Starlette's TestClient returns
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.v1 import auth as auth_module
from app.core.rate_limit import FailedLoginLimiter, RequestLimiter
from app.core.settings import get_settings
from app.infra import notifier
from app.main import build_request_limiter
from app.models import AuditEvent, PlatformSetting, User, VerificationRun
from app.models.enums import Role, VerificationStatus
from app.repositories.documents import DocumentRepository
from app.services.platform_settings import live
from tests.factories import DEFAULT_PASSWORD, login, make_user
from tests.journeys import PDF, TXT, draft, upload

API = "/api/v1"
SETTINGS = f"{API}/admin/settings"


def _admin(client: TestClient, db: Session) -> dict[str, str]:
    make_user(db, "adm@example.sg", Role.ADMIN, protected=True)
    return login(client, "adm@example.sg")


def _put(
    client: TestClient,
    h: dict[str, str],
    key: str,
    value: object,
    *,
    reason: str = "Load from the open day",
    password: str = DEFAULT_PASSWORD,
) -> Response:
    return client.put(
        f"{SETTINGS}/{key}", headers=h, json={"value": value, "reason": reason, "password": password}
    )


def _install_limiter(client: TestClient, limiter: RequestLimiter) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    app.state.limiter = limiter


def _installed_limiter(client: TestClient) -> RequestLimiter:
    app = client.app
    assert isinstance(app, FastAPI)
    limiter = app.state.limiter
    assert isinstance(limiter, RequestLimiter)
    return limiter


def _by_key(client: TestClient, h: dict[str, str]) -> dict[str, dict[str, object]]:
    body = client.get(SETTINGS, headers=h).json()
    return {s["key"]: s for s in body["settings"]}


def _events(db: Session, *types: str) -> list[AuditEvent]:
    db.expire_all()
    stmt = select(AuditEvent).where(AuditEvent.event_type.in_(types)).order_by(AuditEvent.created_at)
    return list(db.scalars(stmt))


@pytest.fixture
def announcements(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    sent: list[str] = []
    monkeypatch.setattr(notifier, "notify", sent.append)
    return sent


# ---- authorization on every route ----

ROUTES = [
    ("GET", SETTINGS, None),
    ("GET", f"{SETTINGS}/history", None),
    ("PUT", f"{SETTINGS}/max_drafts_per_user", {"value": 5, "reason": "because", "password": "x"}),
    (
        "POST",
        f"{SETTINGS}/history/{uuid.uuid4()}/revert",
        {"reason": "because", "password": "x"},
    ),
]


@pytest.mark.parametrize(("method", "url", "body"), ROUTES)
def test_unauthenticated_is_401(
    client: TestClient, method: str, url: str, body: dict[str, object] | None
) -> None:
    assert client.request(method, url, json=body).status_code == 401


@pytest.mark.parametrize("role", [Role.OPERATOR, Role.OFFICER])
@pytest.mark.parametrize(("method", "url", "body"), ROUTES)
def test_operators_and_officers_are_403(
    client: TestClient,
    db: Session,
    role: Role,
    method: str,
    url: str,
    body: dict[str, object] | None,
) -> None:
    make_user(db, "someone@example.sg", role)
    h = login(client, "someone@example.sg")
    r = client.request(method, url, headers=h, json=body)
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
    assert db.scalar(select(PlatformSetting)) is None


# ---- the list ----


def test_an_empty_table_lists_every_setting_at_its_environment_default(
    client: TestClient, db: Session
) -> None:
    h = _admin(client, db)
    body = client.get(SETTINGS, headers=h).json()
    assert body["environment"] == "test"
    s = _by_key(client, h)
    assert len(s) == 11
    env = get_settings()
    for key in (
        "rate_limit_per_minute",
        "login_attempts_per_minute",
        "ai_runs_per_user_per_day",
        "ai_runs_per_day",
        "max_drafts_per_user",
        "upload_max_bytes",
        "ai_max_text_chars",
        "worker_concurrency",
    ):
        assert s[key]["value"] == s[key]["default"] == getattr(env, key), key
        assert s[key]["overridden"] is False and s[key]["updated_by_name"] is None
    assert s["rate_limit_per_minute"]["minimum"] == 10
    assert s["rate_limit_per_minute"]["maximum"] == env.rate_limit_per_minute
    assert s["rate_limit_per_minute"]["max_source"] == "env"
    assert s["ai_paused"]["value"] is False and s["ai_paused"]["kind"] == "bool"
    assert s["scanner_fail_mode"]["value"] == "closed" and s["scanner_fail_mode"]["choices"] == [
        "closed",
        "open",
    ]
    # Stored for later stories, and honest about it.
    assert {k for k, v in s.items() if not v["in_use"]} == {
        "worker_concurrency",
        "telegram_per_check_messages",
        "scanner_fail_mode",
    }
    assert s["upload_max_bytes"]["maximum"] == 10 * 1024 * 1024
    assert "password" not in str(body).lower()


# ---- a change: stored, audited, announced, live ----


def test_a_change_is_stored_audited_announced_and_listed(
    client: TestClient, db: Session, announcements: list[str]
) -> None:
    h = _admin(client, db)
    r = _put(client, h, "max_drafts_per_user", 5, reason="Quiet week, fewer drafts")
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["value"] == 5 and out["default"] == 20 and out["overridden"] is True
    assert out["updated_by_name"] == "Adm" and out["reason"] == "Quiet week, fewer drafts"
    row = db.get(PlatformSetting, "max_drafts_per_user")
    assert row is not None and row.value == 5
    (event,) = _events(db, "settings.changed")
    assert event.application_id is None
    assert event.payload["key"] == "max_drafts_per_user"
    assert (event.payload["old"], event.payload["new"], event.payload["old_was_default"]) == (20, 5, True)
    assert event.payload["reason"] == "Quiet week, fewer drafts"
    assert "password" not in event.payload
    assert len(announcements) == 1
    assert "Drafts per person: 20 -> 5" in announcements[0] and "Quiet week" in announcements[0]
    assert live().int_value("max_drafts_per_user") == 5
    assert _by_key(client, h)["max_drafts_per_user"]["value"] == 5
    # The admin feed reads it in words.
    feed = client.get(f"{API}/admin/audit-feed", headers=h).json()["events"]
    assert any(e["summary"] == "Setting changed: Drafts per person, 20 to 5" for e in feed)


def test_the_second_change_records_the_first_as_the_old_value(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    assert _put(client, h, "max_drafts_per_user", 5).status_code == 200
    assert _put(client, h, "max_drafts_per_user", 3).status_code == 200
    second = _events(db, "settings.changed")[-1].payload
    assert (second["old"], second["new"], second["old_was_default"]) == (5, 3, False)


def test_no_change_is_refused_and_leaves_no_audit_row(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    r = _put(client, h, "max_drafts_per_user", get_settings().max_drafts_per_user)
    assert r.status_code == 422 and r.json()["error"]["details"]["reason"] == "no_change"
    assert _events(db, "settings.changed") == [] and db.scalar(select(PlatformSetting)) is None


def test_setting_the_environment_default_clears_the_override_instead_of_storing_it(
    client: TestClient, db: Session
) -> None:
    h = _admin(client, db)
    assert _put(client, h, "max_drafts_per_user", 5).status_code == 200
    r = _put(client, h, "max_drafts_per_user", 20, reason="Back to the default")  # 20: the env value
    assert r.status_code == 200, r.text
    assert r.json()["value"] == 20 and r.json()["overridden"] is False
    db.expire_all()
    assert db.get(PlatformSetting, "max_drafts_per_user") is None
    last = _events(db, "settings.changed")[-1].payload
    assert (last["old"], last["new"], last["old_was_default"]) == (5, 20, False)
    assert live().int_value("max_drafts_per_user") == 20
    # With no row, setting the default again is still a no-op.
    again = _put(client, h, "max_drafts_per_user", 20)
    assert again.status_code == 422 and again.json()["error"]["details"]["reason"] == "no_change"


def test_an_override_equal_to_the_default_can_be_cleared_by_a_put_and_by_a_revert(
    client: TestClient, db: Session
) -> None:
    """A row left holding the default value (written before this rule, or by hand) used to be stuck: the
    effective value already equalled the default, so both routes answered no_change."""
    h = _admin(client, db)
    admin = make_user(db, "other@example.sg", Role.ADMIN)
    assert _put(client, h, "max_drafts_per_user", 5).status_code == 200
    first = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    row = db.get(PlatformSetting, "max_drafts_per_user")
    assert row is not None
    row.value = 20
    row.updated_by = admin.id
    db.commit()
    stuck = client.get(SETTINGS, headers=h).json()["settings"]
    assert next(s for s in stuck if s["key"] == "max_drafts_per_user")["overridden"] is True
    r = _revert(client, h, first["id"])  # the first entry: back to "following the environment"
    assert r.status_code == 200, r.text
    assert r.json()["overridden"] is False
    db.expire_all()
    assert db.get(PlatformSetting, "max_drafts_per_user") is None
    # The same through a PUT of the default.
    db.add(PlatformSetting(key="max_drafts_per_user", value=20, updated_by=admin.id, reason="stuck"))
    db.commit()
    r = _put(client, h, "max_drafts_per_user", 20)
    assert r.status_code == 200 and r.json()["overridden"] is False
    db.expire_all()
    assert db.get(PlatformSetting, "max_drafts_per_user") is None


def test_an_unknown_key_is_404(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    assert _put(client, h, "jwt_secret", 5).status_code == 404
    assert client.get(f"{SETTINGS}/history", headers=h, params={"key": "nope"}).status_code == 404


# ---- the bounds ----


@pytest.mark.parametrize(
    ("key", "value", "bound", "limit"),
    [
        ("rate_limit_per_minute", 241, "maximum", 240),
        ("rate_limit_per_minute", 9, "minimum", 10),
        ("rate_limit_per_minute", 0, "minimum", 10),
        ("login_attempts_per_minute", 21, "maximum", 20),
        ("ai_runs_per_user_per_day", 61, "maximum", 60),
        ("ai_runs_per_day", 1001, "maximum", 1000),
        ("ai_runs_per_day", 0, "minimum", 1),
        ("max_drafts_per_user", 21, "maximum", 20),
        ("upload_max_bytes", 10 * 1024 * 1024 + 1, "maximum", 10 * 1024 * 1024),
        ("ai_max_text_chars", 20_001, "maximum", 20_000),
        ("worker_concurrency", 3, "maximum", 2),
    ],
)
def test_out_of_bounds_is_422_naming_the_bound(
    client: TestClient, db: Session, key: str, value: int, bound: str, limit: int
) -> None:
    h = _admin(client, db)
    r = _put(client, h, key, value)
    assert r.status_code == 422, r.text
    err = r.json()["error"]
    assert err["code"] == "validation_failed"
    assert err["details"]["bound"] == bound and err["details"][bound] == limit
    assert str(limit) in err["message"]
    assert db.scalar(select(PlatformSetting)) is None and _events(db, "settings.changed") == []


def test_the_ceiling_follows_the_environment(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 50)
    h = _admin(client, db)
    assert _put(client, h, "rate_limit_per_minute", 51).status_code == 422
    assert _put(client, h, "rate_limit_per_minute", 50).status_code == 422  # no change: already 50
    assert _put(client, h, "rate_limit_per_minute", 40).status_code == 200
    assert _by_key(client, h)["rate_limit_per_minute"]["maximum"] == 50


def test_an_environment_of_zero_still_cannot_be_switched_off_or_raised_past_the_cap(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "ai_runs_per_day", 0)  # today: no platform limit
    h = _admin(client, db)
    s = _by_key(client, h)["ai_runs_per_day"]
    assert s["default"] == 0 and s["value"] == 0 and s["max_source"] == "cap"
    assert _put(client, h, "ai_runs_per_day", 0).status_code == 422
    assert _put(client, h, "ai_runs_per_day", 2_000_000).status_code == 422
    assert _put(client, h, "ai_runs_per_day", 300).status_code == 200


@pytest.mark.parametrize("value", ["12", 12.5, None, True])
def test_a_number_setting_refuses_other_types(client: TestClient, db: Session, value: object) -> None:
    h = _admin(client, db)
    r = _put(client, h, "rate_limit_per_minute", value)
    assert r.status_code == 422


def test_switches_and_choices_are_typed(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    assert _put(client, h, "ai_paused", "yes").status_code == 422
    assert _put(client, h, "ai_paused", 1).status_code == 422
    assert _put(client, h, "scanner_fail_mode", "maybe").status_code == 422
    assert _put(client, h, "ai_paused", True).status_code == 200
    assert _put(client, h, "telegram_per_check_messages", True).status_code == 200
    assert _put(client, h, "worker_concurrency", 1).status_code == 200


def test_fail_open_is_allowed_in_development_and_refused_in_production(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _admin(client, db)
    assert _put(client, h, "scanner_fail_mode", "open").status_code == 200
    assert _put(client, h, "scanner_fail_mode", "closed").status_code == 200
    monkeypatch.setattr(get_settings(), "app_env", "production")
    r = _put(client, h, "scanner_fail_mode", "open")
    assert r.status_code == 422
    assert r.json()["error"]["details"]["reason"] == "production_fail_open"
    assert _by_key(client, h)["scanner_fail_mode"]["choices"] == ["closed"]
    assert live().value("scanner_fail_mode") == "closed"


def test_a_row_written_around_the_api_cannot_loosen_a_limit_past_the_environment(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = make_user(db, "adm@example.sg", Role.ADMIN)
    db.add(
        PlatformSetting(key="rate_limit_per_minute", value=100_000, updated_by=admin.id, reason="hand edit")
    )
    db.add(PlatformSetting(key="scanner_fail_mode", value="open", updated_by=admin.id, reason="hand edit"))
    db.commit()
    monkeypatch.setattr(get_settings(), "app_env", "production")
    assert live().int_value("rate_limit_per_minute") == get_settings().rate_limit_per_minute
    assert live().value("scanner_fail_mode") == "closed"


# ---- the request body ----


def test_a_reason_and_a_password_are_required(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    url = f"{SETTINGS}/max_drafts_per_user"
    for body in (
        {"value": 5, "password": DEFAULT_PASSWORD},
        {"value": 5, "reason": "   ", "password": DEFAULT_PASSWORD},
        {"value": 5, "reason": "ok", "password": DEFAULT_PASSWORD},
        {"value": 5, "reason": "x" * 281, "password": DEFAULT_PASSWORD},
        {"value": 5, "reason": "A good reason"},
        {"value": 5, "reason": "A good reason", "password": ""},
        {"reason": "A good reason", "password": DEFAULT_PASSWORD},
    ):
        r = client.put(url, headers=h, json=body)
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_failed", body
    assert db.scalar(select(PlatformSetting)) is None


# ---- the step-up ----


def test_a_wrong_password_is_403_and_changes_nothing(
    client: TestClient, db: Session, announcements: list[str]
) -> None:
    h = _admin(client, db)
    r = _put(client, h, "max_drafts_per_user", 5, password="Not-The-Password-1")
    assert r.status_code == 403 and r.json()["error"]["code"] == "step_up_failed"
    assert db.scalar(select(PlatformSetting)) is None
    assert _events(db, "settings.changed") == [] and announcements == []


def test_a_wrong_password_on_a_change_is_audited_with_the_key_and_never_the_password(
    client: TestClient, db: Session
) -> None:
    h = _admin(client, db)
    r = _put(client, h, "max_drafts_per_user", 5, password="Not-The-Password-1")
    assert r.status_code == 403
    (event,) = _events(db, "settings.step_up_failed")
    adm = db.scalar(select(User).where(User.email == "adm@example.sg"))
    assert adm is not None and event.actor_id == adm.id and event.application_id is None
    assert event.payload == {"key": "max_drafts_per_user", "action": "change"}
    assert "Not-The-Password-1" not in str(event.payload)
    # It is not a change: the history and the setting are untouched, and the feed says it in words.
    assert client.get(f"{SETTINGS}/history", headers=h).json()["entries"] == []
    feed = client.get(f"{API}/admin/audit-feed", headers=h).json()["events"]
    assert any(e["summary"] == "Wrong password on a setting change: max_drafts_per_user" for e in feed)


def test_a_wrong_password_on_a_revert_is_audited_with_the_key(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    assert _put(client, h, "max_drafts_per_user", 5).status_code == 200
    entry = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    assert _revert(client, h, entry["id"], password="wrong-wrong-1").status_code == 403
    (event,) = _events(db, "settings.step_up_failed")
    assert event.payload == {
        "key": "max_drafts_per_user",
        "action": "revert",
        "history_entry": entry["id"],
    }
    # An id that is not a settings entry is still recorded, without a key.
    assert _revert(client, h, str(uuid.uuid4()), password="wrong-wrong-1").status_code == 403
    assert _events(db, "settings.step_up_failed")[-1].payload["key"] is None


def test_the_step_up_checks_the_signed_in_admins_own_password_not_another_admins(
    client: TestClient, db: Session
) -> None:
    make_user(db, "other@example.sg", Role.ADMIN, password="Other-Admin-Pass-7")
    h = _admin(client, db)
    assert _put(client, h, "max_drafts_per_user", 5, password="Other-Admin-Pass-7").status_code == 403
    assert _put(client, h, "max_drafts_per_user", 5).status_code == 200


def test_repeated_wrong_passwords_are_rate_limited_by_the_sign_in_limiter(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _admin(client, db)
    monkeypatch.setattr(auth_module, "login_limiter", FailedLoginLimiter(2))
    for _ in range(2):
        assert _put(client, h, "max_drafts_per_user", 5, password="wrong-wrong-1").status_code == 403
    r = _put(client, h, "max_drafts_per_user", 5, password="wrong-wrong-1")
    assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited"
    # Even the right password is refused while the client is blocked.
    assert _put(client, h, "max_drafts_per_user", 5).status_code == 429
    assert db.scalar(select(PlatformSetting)) is None


def test_the_step_up_runs_before_the_bounds_are_revealed(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    r = _put(client, h, "rate_limit_per_minute", 999_999, password="wrong-wrong-1")
    assert r.status_code == 403


# ---- history and revert ----


def test_history_lists_changes_newest_first_with_paging_and_a_key_filter(
    client: TestClient, db: Session
) -> None:
    h = _admin(client, db)
    assert client.get(f"{SETTINGS}/history", headers=h).json() == {"entries": [], "next_cursor": None}
    _put(client, h, "max_drafts_per_user", 5, reason="first one")
    _put(client, h, "rate_limit_per_minute", 100, reason="second one")
    _put(client, h, "max_drafts_per_user", 3, reason="third one")
    body = client.get(f"{SETTINGS}/history", headers=h).json()
    assert [e["reason"] for e in body["entries"]] == ["third one", "second one", "first one"]
    top = body["entries"][0]
    assert (top["key"], top["old"], top["new"], top["kind"]) == ("max_drafts_per_user", 5, 3, "changed")
    assert top["actor_name"] == "Adm" and top["label"] == "Drafts per person"
    page = client.get(f"{SETTINGS}/history", headers=h, params={"limit": 2}).json()
    assert len(page["entries"]) == 2 and page["next_cursor"]
    rest = client.get(
        f"{SETTINGS}/history", headers=h, params={"limit": 2, "before": page["next_cursor"]}
    ).json()
    assert [e["reason"] for e in rest["entries"]] == ["first one"] and rest["next_cursor"] is None
    only = client.get(f"{SETTINGS}/history", headers=h, params={"key": "max_drafts_per_user"}).json()
    assert [e["reason"] for e in only["entries"]] == ["third one", "first one"]
    assert client.get(f"{SETTINGS}/history", headers=h, params={"limit": 0}).status_code == 422


def _revert(client: TestClient, h: dict[str, str], event_id: str, **kw: str) -> Response:
    body = {"reason": kw.get("reason", "Putting it back"), "password": kw.get("password", DEFAULT_PASSWORD)}
    return client.post(f"{SETTINGS}/history/{event_id}/revert", headers=h, json=body)


def test_reverting_the_first_change_returns_the_setting_to_the_environment(
    client: TestClient, db: Session, announcements: list[str]
) -> None:
    h = _admin(client, db)
    _put(client, h, "max_drafts_per_user", 5)
    entry = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    r = _revert(client, h, entry["id"], reason="Back to normal")
    assert r.status_code == 200, r.text
    assert r.json()["value"] == 20 and r.json()["overridden"] is False
    assert db.get(PlatformSetting, "max_drafts_per_user") is None
    assert live().int_value("max_drafts_per_user") == 20
    (reverted,) = _events(db, "settings.reverted")
    assert reverted.payload["reverted_event_id"] == entry["id"]
    assert (reverted.payload["old"], reverted.payload["new"]) == (5, 20)
    assert reverted.payload["reason"] == "Back to normal"
    assert "reverted" in announcements[-1] and "Drafts per person: 5 -> 20" in announcements[-1]
    top = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    assert top["kind"] == "reverted" and top["reverted_event_id"] == entry["id"]


def test_reverting_a_later_change_restores_the_previous_override(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    _put(client, h, "max_drafts_per_user", 5)
    _put(client, h, "max_drafts_per_user", 3)
    latest = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    r = _revert(client, h, latest["id"])
    assert r.status_code == 200 and r.json()["value"] == 5 and r.json()["overridden"] is True
    assert live().int_value("max_drafts_per_user") == 5


def test_a_revert_cannot_restore_a_value_the_ceiling_now_forbids(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _admin(client, db)
    _put(client, h, "max_drafts_per_user", 15)
    _put(client, h, "max_drafts_per_user", 3)
    latest = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    monkeypatch.setattr(get_settings(), "max_drafts_per_user", 10)  # the ceiling came down since
    r = _revert(client, h, latest["id"])
    assert r.status_code == 422 and r.json()["error"]["details"]["bound"] == "maximum"
    kept = db.get(PlatformSetting, "max_drafts_per_user")
    assert kept is not None and kept.value == 3


def test_revert_needs_the_password_and_a_real_settings_entry(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    _put(client, h, "max_drafts_per_user", 5)
    entry = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    r = _revert(client, h, entry["id"], password="wrong-wrong-1")
    assert r.status_code == 403 and db.get(PlatformSetting, "max_drafts_per_user") is not None
    assert _events(db, "settings.reverted") == []
    assert _revert(client, h, str(uuid.uuid4())).status_code == 404
    other = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "user.created"))
    if other is None:
        # An admin sign-in is not audited as another type here; make one of an unrelated type.
        db.add(AuditEvent(application_id=None, actor_id=None, event_type="user.created", payload={}))
        db.commit()
        other = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "user.created"))
    assert other is not None
    assert _revert(client, h, str(other.id)).status_code == 404
    assert _revert(client, h, "not-a-uuid").status_code == 404


def test_reverting_to_the_value_already_in_force_is_refused(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    _put(client, h, "max_drafts_per_user", 5)
    entry = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]
    assert _revert(client, h, entry["id"]).status_code == 200
    r = _revert(client, h, entry["id"])  # already back at the default
    assert r.status_code == 422 and r.json()["error"]["details"]["reason"] == "no_change"


# ---- every consumer reads the live value ----


@pytest.fixture
def small_ceilings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    s = get_settings()
    monkeypatch.setattr(s, "rate_limit_per_minute", 12)
    monkeypatch.setattr(s, "login_attempts_per_minute", 6)
    yield


def test_the_request_limiter_reads_the_live_value(
    client: TestClient, db: Session, small_ceilings: None
) -> None:
    h = _admin(client, db)
    # Empty table: the environment value (12) is the limit, exactly as before the story.
    _install_limiter(client, build_request_limiter(enabled=True))
    codes = [client.get(f"{API}/form-schema").status_code for _ in range(13)]
    assert codes[:12] == [401] * 12 and codes[12] == 429
    _installed_limiter(client).clear()
    _install_limiter(client, build_request_limiter(enabled=False))
    assert _put(client, h, "rate_limit_per_minute", 10).status_code == 200
    _install_limiter(client, build_request_limiter(enabled=True))
    codes = [client.get(f"{API}/form-schema").status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


def test_one_limiter_instance_follows_a_change_without_being_rebuilt(
    client: TestClient, db: Session, small_ceilings: None
) -> None:
    h = _admin(client, db)
    _install_limiter(client, build_request_limiter(enabled=False))
    limiter = build_request_limiter(enabled=True)
    assert limiter.general.limit == 12 and limiter.login.limit == 6
    assert _put(client, h, "rate_limit_per_minute", 11).status_code == 200
    assert _put(client, h, "login_attempts_per_minute", 3).status_code == 200
    assert limiter.general.limit == 11 and limiter.login.limit == 3


def test_the_sign_in_limiter_reads_the_live_value(
    client: TestClient, db: Session, small_ceilings: None
) -> None:
    h = _admin(client, db)
    assert _put(client, h, "login_attempts_per_minute", 3).status_code == 200
    _install_limiter(client, build_request_limiter(enabled=True))
    bad = {"email": "nobody@example.sg", "password": "wrong-wrong-1"}
    codes = [client.post(f"{API}/auth/login", json=bad).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_the_draft_quota_reads_the_live_value(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    draft(client, op)
    draft(client, op)  # empty table: the environment allows 20
    assert _put(client, h, "max_drafts_per_user", 2).status_code == 200
    r = client.post(f"{API}/applications", headers=op)
    assert r.status_code == 409 and r.json()["error"]["details"] == {"code": "draft_limit", "limit": 2}


def test_the_per_person_ai_quota_reads_the_live_value(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    assert upload(client, op, app_id, "business_profile", "a.pdf", PDF).status_code == 201
    assert _put(client, h, "ai_runs_per_user_per_day", 1).status_code == 200
    second = upload(client, op, app_id, "floor_plan", "b.pdf", PDF).json()
    assert second["document"]["verification"]["status"] == "unavailable"
    assert second["document"]["verification"]["error_reason"] == "daily_limit_reached"


def test_the_platform_ai_quota_reads_the_live_value_and_the_overview_shows_it(
    client: TestClient, db: Session
) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    assert upload(client, op, app_id, "business_profile", "a.pdf", PDF).status_code == 201
    assert _put(client, h, "ai_runs_per_day", 1).status_code == 200
    second = upload(client, op, app_id, "floor_plan", "b.pdf", PDF).json()
    assert second["document"]["verification"]["error_reason"] == "daily_limit_reached"
    assert client.get(f"{API}/admin/overview", headers=h).json()["today"]["runs_per_day_quota"] == 1


def test_the_upload_gate_and_the_body_limit_read_the_live_size(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    big = PDF + b"0" * int(1.5 * 1024 * 1024)
    assert upload(client, op, app_id, "business_profile", "ok.pdf", big).status_code == 201  # 10 MB today
    assert _put(client, h, "upload_max_bytes", 1024 * 1024).status_code == 200
    r = upload(client, op, app_id, "floor_plan", "big.pdf", big)
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "too_large"
    assert "1 MB" in r.json()["error"]["message"]
    small = PDF + b"0" * 1000
    assert upload(client, op, app_id, "floor_plan", "small.pdf", small).status_code == 201


def test_the_ai_text_cap_reads_the_live_value(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    text = ("lorem ipsum " * 400).encode()  # 4,800 characters
    r = upload(client, op, app_id, "business_profile", "a.txt", text, "text/plain")
    assert r.status_code == 201
    stored = DocumentRepository(db).get_in_application(
        uuid.UUID(app_id), uuid.UUID(r.json()["document"]["id"])
    )
    assert stored is not None and stored.extracted_text is not None and len(stored.extracted_text) > 4000
    assert _put(client, h, "ai_max_text_chars", 1000).status_code == 200
    r = upload(client, op, app_id, "floor_plan", "b.txt", text, "text/plain")
    db.expire_all()
    stored = DocumentRepository(db).get_in_application(
        uuid.UUID(app_id), uuid.UUID(r.json()["document"]["id"])
    )
    assert stored is not None and stored.extracted_text is not None and len(stored.extracted_text) <= 1000


# ---- the AI pause switch ----


def _no_provider(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from app.services import verification

    calls: list[str] = []

    def spy() -> NoReturn:
        calls.append("provider")
        raise AssertionError("the provider must not be reached while the AI is paused")

    monkeypatch.setattr(verification, "get_provider", spy)
    return calls


def test_while_paused_a_new_check_is_stored_unavailable_and_never_reaches_the_provider(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    assert _put(client, h, "ai_paused", True, reason="Provider incident").status_code == 200
    calls = _no_provider(monkeypatch)
    r = upload(client, op, app_id, "business_profile", "a.pdf", PDF)
    assert r.status_code == 201
    v = r.json()["document"]["verification"]
    assert v["status"] == "unavailable" and v["error_reason"] == "ai_paused"
    assert calls == []
    # The application can still go on; the operator sees the reason code in the document view.
    view = client.get(f"{API}/applications/{app_id}", headers=op).json()
    assert view["completeness"]["documents_present"] == 1


def test_a_check_that_was_pending_when_the_ai_was_paused_is_stopped_before_the_provider(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.verification import run_verification

    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    first = upload(client, op, app_id, "business_profile", "a.txt", TXT, "text/plain")
    doc_id = first.json()["document"]["id"]
    run = VerificationRun(document_id=uuid.UUID(doc_id), status=VerificationStatus.PENDING, provider="none")
    db.add(run)
    db.commit()
    assert _put(client, h, "ai_paused", True).status_code == 200
    calls = _no_provider(monkeypatch)
    run_verification(run.id)
    db.expire_all()
    done = db.get(VerificationRun, run.id)
    assert done is not None
    assert done.status == VerificationStatus.UNAVAILABLE and done.error_reason == "ai_paused"
    assert calls == []


def test_paused_checks_do_not_count_toward_the_quotas_and_unpausing_resumes(
    client: TestClient, db: Session
) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    assert _put(client, h, "ai_runs_per_user_per_day", 1).status_code == 200
    assert _put(client, h, "ai_paused", True).status_code == 200
    for dtype in ("business_profile", "floor_plan"):
        v = upload(client, op, app_id, dtype, f"{dtype}.pdf", PDF).json()["document"]["verification"]
        assert v["error_reason"] == "ai_paused"
    assert _put(client, h, "ai_paused", False).status_code == 200
    v = upload(client, op, app_id, "tenancy_agreement", "t.pdf", PDF).json()["document"]["verification"]
    assert v["status"] != "unavailable"  # the paused ones used none of the one run allowed


def test_unpausing_reports_how_many_checks_the_pause_stopped(
    client: TestClient, db: Session, announcements: list[str]
) -> None:
    h = _admin(client, db)
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    assert _put(client, h, "ai_paused", True).status_code == 200
    for dtype in ("business_profile", "floor_plan"):
        upload(client, op, app_id, dtype, f"{dtype}.pdf", PDF)
    assert _put(client, h, "ai_paused", False).status_code == 200
    on, off = _events(db, "settings.changed")
    assert "ended_while_paused" not in on.payload and off.payload["ended_while_paused"] == 2
    assert "2 checks ended as ai_paused" in announcements[-1]
    feed = client.get(f"{API}/admin/audit-feed", headers=h).json()["events"]
    assert any("(2 checks ended as ai_paused while paused)" in e["summary"] for e in feed)
    # A pause with nothing stopped reports zero; checks before the pause are not counted.
    assert _put(client, h, "ai_paused", True).status_code == 200
    assert _put(client, h, "ai_paused", False).status_code == 200
    assert _events(db, "settings.changed")[-1].payload["ended_while_paused"] == 0


# ---- the cache ----


def test_a_change_made_elsewhere_is_picked_up_within_ten_seconds(db: Session) -> None:
    """Another process writes the row; this one sees it once the ten seconds are up (clock injected)."""
    from app.services.platform_settings import LiveSettings, reset_live, run_inline

    now = {"t": 5000.0}
    reader = reset_live(LiveSettings(clock=lambda: now["t"], spawn=run_inline))
    admin = make_user(db, "adm@example.sg", Role.ADMIN)
    assert reader.int_value("max_drafts_per_user") == 20
    db.add(PlatformSetting(key="max_drafts_per_user", value=4, updated_by=admin.id, reason="from afar"))
    db.commit()
    now["t"] += 9.9
    assert reader.int_value("max_drafts_per_user") == 20
    now["t"] += 0.2
    assert reader.int_value("max_drafts_per_user") == 4


def test_the_reload_runs_on_its_own_connection_with_short_timeouts(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The background reload is bounded (1 s statement, 3 s connect) without touching the application
    engine's defaults, and it reads the same rows the API wrote."""
    from app.repositories.platform_settings import PlatformSettingsRepository
    from app.services import platform_settings as service

    seen: dict[str, str] = {}
    original = PlatformSettingsRepository.all

    def spy(self: PlatformSettingsRepository) -> list[PlatformSetting]:
        seen["statement_timeout"] = str(self.db.execute(text("SHOW statement_timeout")).scalar_one())
        return original(self)

    monkeypatch.setattr(PlatformSettingsRepository, "all", spy)
    admin = make_user(db, "adm@example.sg", Role.ADMIN)
    db.add(PlatformSetting(key="max_drafts_per_user", value=4, updated_by=admin.id, reason="r"))
    db.commit()
    assert service._load_rows() == {"max_drafts_per_user": 4}
    assert seen["statement_timeout"] == "1s"
    # The application's own sessions keep the server default.
    assert db.execute(text("SHOW statement_timeout")).scalar_one() == "0"


def test_the_background_pool_is_separate_and_connects_with_a_timeout() -> None:
    from sqlalchemy.engine import Engine
    from sqlalchemy.pool import QueuePool

    from app.infra import db as dbmod

    session = dbmod.background_session()
    try:
        bind = session.get_bind()
        assert isinstance(bind, Engine) and bind is not dbmod.get_engine()
        assert isinstance(bind.pool, QueuePool) and bind.pool.timeout() == 3
        raw = session.connection().connection.driver_connection
        assert raw is not None and "connect_timeout=3" in raw.info.dsn
    finally:
        session.close()
