"""US-101, the cache every limit reads: ten seconds, an injected clock, the environment as the fallback."""

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import pytest

from app.core.settings import get_settings
from app.domain.platform_settings import SPECS
from app.services.platform_settings import TTL_SECONDS, LiveSettings, run_inline


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
    live = LiveSettings(spawn=run_inline, loader=Loader({}))
    s = get_settings()
    for spec in SPECS:
        if spec.env_field is not None:
            assert live.value(spec.key) == getattr(s, spec.env_field), spec.key
    assert live.bool_value("ai_paused") is False
    assert live.value("scanner_fail_mode") == "closed"


def test_a_row_overrides_and_is_read_from_memory_for_ten_seconds() -> None:
    clock, loader = Clock(), Loader({"max_drafts_per_user": 3})
    live = LiveSettings(clock=clock, spawn=run_inline, loader=loader)
    assert live.int_value("max_drafts_per_user") == 3
    loader.rows["max_drafts_per_user"] = 2  # changed by someone else (another process)
    clock.now += TTL_SECONDS - 0.1
    assert live.int_value("max_drafts_per_user") == 3 and loader.calls == 1
    clock.now += 0.1
    assert live.int_value("max_drafts_per_user") == 2 and loader.calls == 2


def test_removing_a_row_returns_to_the_environment_within_ten_seconds() -> None:
    clock, loader = Clock(), Loader({"max_drafts_per_user": 1})
    live = LiveSettings(clock=clock, spawn=run_inline, loader=loader)
    assert live.int_value("max_drafts_per_user") == 1
    loader.rows.clear()
    clock.now += TTL_SECONDS
    assert live.int_value("max_drafts_per_user") == get_settings().max_drafts_per_user


def test_invalidate_makes_the_next_read_reload() -> None:
    loader = Loader({"max_drafts_per_user": 3})
    live = LiveSettings(clock=Clock(), spawn=run_inline, loader=loader)
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
    live = LiveSettings(clock=clock, spawn=run_inline, loader=broken)
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

    live = LiveSettings(clock=clock, spawn=run_inline, loader=flaky)
    assert live.int_value("max_drafts_per_user") == 2
    state["ok"] = False
    clock.now += TTL_SECONDS
    assert live.int_value("max_drafts_per_user") == 2


def test_a_row_above_the_environment_ceiling_never_loosens_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 100)
    live = LiveSettings(spawn=run_inline, loader=Loader({"rate_limit_per_minute": 5000}))
    assert live.int_value("rate_limit_per_minute") == 100


class Threads:
    """A spawner that keeps the reload threads, so a test can wait for them."""

    def __init__(self) -> None:
        self.started: list[threading.Thread] = []

    def __call__(self, job: Callable[[], None]) -> None:
        t = threading.Thread(target=job, daemon=True)
        self.started.append(t)
        t.start()

    def join(self) -> None:
        for t in self.started:
            t.join(5)
            assert not t.is_alive()


class SlowLoader:
    """Blocks inside the first call until released, like a database that does not answer."""

    def __init__(self, rows: dict[str, Any]) -> None:
        self.rows = rows
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def __call__(self) -> dict[str, Any]:
        self.calls += 1
        read = dict(self.rows)  # what the table said when the query ran
        if self.calls == 1:
            self.entered.set()
            self.release.wait(5)
        return read


def test_a_slow_reload_does_not_block_other_readers() -> None:
    """Once a snapshot exists, one thread reloads and the rest keep serving the old one."""
    clock = Clock()
    state: dict[str, Any] = {"slow": False}
    started, release = threading.Event(), threading.Event()

    def loader() -> dict[str, Any]:
        if state["slow"]:
            started.set()
            release.wait(5)
            return {"max_drafts_per_user": 9}
        return {"max_drafts_per_user": 2}

    threads = Threads()
    live = LiveSettings(clock=clock, loader=loader, spawn=threads)
    live.int_value("max_drafts_per_user")  # starts the first (fast) load
    threads.join()
    assert live.int_value("max_drafts_per_user") == 2
    state["slow"] = True
    clock.now += TTL_SECONDS
    assert live.int_value("max_drafts_per_user") == 2  # due: serves the old one, reload runs behind
    assert started.wait(5)
    assert live.int_value("max_drafts_per_user") == 2  # still not blocked, still the old snapshot
    assert len(threads.started) == 2  # one reload in flight, not one per reader
    release.set()
    threads.join()
    assert live.int_value("max_drafts_per_user") == 9


def test_the_first_read_serves_the_environment_and_never_waits_for_the_database() -> None:
    loader = SlowLoader({"max_drafts_per_user": 3})
    threads = Threads()
    live = LiveSettings(loader=loader, spawn=threads)
    t0 = time.monotonic()
    assert live.int_value("max_drafts_per_user") == get_settings().max_drafts_per_user
    assert time.monotonic() - t0 < 1.0
    assert loader.entered.wait(5)
    assert live.int_value("max_drafts_per_user") == get_settings().max_drafts_per_user  # still loading
    loader.release.set()
    threads.join()
    assert live.int_value("max_drafts_per_user") == 3  # the snapshot updates once the reload completes
    assert loader.calls == 1


