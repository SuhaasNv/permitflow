"""Operating hours (US-108): one set of times shared by every open day.

The stored value is `{"days": ["mon", ...], "opens": "HH:MM" | None, "closes": "HH:MM" | None,
"open_24h": bool}`. Submitted revisions made before v0.4.1 hold a free-text string instead; those are
immutable snapshots, shown as written (`summarise_hours` returns them unchanged) and never rewritten.
The TypeScript mirror is `frontend/src/lib/hours.ts`.
"""

import re
from typing import Any

DAYS: tuple[tuple[str, str], ...] = (
    ("mon", "Mon"),
    ("tue", "Tue"),
    ("wed", "Wed"),
    ("thu", "Thu"),
    ("fri", "Fri"),
    ("sat", "Sat"),
    ("sun", "Sun"),
)
DAY_KEYS: tuple[str, ...] = tuple(k for k, _ in DAYS)
_DAY_LABEL = dict(DAYS)
STEP_MINUTES = 30
_HOURS_KEYS = frozenset({"days", "opens", "closes", "open_24h"})
_TIME = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")

LEGACY_MESSAGE = "Pick your opening days and hours."
NO_DAYS_MESSAGE = "Choose at least one day you open."
NO_TIMES_MESSAGE = "Choose an opening and a closing time."
BAD_TIME_MESSAGE = "Choose a time on the half hour, from 00:00 to 23:30."
SAME_TIME_MESSAGE = "Opening and closing time cannot be the same."


def time_options(step_minutes: int = STEP_MINUTES) -> list[str]:
    return [f"{m // 60:02d}:{m % 60:02d}" for m in range(0, 24 * 60, step_minutes)]


def _is_slot(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    m = _TIME.fullmatch(value)
    return m is not None and int(m.group(2)) % STEP_MINUTES == 0


def normalise_hours(value: dict[str, Any]) -> dict[str, Any]:
    """Days de-duplicated in week order, blank times as None, times dropped when open 24 hours."""
    days = value.get("days")
    if isinstance(days, list) and all(d in DAY_KEYS for d in days):
        days = [d for d in DAY_KEYS if d in days]
    out: dict[str, Any] = {**value, "days": days}
    for key in ("opens", "closes"):
        v = out.get(key)
        out[key] = None if v is None or (isinstance(v, str) and v.strip() == "") else v
    out.setdefault("open_24h", False)
    if out["open_24h"] is True:
        out["opens"] = None
        out["closes"] = None
    return out


def validate_hours(value: Any, *, snapshot: bool = False) -> str | None:
    """Return the error message for an operating-hours value, or None. `value` is normalised first.

    A free-text string is the pre-v0.4.1 shape: fine when reading a submitted snapshot, an error when an
    operator edits (they re-pick once).
    """
    if isinstance(value, str):
        return None if snapshot else LEGACY_MESSAGE
    if not isinstance(value, dict) or not set(value) <= _HOURS_KEYS:
        return LEGACY_MESSAGE
    days = value.get("days")
    if not isinstance(days, list) or not all(d in DAY_KEYS for d in days):
        return LEGACY_MESSAGE
    open_24h = value.get("open_24h")
    if not isinstance(open_24h, bool):
        return LEGACY_MESSAGE
    if not days:
        return NO_DAYS_MESSAGE
    if open_24h:
        return None
    opens, closes = value.get("opens"), value.get("closes")
    if opens is None or closes is None:
        return NO_TIMES_MESSAGE
    if not _is_slot(opens) or not _is_slot(closes):
        return BAD_TIME_MESSAGE
    if opens == closes:
        return SAME_TIME_MESSAGE
    return None


def _day_phrase(days: list[str]) -> str:
    if len(days) == len(DAY_KEYS):
        return "Every day"
    indexes = [DAY_KEYS.index(d) for d in days]
    parts: list[str] = []
    i = 0
    while i < len(indexes):
        j = i
        while j + 1 < len(indexes) and indexes[j + 1] == indexes[j] + 1:
            j += 1
        if j - i >= 2:  # three or more in a row read as a range
            parts.append(f"{_DAY_LABEL[DAY_KEYS[indexes[i]]]} to {_DAY_LABEL[DAY_KEYS[indexes[j]]]}")
        else:
            parts.extend(_DAY_LABEL[DAY_KEYS[k]] for k in indexes[i : j + 1])
        i = j + 1
    return ", ".join(parts)


def closes_after_midnight(opens: str, closes: str) -> bool:
    return closes < opens


def summarise_hours(value: Any) -> str:
    """The one place hours become words: "Mon to Sat, 07:00 to 21:00", "Every day, open 24 hours".

    A legacy free-text string is returned as written. Anything unreadable is an empty string.
    """
    if isinstance(value, str):
        return value
    if validate_hours(normalise_hours(value) if isinstance(value, dict) else value) is not None:
        return ""
    value = normalise_hours(value)
    days = _day_phrase(value["days"])
    if value["open_24h"]:
        return f"{days}, open 24 hours"
    opens, closes = value["opens"], value["closes"]
    suffix = " (next day)" if closes_after_midnight(opens, closes) else ""
    return f"{days}, {opens} to {closes}{suffix}"
