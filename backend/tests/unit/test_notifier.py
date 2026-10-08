"""US-101, the Telegram announcement: silent without configuration, never raises, never leaks the token."""

import logging
import threading
import urllib.request
from typing import Any

import pytest

from app.core.settings import get_settings
from app.infra import notifier


def _join_senders() -> None:
    for t in threading.enumerate():
        if t.name == "telegram-notify":
            t.join(5)


def test_without_a_token_and_chat_nothing_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: Any, **k: Any) -> None:
        raise AssertionError("no connection may be opened")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert notifier.configured() is False
    notifier.notify("hello")
    _join_senders()


def test_with_both_set_it_posts_plain_text_to_the_bot_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "123:abc")
    monkeypatch.setattr(get_settings(), "telegram_chat_id", "-42")
    seen: list[urllib.request.Request] = []

    class Resp:
        def __enter__(self) -> "Resp":
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_urlopen(req: urllib.request.Request, timeout: float) -> Resp:
        seen.append(req)
        return Resp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    notifier.notify("Setting changed <b>x</b>")
    _join_senders()
    assert len(seen) == 1
    assert seen[0].full_url == "https://api.telegram.org/bot123:abc/sendMessage"
    body = seen[0].data
    assert isinstance(body, bytes)
    assert b'"chat_id": "-42"' in body and b"parse_mode" not in body  # plain text: no markup injection


def test_a_failing_send_is_swallowed_and_the_token_is_not_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "123:secret-token")
    monkeypatch.setattr(get_settings(), "telegram_chat_id", "-42")

    def broken(*a: Any, **k: Any) -> None:
        raise OSError("https://api.telegram.org/bot123:secret-token/sendMessage unreachable")

    monkeypatch.setattr(urllib.request, "urlopen", broken)
    with caplog.at_level(logging.WARNING, logger="permitflow.notifier"):
        notifier.notify("x")
        _join_senders()
    assert "telegram_notify_failed" in caplog.text
    assert "secret-token" not in caplog.text


def test_a_long_message_is_cut_below_the_telegram_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "t")
    monkeypatch.setattr(get_settings(), "telegram_chat_id", "c")
    sent: list[str] = []
    monkeypatch.setattr(notifier, "_send", sent.append)
    notifier.notify("y" * 10_000)
    _join_senders()
    assert len(sent) == 1 and len(sent[0]) <= 3500
