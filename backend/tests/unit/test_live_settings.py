"""US-101, the cache every limit reads: ten seconds, an injected clock, the environment as the fallback."""

import logging
import threading
from typing import Any

import pytest

from app.core.settings import get_settings
from app.domain.platform_settings import SPECS
from app.services.platform_settings import TTL_SECONDS, LiveSettings


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Loader:
    def __init__(self, rows: dict[str, Any]) -> None:
        self.rows = rows
        self.calls = 0

    def __call__(self) -> dict[str, Any]:
        self.calls += 1
        return dict(self.rows)


def test_an_empty_table_is_the_environment_for_every_setting() -> None:
    live = LiveSettings(loader=Loader({}))
    s = get_settings()
    for spec in SPECS:
        if spec.env_field is not None:
            assert live.value(spec.key) == getattr(s, spec.env_field), spec.key
    assert live.bool_value("ai_paused") is False
    assert live.value("scanner_fail_mode") == "closed"


def test_a_row_overrides_and_is_read_from_memory_for_ten_seconds() -> None:
    clock, loader = Clock(), Loader({"max_drafts_per_user": 3})
    live = LiveSettings(clock=clock, loader=loader)
    assert live.int_value("max_drafts_per_user") == 3
    loader.rows["max_drafts_per_user"] = 2  # changed by someone else (another process)
    clock.now += TTL_SECONDS - 0.1
    assert live.int_value("max_drafts_per_user") == 3 and loader.calls == 1
    clock.now += 0.1
    assert live.int_value("max_drafts_per_user") == 2 and loader.calls == 2


def test_removing_a_row_returns_to_the_environment_within_ten_seconds() -> None:
    clock, loader = Clock(), Loader({"max_drafts_per_user": 1})
    live = LiveSettings(clock=clock, loader=loader)
    assert live.int_value("max_drafts_per_user") == 1
    loader.rows.clear()
    clock.now += TTL_SECONDS
    assert live.int_value("max_drafts_per_user") == get_settings().max_drafts_per_user


def test_invalidate_makes_the_next_read_reload() -> None:
    loader = Loader({"max_drafts_per_user": 3})
    live = LiveSettings(clock=Clock(), loader=loader)
    live.int_value("max_drafts_per_user")
    loader.rows["max_drafts_per_user"] = 4
    live.invalidate()
    assert live.int_value("max_drafts_per_user") == 4


def test_an_unreadable_table_falls_back_to_the_environment_and_does_not_retry_every_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0

    def broken() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise RuntimeError("database is down")

    clock = Clock()
    live = LiveSettings(clock=clock, loader=broken)
    with caplog.at_level(logging.WARNING, logger="permitflow.settings"):
        for _ in range(5):
            assert live.int_value("max_drafts_per_user") == get_settings().max_drafts_per_user
    assert calls == 1
    assert "platform_settings_unreadable" in caplog.text
    clock.now += TTL_SECONDS
    live.int_value("max_drafts_per_user")
    assert calls == 2


def test_a_failed_reload_keeps_the_last_good_snapshot() -> None:
    clock = Clock()
    state: dict[str, Any] = {"ok": True}

    def flaky() -> dict[str, Any]:
        if state["ok"]:
            return {"max_drafts_per_user": 2}
        raise RuntimeError("down")

    live = LiveSettings(clock=clock, loader=flaky)
    assert live.int_value("max_drafts_per_user") == 2
    state["ok"] = False
    clock.now += TTL_SECONDS
    assert live.int_value("max_drafts_per_user") == 2


def test_a_row_above_the_environment_ceiling_never_loosens_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 100)
    live = LiveSettings(loader=Loader({"rate_limit_per_minute": 5000}))
    assert live.int_value("rate_limit_per_minute") == 100


def test_a_slow_reload_does_not_block_other_readers() -> None:
    """Once a snapshot exists, one thread reloads and the rest keep serving the old one."""
    clock = Clock()
    started, release = threading.Event(), threading.Event()
    state: dict[str, Any] = {"slow": False}

    def loader() -> dict[str, Any]:
        if state["slow"]:
            started.set()
            release.wait(5)
            return {"max_drafts_per_user": 9}
        return {"max_drafts_per_user": 2}

    live = LiveSettings(clock=clock, loader=loader)
    assert live.int_value("max_drafts_per_user") == 2
    state["slow"] = True
    clock.now += TTL_SECONDS
    seen: list[int] = []
    t = threading.Thread(target=lambda: seen.append(live.int_value("max_drafts_per_user")))
    t.start()
    assert started.wait(5)
    assert live.int_value("max_drafts_per_user") == 2  # not blocked, previous snapshot
    release.set()
    t.join(5)
    assert seen == [9]
