"""Site visit appointment rules (US-084, FR-043). Pure: dates in and out, no I/O.

The officer proposes a date and a slot; the operator accepts or proposes another; the officer decides.
Dates are Singapore working days (Monday to Friday; public holidays are not modelled in this release, an
accepted simplification recorded in SCOPE.md). Times are the two slots the licensing office inspects in.
"""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.enums import SiteVisitSlot

SINGAPORE = ZoneInfo("Asia/Singapore")

SLOT_TIMES: dict[SiteVisitSlot, tuple[str, str]] = {
    SiteVisitSlot.MORNING: ("09:00", "12:00"),
    SiteVisitSlot.AFTERNOON: ("14:00", "17:00"),
}
SLOT_LABELS: dict[SiteVisitSlot, str] = {
    SiteVisitSlot.MORNING: "morning",
    SiteVisitSlot.AFTERNOON: "afternoon",
}

# The operator needs notice to have the premises and the people ready; the officer plans a day ahead.
OPERATOR_MIN_WORKING_DAYS_AHEAD = 2
OFFICER_MIN_WORKING_DAYS_AHEAD = 1
MAX_DAYS_AHEAD = 60
# A proposal the operator leaves unanswered can be confirmed by the officer after this many working days.
REPLY_WORKING_DAYS = 3
# Proposals per visit, both sides together, reschedules included. At the cap only the closing moves remain:
# the operator accepts, the officer accepts the operator's date or keeps the original.
MAX_ROUNDS = 6
ROUND_LIMIT_REASON = "No more dates can be proposed for this visit."
# A date that has arrived cannot be confirmed any more: whoever holds the move proposes another one.
PAST_DATE_REASON = "This date has passed; propose another one."


def rounds_left(proposal_count: int) -> int:
    return max(0, MAX_ROUNDS - proposal_count)


def today_in_singapore(now: datetime | None = None) -> date:
    now = now or datetime.now(UTC)
    return now.astimezone(SINGAPORE).date()


def is_working_day(d: date) -> bool:
    return d.weekday() < 5


def add_working_days(start: date, days: int) -> date:
    """The date `days` working days after `start` (a Saturday start counts from the next Monday)."""
    d = start
    remaining = days
    while remaining > 0:
        d += timedelta(days=1)
        if is_working_day(d):
            remaining -= 1
    return d


def reply_deadline(proposed_at: datetime, visit_date: date | None = None) -> date:
    """The Singapore date from which an unanswered proposal may be confirmed by the officer alone:
    three working days after the proposal, never later than the visit itself."""
    deadline = add_working_days(proposed_at.astimezone(SINGAPORE).date(), REPLY_WORKING_DAYS)
    return min(deadline, visit_date) if visit_date else deadline


def earliest_date(today: date, *, by_operator: bool) -> date:
    ahead = OPERATOR_MIN_WORKING_DAYS_AHEAD if by_operator else OFFICER_MIN_WORKING_DAYS_AHEAD
    return add_working_days(today, ahead)


def date_problem(d: date, today: date, *, by_operator: bool) -> str | None:
    """The rule a proposed date breaks, in the words the form shows, or None when it is fine."""
    if not is_working_day(d):
        return "Choose a working day, Monday to Friday."
    earliest = earliest_date(today, by_operator=by_operator)
    if d < earliest:
        if by_operator:
            return f"Choose a date at least {OPERATOR_MIN_WORKING_DAYS_AHEAD} working days ahead."
        return "Choose a date from the next working day."
    if d > today + timedelta(days=MAX_DAYS_AHEAD):
        return f"Choose a date within the next {MAX_DAYS_AHEAD} days."
    return None


def format_visit(d: date, slot: SiteVisitSlot) -> str:
    """\"Tuesday 22 September 2026, morning (09:00 to 12:00)\"."""
    start, end = SLOT_TIMES[slot]
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}, {SLOT_LABELS[slot]} ({start} to {end})"


def short_visit(d: date, slot: SiteVisitSlot) -> str:
    """\"Tue 22 Sep, morning\" for notifications and the queue."""
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b')}, {SLOT_LABELS[slot]}"
