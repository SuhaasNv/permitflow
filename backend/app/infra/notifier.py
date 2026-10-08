"""Operator announcements to the monitoring Telegram chat (US-101).

The monitoring bot (`docker/observability/telegram-bot`) only reads; this is the API's one outbound
message, used when an administrator changes a platform setting. It is plain text (no parse mode, so a
reason typed by a person cannot inject markup), sent from a short-lived thread so a slow Telegram never
holds a request, and it never raises: an announcement is not worth failing a change that is already
committed. Without `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` it does nothing and opens no connection.
"""

import json
import logging
import threading
import urllib.request

from app.core.settings import get_settings

logger = logging.getLogger("permitflow.notifier")

_TIMEOUT_SECONDS = 5
_MAX_LENGTH = 3500  # Telegram refuses more than 4096; leave room


def configured() -> bool:
    s = get_settings()
    return bool(s.telegram_bot_token and s.telegram_chat_id)


def notify(text: str) -> None:
    """Send `text` to the chat, in the background. A no-op when Telegram is not configured."""
    if not configured():
        return
    threading.Thread(target=_send, args=(text[:_MAX_LENGTH],), name="telegram-notify", daemon=True).start()


def _send(text: str) -> None:
    s = get_settings()
    body = json.dumps({"chat_id": s.telegram_chat_id, "text": text, "disable_web_page_preview": True})
    request = urllib.request.Request(  # noqa: S310 - a fixed https URL
        f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
        data=body.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS):  # noqa: S310
            pass
    except Exception as exc:  # noqa: BLE001 - never let an announcement fail a change
        # The URL carries the bot token; log the exception type only.
        logger.warning("telegram_notify_failed", extra={"extra_fields": {"error": type(exc).__name__}})
