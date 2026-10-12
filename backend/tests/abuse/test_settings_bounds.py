"""Abuse case 8 (US-105; THREAT_MODEL T31 a stolen administrator session tuning the limits, US-101): the
platform settings panel can lower a limit but never remove it or raise it past the environment's ceiling; the
change needs the administrator's own password; and only an administrator may try.

The sweeps run over `SPECS`, so a setting added later is attacked without anyone remembering to add it.
Already asserted elsewhere and not repeated: the exact bound named in the 422 for eleven chosen values, the
403 for a wrong password with its audit row, the order (password before bounds), the sign-in limiter on
repeated wrong passwords, a row written around the API being clamped at read time, and a revert that
the ceiling now forbids (tests/integration/test_platform_settings.py).
"""

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.domain.platform_settings import SPECS, SettingSpec, bounds_for
from app.models import AuditEvent, PlatformSetting
from app.models.enums import Role
from tests.factories import DEFAULT_PASSWORD, login, make_user

SETTINGS = "/api/v1/admin/settings"
REASON = "Load from the open day"
INT_SPECS = [s for s in SPECS if s.kind == "int"]
OTHER_SPECS = [s for s in SPECS if s.kind != "int"]


def _admin(client: TestClient, db: Session) -> dict[str, str]:
    make_user(db, "adm@example.sg", Role.ADMIN, protected=True)
    return login(client, "adm@example.sg")


def _put(client: TestClient, h: dict[str, str], key: str, body: dict[str, object]):  # type: ignore[no-untyped-def]
    # Raw JSON, so values a Python client would refuse to encode (NaN, Infinity) can be sent too.
    return client.put(
        f"{SETTINGS}/{key}",
        headers={**h, "Content-Type": "application/json"},
        content=json.dumps(body).encode(),
    )


def _full(value: object, password: str = DEFAULT_PASSWORD) -> dict[str, object]:
    return {"value": value, "reason": REASON, "password": password}


def _nothing_changed(db: Session) -> None:
    db.expire_all()
    assert db.scalar(select(PlatformSetting)) is None, "a setting row was written"
    changed = select(AuditEvent).where(AuditEvent.event_type.in_(("settings.changed", "settings.reverted")))
    assert db.scalar(changed) is None, "a settings change was audited as made"


def _bounds(spec: SettingSpec) -> tuple[int, int]:
    assert spec.env_field is not None
    b = bounds_for(spec, getattr(get_settings(), spec.env_field))
    assert b.minimum is not None and b.maximum is not None
    return b.minimum, b.maximum