def test_a_blocked_reload_does_not_stall_the_event_loop() -> None:
    """The middlewares call this from `async def`: a database that hangs must not freeze the loop."""
    loader = SlowLoader({"rate_limit_per_minute": 10})
    threads = Threads()
    live = LiveSettings(loader=loader, spawn=threads)

    async def scenario() -> tuple[int, int]:
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        task = asyncio.create_task(ticker())
        await asyncio.sleep(0)
        t0 = time.monotonic()
        value = live.int_value("rate_limit_per_minute")  # what the middleware does, on the loop thread
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        await asyncio.sleep(0.1)  # the loader is still blocked; the loop keeps turning
        task.cancel()
        assert value == get_settings().rate_limit_per_minute
        assert loader.entered.is_set() and not loader.release.is_set()
        assert ticks >= 3
        return elapsed_ms, ticks

    elapsed_ms, _ = asyncio.run(scenario())
    assert elapsed_ms < 500
    loader.release.set()
    threads.join()
    assert live.int_value("rate_limit_per_minute") == min(10, get_settings().rate_limit_per_minute)


def test_a_failing_background_reload_keeps_serving_and_is_not_retried_every_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = Clock()
    state: dict[str, Any] = {"ok": True, "calls": 0}

    def flaky() -> dict[str, Any]:
        state["calls"] += 1
        if state["ok"]:
            return {"max_drafts_per_user": 2}
        raise RuntimeError("database is down")

    threads = Threads()
    live = LiveSettings(clock=clock, loader=flaky, spawn=threads)
    live.int_value("max_drafts_per_user")
    threads.join()
    state["ok"] = False
    clock.now += TTL_SECONDS
    with caplog.at_level(logging.WARNING, logger="permitflow.settings"):
        for _ in range(5):
            assert live.int_value("max_drafts_per_user") == 2
            threads.join()
    assert state["calls"] == 2  # one failed attempt, then quiet until the next ttl
    assert "platform_settings_unreadable" in caplog.text


def test_a_reload_that_started_before_a_change_cannot_store_its_older_rows() -> None:
    """The race: a reload reads the table, an administrator changes a setting (invalidate), the reload then
    stores what it read as fresh. The generation counter makes it drop them."""
    loader = SlowLoader({"max_drafts_per_user": 2})  # what the table said before the change
    threads = Threads()
    live = LiveSettings(loader=loader, spawn=threads)
    live.int_value("max_drafts_per_user")
    assert loader.entered.wait(5)
    # The change commits and this process is told, while the older reload is still in flight.
    loader.rows = {"max_drafts_per_user": 7}
    live.invalidate()
    loader.release.set()
    threads.join()
    # The older rows were dropped: the snapshot is not marked fresh, so the next read reloads again and
    # the value that ends up in force is the new one, never the 2 the older reload read.
    assert loader.calls == 1
    live.int_value("max_drafts_per_user")
    threads.join()
    assert loader.calls == 2
    assert live.int_value("max_drafts_per_user") == 7


def test_a_reload_in_flight_cannot_overwrite_the_refresh_that_followed_a_change() -> None:
    """The write path: invalidate, then refresh on the writer's thread. A background reload that began
    earlier and finishes afterwards must not put its older rows back over the refreshed ones."""
    loader = SlowLoader({"max_drafts_per_user": 2})
    threads = Threads()
    live = LiveSettings(loader=loader, spawn=threads)
    live.int_value("max_drafts_per_user")
    assert loader.entered.wait(5)  # the older reload is in flight, holding the 2
    loader.rows = {"max_drafts_per_user": 7}
    live.invalidate()
    live.refresh()  # the writer's thread: loads the 7 at once
    assert live.int_value("max_drafts_per_user") == 7
    loader.release.set()
    threads.join()  # the older reload now finishes with its 2
    assert live.int_value("max_drafts_per_user") == 7
    assert loader.calls == 2  # and nothing was marked stale to fetch again


def test_refresh_after_invalidate_serves_the_new_value_at_once() -> None:
    loader = Loader({"max_drafts_per_user": 3})
    live = LiveSettings(spawn=run_inline, loader=loader)
    assert live.int_value("max_drafts_per_user") == 3
    loader.rows["max_drafts_per_user"] = 4
    live.invalidate()
    live.refresh()
    assert live.int_value("max_drafts_per_user") == 4 and loader.calls == 2


def test_a_refresh_that_fails_does_not_raise_and_keeps_the_previous_snapshot() -> None:
    state: dict[str, Any] = {"ok": True}

    def flaky() -> dict[str, Any]:
        if state["ok"]:
            return {"max_drafts_per_user": 2}
        raise RuntimeError("down")

    live = LiveSettings(spawn=run_inline, loader=flaky)
    assert live.int_value("max_drafts_per_user") == 2
    state["ok"] = False
    live.invalidate()
    live.refresh()
    assert live.int_value("max_drafts_per_user") == 2
