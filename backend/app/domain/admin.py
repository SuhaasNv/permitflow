"""Pure rules for the administrator's overview (US-070): whose turn a status is, the Singapore calendar
day as a UTC window, idle days."""

from datetime import UTC, date, datetime, time, timedelta

from app.domain.enums import ApplicationStatus as S
from app.domain.site_visit import SINGAPORE, today_in_singapore
from app.domain.workflow import TERMINAL

IDLE_DAYS = 7
IDLE_LIST_SIZE = 10

# Whose move a status is, as the overview groups them: the office, the operator, or nobody.
_OPERATOR_TURN = frozenset(
    {S.PENDING_PRE_SITE_RESUBMISSION, S.AWAITING_POST_SITE_CLARIFICATION, S.PENDING_POST_SITE_RESUBMISSION}
)


def turn_for(status: S) -> str:
    if status == S.DRAFT:
        return "draft"
    if status in TERMINAL:
        return "decided"
    if status in _OPERATOR_TURN:
        return "operator"
    return "office"


def singapore_day_window(day: date) -> tuple[datetime, datetime]:
    """The UTC instants that bound one Singapore calendar day, half-open."""
    start = datetime.combine(day, time.min, tzinfo=SINGAPORE).astimezone(UTC)
    return start, start + timedelta(days=1)


def idle_days(last_activity: datetime, now: datetime | None = None) -> int:
    """Whole Singapore calendar days since the last activity: an application last touched yesterday
    evening is one day idle this morning, however few hours passed."""
    today = today_in_singapore(now)
    last = last_activity.astimezone(SINGAPORE).date()
    return max((today - last).days, 0)


def is_idle(days: int) -> bool:
    return days > IDLE_DAYS


def percentile(values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile; None without values."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(fraction * len(ordered) + 0.5) - 1))
    return ordered[index]


__all__ = [
    "IDLE_DAYS",
    "IDLE_LIST_SIZE",
    "idle_days",
    "is_idle",
    "percentile",
    "singapore_day_window",
    "turn_for",
]