def test_no_number_outside_the_bounds_is_accepted_on_any_setting(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    failures = []
    for spec in INT_SPECS:
        low, high = _bounds(spec)
        outside = {low - 1, 0, -1, -(2**31), high + 1, high * 2, 2**31, 2**63, 2**64} - set(
            range(low, high + 1)
        )
        for value in sorted(outside):
            r = _put(client, h, spec.key, _full(value))
            if r.status_code != 422 or r.json()["error"]["code"] != "validation_failed":
                failures.append(f"{spec.key}={value}: {r.status_code}")
    assert not failures, "\n".join(failures)
    _nothing_changed(db)


def test_the_absolute_cap_holds_when_the_environment_asks_for_more(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An environment value of a billion, or of zero (no limit), still leaves each setting its own cap."""
    h = _admin(client, db)
    failures = []
    for spec in INT_SPECS:
        assert spec.env_field is not None
        for env_value in (10**9, 0):
            monkeypatch.setattr(get_settings(), spec.env_field, env_value)
            r = _put(client, h, spec.key, _full(spec.absolute_max + 1))
            if r.status_code != 422:
                failures.append(f"{spec.key} with the environment at {env_value}: {r.status_code}")
    assert not failures, "\n".join(failures)
    _nothing_changed(db)


NOT_WHOLE_NUMBERS: list[object] = [
    "5",
    "5.0",
    "1e9",
    "0x10",
    "NaN",
    5.5,
    1e999,
    float("nan"),
    True,
    False,
    None,
    [5],
    {"n": 5},
]


def test_a_number_setting_takes_only_a_whole_number(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    failures = []
    for spec in INT_SPECS:
        for value in NOT_WHOLE_NUMBERS:
            r = _put(client, h, spec.key, _full(value))
            if r.status_code != 422:
                failures.append(f"{spec.key}={value!r}: {r.status_code}")
    assert not failures, "\n".join(failures)
    _nothing_changed(db)


def test_switches_and_choices_take_only_their_own_values(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    wrong: list[object] = ["true", "false", "yes", 1, 0, 2, "", "RETRY", "off", "hold ", ["retry"], None, {}]
    failures = []
    for spec in OTHER_SPECS:
        for value in wrong:
            r = _put(client, h, spec.key, _full(value))
            if r.status_code != 422:
                failures.append(f"{spec.key}={value!r}: {r.status_code}")
    assert not failures, "\n".join(failures)
    _nothing_changed(db)


@pytest.mark.parametrize(
    "key", ["../admin/users", "..%2F", "max_drafts_per_user ", "MAX_DRAFTS_PER_USER", "x" * 300, "%00"]
)
def test_an_unknown_key_writes_nothing(client: TestClient, db: Session, key: str) -> None:
    h = _admin(client, db)
    r = _put(client, h, key, _full(5))
    assert r.status_code in (404, 405), r.status_code  # a path the router does not own is no setting either
    _nothing_changed(db)


# ---- the step-up password ----


def test_a_valid_change_without_the_password_is_refused_on_every_setting(
    client: TestClient, db: Session
) -> None:
    h = _admin(client, db)
    failures = []
    for spec in INT_SPECS:
        low, high = _bounds(spec)
        value = low if low != getattr(get_settings(), spec.env_field or "") else high - 1
        base: dict[str, object] = {"value": value, "reason": REASON}
        attempts = {
            "no password": base,
            "empty password": {**base, "password": ""},
            "wrong password": {**base, "password": "Not-The-Password-1"},
            "the right password plus a space": {**base, "password": DEFAULT_PASSWORD + " "},
            "the right password in the reason": {"value": value, "reason": DEFAULT_PASSWORD},
            "a null password": {**base, "password": None},
        }
        for label, body in attempts.items():
            r = _put(client, h, spec.key, body)
            if r.status_code not in (403, 422):
                failures.append(f"{spec.key}, {label}: {r.status_code}")
    assert not failures, "\n".join(failures)
    _nothing_changed(db)


def test_the_revert_route_needs_the_password_too(client: TestClient, db: Session) -> None:
    h = _admin(client, db)
    assert _put(client, h, "max_drafts_per_user", _full(5)).status_code == 200
    entry = client.get(f"{SETTINGS}/history", headers=h).json()["entries"][0]["id"]
    url = f"{SETTINGS}/history/{entry}/revert"
    assert (
        client.post(url, headers=h, json={"reason": REASON, "password": "Not-The-Password-1"}).status_code
        == 403
    )
    assert client.post(url, headers=h, json={"reason": REASON, "password": ""}).status_code == 422
    assert client.post(url, headers=h, json={"reason": REASON}).status_code == 422
    db.expire_all()
    row = db.scalar(select(PlatformSetting).where(PlatformSetting.key == "max_drafts_per_user"))
    assert row is not None and row.value == 5  # still the changed value
    assert db.scalar(select(AuditEvent).where(AuditEvent.event_type == "settings.reverted")) is None


# ---- who may try ----


@pytest.mark.parametrize("role", [Role.OPERATOR, Role.OFFICER])
def test_only_an_administrator_may_change_a_setting_even_with_everything_else_right(
    client: TestClient, db: Session, role: Role
) -> None:
    """The right password, an in-bounds value and a reason: the role alone decides."""
    make_user(db, "someone@example.sg", role)
    h = login(client, "someone@example.sg")
    for spec in INT_SPECS:
        low, _ = _bounds(spec)
        r = _put(client, h, spec.key, _full(low))
        assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden", spec.key
    assert _put(client, h, "ai_paused", _full(True)).status_code == 403
    assert client.get(SETTINGS, headers=h).status_code == 403
    assert client.get(f"{SETTINGS}/history", headers=h).status_code == 403
    revert = {"reason": REASON, "password": DEFAULT_PASSWORD}
    assert client.post(f"{SETTINGS}/history/{uuid.uuid4()}/revert", headers=h, json=revert).status_code == 403
    _nothing_changed(db)


def test_anonymous_callers_get_401_on_every_setting(client: TestClient, db: Session) -> None:
    for spec in SPECS:
        assert _put(client, {}, spec.key, _full(1)).status_code == 401, spec.key
    _nothing_changed(db)
