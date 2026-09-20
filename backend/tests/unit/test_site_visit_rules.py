"""The appointment's date rules (US-084): Singapore working days, notice periods, the reply deadline."""

from datetime import UTC, date, datetime

from app.domain.enums import SiteVisitSlot
from app.domain.site_visit import (
    add_working_days,
    date_problem,
    earliest_date,
    format_visit,
    is_working_day,
    reply_deadline,
    short_visit,
    today_in_singapore,
)

MON = date(2026, 9, 21)  # a Monday


def test_working_days_skip_the_weekend() -> None:
    assert is_working_day(MON) and not is_working_day(date(2026, 9, 26))
    assert add_working_days(date(2026, 9, 18), 1) == MON  # Friday plus one is Monday
    assert add_working_days(date(2026, 9, 19), 2) == date(2026, 9, 22)  # Saturday start counts from Monday
    assert add_working_days(MON, 3) == date(2026, 9, 24)


def test_notice_periods_differ_per_side() -> None:
    assert earliest_date(MON, by_operator=False) == date(2026, 9, 22)
    assert earliest_date(MON, by_operator=True) == date(2026, 9, 23)
    assert (
        date_problem(date(2026, 9, 22), MON, by_operator=True)
        == "Choose a date at least 2 working days ahead."
    )
    assert date_problem(date(2026, 9, 22), MON, by_operator=False) is None
    assert date_problem(MON, MON, by_operator=False) == "Choose a date from the next working day."
    assert (
        date_problem(date(2026, 9, 27), MON, by_operator=False) == "Choose a working day, Monday to Friday."
    )
    assert date_problem(date(2026, 12, 1), MON, by_operator=False) == "Choose a date within the next 60 days."


def test_reply_deadline_is_three_working_days_in_singapore_time() -> None:
    # 23:30 UTC on Friday is already Saturday 07:30 in Singapore: the clock starts on the Singapore date.
    friday_night_utc = datetime(2026, 9, 18, 23, 30, tzinfo=UTC)
    assert today_in_singapore(friday_night_utc) == date(2026, 9, 19)
    assert reply_deadline(friday_night_utc) == date(2026, 9, 23)
    assert reply_deadline(datetime(2026, 9, 21, 8, 0, tzinfo=UTC)) == date(2026, 9, 24)


def test_wording() -> None:
    assert (
        format_visit(date(2026, 9, 22), SiteVisitSlot.MORNING)
        == "Tuesday 22 September 2026, morning (09:00 to 12:00)"
    )
    assert short_visit(date(2026, 9, 24), SiteVisitSlot.AFTERNOON) == "Thu 24 Sep, afternoon"


def test_round_cap_counts_both_sides() -> None:
    from app.domain.site_visit import MAX_ROUNDS, rounds_left

    assert MAX_ROUNDS == 6
    assert rounds_left(0) == 6 and rounds_left(5) == 1 and rounds_left(6) == 0 and rounds_left(9) == 0
