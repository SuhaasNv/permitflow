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


def test_audit_summaries_read_as_sentences() -> None:
    from app.domain.audit_labels import summarize

    base = {"visit_no": 1, "date": "2026-09-22", "slot": "morning", "status": "proposed"}
    assert (
        summarize("site_visit.proposed", {**base, "round": 1})
        == "Site visit proposed: 2026-09-22, morning (round 1)"
    )
    assert summarize("site_visit.counter_proposed", {**base, "round": 2}) == (
        "Operator proposed another visit date (round 2)"
    )
    assert summarize("site_visit.confirmed", {**base, "how": "kept_original_date"}) == (
        "Site visit confirmed: 2026-09-22, morning (original date kept)"
    )
    assert summarize("site_visit.rescheduled", {**base, "round": 3, "by": "operator"}) == (
        "Site visit reschedule asked by the operator: 2026-09-22, morning (round 3)"
    )


def test_reply_deadline_never_falls_after_the_visit() -> None:
    proposed = datetime(2026, 9, 20, 13, 0, tzinfo=UTC)  # Sunday in Singapore
    assert reply_deadline(proposed) == date(2026, 9, 23)
    # A visit on Tuesday: the working day before it (Monday), which is also the first working day.
    assert reply_deadline(proposed, date(2026, 9, 22)) == date(2026, 9, 21)
    assert reply_deadline(proposed, date(2026, 10, 2)) == date(2026, 9, 23)


def test_reply_deadline_is_the_working_day_before_the_visit() -> None:
    # UAT run 5 (F4): proposed Thursday 24 Sep for Tuesday 29 Sep. Three working days would be the visit
    # day itself; the officer may confirm alone from Monday 28 Sep instead.
    thursday = datetime(2026, 9, 24, 4, 31, tzinfo=UTC)
    assert reply_deadline(thursday, date(2026, 9, 29)) == date(2026, 9, 28)
    # A visit on the next working day: the operator still gets that day, so the deadline is the visit day.
    assert reply_deadline(thursday, date(2026, 9, 25)) == date(2026, 9, 25)
    # A Monday visit proposed on Thursday: Friday, the working day before it.
    assert reply_deadline(thursday, date(2026, 9, 28)) == date(2026, 9, 25)


def test_midnight_in_singapore_not_utc() -> None:
    """Singapore is UTC+8: 16:00 UTC is already the next calendar day there (NFR-016, US-090)."""
    assert today_in_singapore(datetime(2026, 9, 21, 15, 59, tzinfo=UTC)) == date(2026, 9, 21)
    assert today_in_singapore(datetime(2026, 9, 21, 16, 0, tzinfo=UTC)) == date(2026, 9, 22)
    # a proposal at 23:30 Friday in Singapore counts from Friday; one at 00:30 Saturday from Saturday
    friday_late = datetime(2026, 9, 25, 15, 30, tzinfo=UTC)
    saturday_early = datetime(2026, 9, 25, 16, 30, tzinfo=UTC)
    assert reply_deadline(friday_late) == date(2026, 9, 30)
    assert reply_deadline(saturday_early) == date(2026, 9, 30)  # Saturday start counts from Monday
    # the operator's "too soon" rule uses the Singapore date: a Tuesday counter made late Sunday SGT
    assert (
        date_problem(
            date(2026, 9, 22), today_in_singapore(datetime(2026, 9, 20, 15, 0, tzinfo=UTC)), by_operator=True
        )
        is None
    )
    assert (
        date_problem(
            date(2026, 9, 22), today_in_singapore(datetime(2026, 9, 20, 16, 0, tzinfo=UTC)), by_operator=True
        )
        is not None
    )


def test_checklist_audit_summaries_read_as_sentences() -> None:
    from app.domain.audit_labels import summarize

    assert (
        summarize("checklist.created", {"visit_no": 1, "items": 17})
        == "Checklist opened for visit 1 (17 items)"
    )
    assert summarize(
        "checklist.submitted",
        {
            "visit_no": 1,
            "satisfactory": 14,
            "unsatisfactory": 2,
            "not_applicable": 1,
            "flagged_keys": ["a", "b"],
        },
    ) == (
        "Checklist submitted for visit 1: 14 satisfactory, 2 unsatisfactory, 1 not applicable, "
        "2 flagged for clarification"
    )
