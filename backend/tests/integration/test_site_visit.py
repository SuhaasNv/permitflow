"""The site visit appointment (US-084, FR-043): propose, accept or counter, decide, reschedule, confirm
without a reply, done only once confirmed; every round audited and both sides notified."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import Role
from app.domain.site_visit import add_working_days, date_problem, reply_deadline, today_in_singapore
from app.models import AuditEvent, Notification, SiteVisit, SiteVisitProposal
from app.repositories.users import UserRepository
from app.services.site_visit import SiteVisitService
from tests.factories import login, make_user
from tests.journeys import arrange_visit, next_working_day, propose_visit, transition, under_review

Headers = dict[str, str]


def _officer_view(client: TestClient, off: Headers, app_id: str) -> dict:  # type: ignore[type-arg]
    return client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()


def _operator_view(client: TestClient, op: Headers, app_id: str) -> dict:  # type: ignore[type-arg]
    return client.get(f"/api/v1/applications/{app_id}", headers=op).json()


def _events(db: Session, app_id: str, prefix: str = "site_visit.") -> list[AuditEvent]:
    rows = db.scalars(
        select(AuditEvent).where(AuditEvent.application_id == app_id).order_by(AuditEvent.created_at)
    )
    return [e for e in rows if e.event_type.startswith(prefix)]


def test_propose_from_under_review_moves_the_case_and_asks_the_operator(
    client: TestClient, db: Session
) -> None:
    app_id, op, off, _ = under_review(client, db)
    view = propose_visit(client, off, app_id, slot="afternoon")
    assert view["status"] == "site_visit_scheduled"
    visit = view["site_visit"]
    assert visit["status"] == "proposed" and visit["status_label"] == "Waiting for the operator"
    assert visit["slot"] == "afternoon" and "(14:00 to 17:00)" in visit["when"]
    assert (
        visit["can_confirm_without_reply"] is False
        and "Available from" in visit["confirm_without_reply_reason"]
    )
    assert [r["author_role"] for r in visit["rounds"]] == ["officer"]
    # one status change plus the proposal, both audited, in that order
    types = [e.event_type for e in _events(db, app_id, "")]
    assert types[-2:] == ["status.changed", "site_visit.proposed"]
    # the operator sees the date in their own words and the case under Needs your response
    mine = _operator_view(client, op, app_id)
    assert mine["status_label"] == "Pending Site Visit"
    assert mine["status_explanation"].startswith("The licensing officer proposed a site visit.")
    assert mine["site_visit"]["status_label"] == "Waiting for your reply"
    # the officer's name stays inside the office: the operator sees the role
    assert mine["site_visit"]["rounds"][0]["author_name"] == "Licensing officer"
    assert view["site_visit"]["rounds"][0]["author_name"] not in ("", "Licensing officer")
    assert mine["site_visit"]["can_accept"] and mine["site_visit"]["can_counter"]
    assert mine["site_visit"]["reply_by"] is not None
    assert mine["needs_operator_action"] is True
    listed = client.get("/api/v1/applications", headers=op).json()
    assert next(a for a in listed if a["id"] == app_id)["needs_operator_action"] is True
    note = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert note is not None and "Site visit proposed" in note.title and "Accept the date" in note.body
    # the officer queue says whose move it is
    row = next(
        i
        for i in client.get("/api/v1/officer/applications", headers=off).json()["items"]
        if i["id"] == app_id
    )
    assert row["next_action"] == "Waiting on operator" and row["officer_turn"] is False


def test_operator_accepts_and_the_visit_can_be_marked_done(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id)
    view = _officer_view(client, off, app_id)
    done = next(a for a in view["actions"] if a["target"] == "site_visit_done")
    assert done["enabled"] is False
    r = client.post(f"/api/v1/applications/{app_id}/site-visit/accept", headers=op)
    assert r.status_code == 200
    assert r.json()["site_visit"]["status_label"] == "Confirmed"
    assert r.json()["needs_operator_action"] is False
    view = _officer_view(client, off, app_id)
    assert view["site_visit"]["status"] == "confirmed" and view["site_visit"]["can_reschedule"] is True
    done = next(a for a in view["actions"] if a["target"] == "site_visit_done")
    assert done["enabled"] is True
    # accepting twice is refused; the officers were told once
    assert client.post(f"/api/v1/applications/{app_id}/site-visit/accept", headers=op).status_code == 409
    titles = [n.title for n in db.scalars(select(Notification))]
    assert sum("Site visit confirmed" in t for t in titles) == 1
    view = transition(client, off, app_id, "site_visit_done")
    assert view["site_visit"]["status"] == "done"
    assert db.scalar(select(SiteVisit).where(SiteVisit.application_id == app_id)).done_at is not None


def test_counter_proposal_then_officer_accepts_the_operators_date(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id)
    later = next_working_day(4)
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": later, "slot": "afternoon", "reason": "The shop is closed that morning."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["site_visit"]["status_label"] == "Waiting for the officer"
    assert r.json()["site_visit"]["can_accept"] is False
    view = _officer_view(client, off, app_id)
    assert view["site_visit"]["status_label"] == "Waiting for you"
    assert view["site_visit"]["counter"]["date"] == later and view["site_visit"]["counter"]["reason"]
    assert view["site_visit"]["original"]["author_role"] == "officer"
    row = next(
        i
        for i in client.get("/api/v1/officer/applications", headers=off).json()["items"]
        if i["id"] == app_id
    )
    assert row["next_action"] == "Decide the visit date" and row["officer_turn"] is True
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "accept_operator"},
    )
    assert r.status_code == 200, r.text
    visit = r.json()["site_visit"]
    assert visit["status"] == "confirmed" and visit["date"] == later and visit["slot"] == "afternoon"
    outcomes = [
        p.outcome.value for p in db.scalars(select(SiteVisitProposal).order_by(SiteVisitProposal.round_no))
    ]
    assert outcomes == ["declined", "accepted"]
    events = _events(db, app_id)
    assert [e.event_type for e in events] == [
        "site_visit.proposed",
        "site_visit.counter_proposed",
        "site_visit.confirmed",
    ]
    assert events[-1].payload["how"] == "accepted_operator_date"
    mine = _operator_view(client, op, app_id)
    assert mine["site_visit"]["status_label"] == "Confirmed" and mine["site_visit"]["date"] == later
    assert mine["status_explanation"].startswith("Your site visit is confirmed.")


def test_officer_keeps_the_original_or_proposes_a_third_date(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    first = propose_visit(client, off, app_id)["site_visit"]["date"]
    client.post(
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": next_working_day(4), "slot": "morning", "reason": "Staff training that day."},
    )
    third = next_working_day(6)
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "propose", "date": third, "slot": "morning", "note": "Third attempt."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["site_visit"]["status"] == "proposed" and r.json()["site_visit"]["date"] == third
    assert [p["round"] for p in r.json()["site_visit"]["rounds"]] == [1, 2, 3]
    # the operator counters again; this time the officer keeps their own date
    client.post(
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": next_working_day(7), "slot": "afternoon", "reason": "Supplier delivery."},
    )
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "keep_original"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["site_visit"]["status"] == "confirmed" and r.json()["site_visit"]["date"] == third
    assert first != third
    events = _events(db, app_id)
    assert (
        events[-1].event_type == "site_visit.confirmed" and events[-1].payload["how"] == "kept_original_date"
    )
    last = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert last is not None and "kept the original date" in last.body


def test_reschedule_before_the_date_by_either_side(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    # the operator asks to move it: the officer decides, the case stays Site Visit Scheduled
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/reschedule",
        headers=op,
        json={"date": next_working_day(8), "slot": "morning"},
    )
    assert r.status_code == 422 and "reason" in r.json()["error"]["details"]["fields"]
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/reschedule",
        headers=op,
        json={"date": next_working_day(8), "slot": "morning", "reason": "Renovation overran."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["site_visit"]["status_label"] == "Waiting for the officer"
    assert r.json()["status_label"] == "Pending Site Visit"
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "accept_operator"},
    )
    assert r.status_code == 200 and r.json()["site_visit"]["status"] == "confirmed"
    # the officer moves it: the operator answers the new proposal
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/reschedule",
        headers=off,
        json={"date": next_working_day(9), "slot": "afternoon", "reason": "Officer on leave."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["site_visit"]["status"] == "proposed"
    assert _operator_view(client, op, app_id)["site_visit"]["can_accept"] is True
    types = [e.event_type for e in _events(db, app_id)]
    assert types.count("site_visit.rescheduled") == 2


def test_confirm_without_reply_only_after_three_working_days(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id, date=next_working_day(10))
    r = client.post(f"/api/v1/officer/applications/{app_id}/site-visit/confirm", headers=off)
    assert r.status_code == 409 and "has until" in r.json()["error"]["message"]
    # walk the calendar: a service with a clock three working days on may confirm alone
    proposal = db.scalar(select(SiteVisitProposal))
    assert proposal is not None
    deadline = reply_deadline(proposal.created_at)
    later = datetime.combine(deadline, datetime.min.time(), tzinfo=UTC) + timedelta(hours=6)
    row = db.scalar(select(SiteVisit).where(SiteVisit.application_id == uuid.UUID(app_id)))
    assert row is not None
    user = UserRepository(db).get(row.proposed_by_id)
    assert user is not None
    visit = SiteVisitService(db, now=later).confirm_without_reply(user, uuid.UUID(app_id))
    assert visit.status.value == "confirmed"
    events = _events(db, app_id)
    assert events[-1].payload["how"] == "confirmed_without_reply"
    last = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert last is not None and "No reply was received" in last.body


def test_a_proposal_whose_date_has_passed_is_never_confirmed_and_can_be_moved(
    client: TestClient, db: Session
) -> None:
    """The officer proposes, nobody acts, the date arrives: the operator cannot accept it, the officer
    cannot confirm it without a reply, and the proposal can be moved by either side instead of the case
    sitting with Reject as its only move (review finding, 21 Sep)."""
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id, date=next_working_day(1))
    # the calendar moves past the date
    row = db.scalar(select(SiteVisit).where(SiteVisit.application_id == uuid.UUID(app_id)))
    assert row is not None
    row.date = today_in_singapore() - timedelta(days=1)
    db.commit()
    reason = "This date has passed; propose another one."
    r = client.post(f"/api/v1/applications/{app_id}/site-visit/accept", headers=op)
    assert r.status_code == 409 and r.json()["error"]["message"] == reason
    mine = _operator_view(client, op, app_id)["site_visit"]
    assert mine["can_accept"] is False and mine["can_counter"] is True
    theirs = _officer_view(client, off, app_id)["site_visit"]
    assert theirs["can_confirm_without_reply"] is False and theirs["confirm_without_reply_reason"] == reason
    assert theirs["can_reschedule"] is True
    r = client.post(f"/api/v1/officer/applications/{app_id}/site-visit/confirm", headers=off)
    assert r.status_code == 409
    # the officer moves it: the lapsed proposal is settled, round 2 is a fresh proposal
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/reschedule",
        headers=off,
        json={"date": next_working_day(3), "slot": "afternoon", "reason": "The first date lapsed unanswered."},
    )
    assert r.status_code == 200, r.text
    visit = r.json()["site_visit"]
    assert visit["status"] == "proposed" and [p["outcome"] for p in visit["rounds"]] == ["declined", "pending"]
    # and the operator can now accept the new date
    r = client.post(f"/api/v1/applications/{app_id}/site-visit/accept", headers=op)
    assert r.status_code == 200 and r.json()["site_visit"]["status"] == "confirmed"


def test_an_expired_counter_proposal_cannot_be_accepted_by_the_officer(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id, date=next_working_day(6))
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": next_working_day(2), "slot": "morning", "reason": "Earlier suits us."},
    )
    assert r.status_code == 200, r.text
    counter = db.scalar(select(SiteVisitProposal).where(SiteVisitProposal.author_role == "operator"))
    assert counter is not None
    counter.date = today_in_singapore() - timedelta(days=1)
    db.commit()
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide", headers=off, json={"action": "accept_operator"}
    )
    assert r.status_code == 409 and "passed" in r.json()["error"]["message"]
    # the officer's own date is still ahead: keeping it works
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide", headers=off, json={"action": "keep_original"}
    )
    assert r.status_code == 200 and r.json()["site_visit"]["status"] == "confirmed"


def test_date_rules_and_validation(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    version = _officer_view(client, off, app_id)["version"]
    today = today_in_singapore()
    # the officer may not pick today, a weekend, or a date beyond 60 days
    for bad in (today.isoformat(), (today + timedelta(days=90)).isoformat()):
        r = client.post(
            f"/api/v1/officer/applications/{app_id}/site-visit",
            headers=off,
            json={"date": bad, "slot": "morning", "expected_version": version},
        )
        assert r.status_code == 422 and "date" in r.json()["error"]["details"]["fields"], bad
    saturday = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
    assert date_problem(saturday, today, by_operator=False) == "Choose a working day, Monday to Friday."
    # slot must be one of the two
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit",
        headers=off,
        json={"date": next_working_day(3), "slot": "evening", "expected_version": version},
    )
    assert r.status_code == 422 and "slot" in r.json()["error"]["details"]["fields"]
    # a stale version is refused before anything moves
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit",
        headers=off,
        json={"date": next_working_day(3), "slot": "morning", "expected_version": version + 5},
    )
    assert r.status_code == 409
    propose_visit(client, off, app_id)
    # the operator needs two working days' notice; tomorrow is too soon
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": add_working_days(today, 1).isoformat(), "slot": "morning", "reason": "Too soon."},
    )
    assert r.status_code == 422 and "working days ahead" in r.json()["error"]["details"]["fields"]["date"]
    # a second proposal while one is on the table is refused
    version = _officer_view(client, off, app_id)["version"]
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit",
        headers=off,
        json={"date": next_working_day(3), "slot": "morning", "expected_version": version},
    )
    assert r.status_code == 409


def test_authorization_and_ownership(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id)
    make_user(db, "other@example.sg", Role.OPERATOR)
    make_user(db, "admin-sv@example.sg", Role.ADMIN)
    other = login(client, "other@example.sg")
    admin = login(client, "admin-sv@example.sg")
    body = {"date": next_working_day(4), "slot": "morning", "reason": "x"}
    # operator routes: another operator gets 404 (ownership), an officer or admin 403
    assert client.post(f"/api/v1/applications/{app_id}/site-visit/accept", headers=other).status_code == 404
    assert (
        client.post(f"/api/v1/applications/{app_id}/site-visit/counter", headers=other, json=body).status_code
        == 404
    )
    assert client.post(f"/api/v1/applications/{app_id}/site-visit/accept", headers=off).status_code == 403
    assert client.post(f"/api/v1/applications/{app_id}/site-visit/accept", headers=admin).status_code == 403
    # officer routes: operators and admins get 403
    for h in (op, admin):
        assert (
            client.post(f"/api/v1/officer/applications/{app_id}/site-visit/confirm", headers=h).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/officer/applications/{app_id}/site-visit/decide",
                headers=h,
                json={"action": "keep_original"},
            ).status_code
            == 403
        )
    # the operator never receives the officer's wording or an internal code
    mine = _operator_view(client, op, app_id)
    text = str(mine["site_visit"])
    assert "Waiting for the operator" not in text and "site_visit_scheduled" not in text


def test_six_rounds_then_only_the_closing_moves_remain(client: TestClient, db: Session) -> None:
    """Round cap (MAX_ROUNDS = 6): the ping-pong ends; the operator can still accept, the officer can
    still accept or keep, and the reschedule of a confirmed visit is closed too."""
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id)  # round 1
    for i in range(2, 6, 2):  # rounds 2+3 and 4+5: operator counters, officer proposes a third date
        r = client.post(
            f"/api/v1/applications/{app_id}/site-visit/counter",
            headers=op,
            json={"date": next_working_day(4 + i), "slot": "afternoon", "reason": "Closed that day."},
        )
        assert r.status_code == 200, r.text
        r = client.post(
            f"/api/v1/officer/applications/{app_id}/site-visit/decide",
            headers=off,
            json={"action": "propose", "date": next_working_day(5 + i), "slot": "morning"},
        )
        assert r.status_code == 200, r.text
    view = _operator_view(client, op, app_id)["site_visit"]
    assert len(view["rounds"]) == 5 and view["rounds_left"] == 1 and view["can_counter"] is True
    r = client.post(  # round 6: the last one anybody may add
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": next_working_day(12), "slot": "afternoon", "reason": "Still closed."},
    )
    assert r.status_code == 200, r.text
    officer = _officer_view(client, off, app_id)["site_visit"]
    assert officer["rounds_left"] == 0 and "No more dates" in officer["round_limit_reason"]
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "propose", "date": next_working_day(14), "slot": "morning"},
    )
    assert r.status_code == 409 and "No more dates" in r.json()["error"]["message"]
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "keep_original"},
    )
    assert r.status_code == 200, r.text
    visit = r.json()["site_visit"]
    assert visit["status"] == "confirmed" and visit["can_reschedule"] is False
    mine = _operator_view(client, op, app_id)["site_visit"]
    assert mine["status_label"] == "Confirmed" and mine["can_reschedule"] is False
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/reschedule",
        headers=op,
        json={"date": next_working_day(14), "slot": "morning", "reason": "One more time."},
    )
    assert r.status_code == 409 and "No more dates" in r.json()["error"]["message"]


def test_keep_after_a_reschedule_keeps_the_confirmed_date_not_round_one(
    client: TestClient, db: Session
) -> None:
    """Officer proposes A, operator counters B, officer accepts B; the operator later asks for C and the
    officer keeps: the visit stays on B and the earlier rounds keep their recorded outcomes."""
    app_id, op, off, _ = under_review(client, db)
    a, b, c = next_working_day(3), next_working_day(5), next_working_day(8)
    propose_visit(client, off, app_id, date=a)
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": b, "slot": "afternoon", "reason": "Closed that morning."},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "accept_operator"},
    )
    assert r.status_code == 200 and r.json()["site_visit"]["date"] == b
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/reschedule",
        headers=op,
        json={"date": c, "slot": "morning", "reason": "Renovation that week."},
    )
    assert r.status_code == 200, r.text
    view = _officer_view(client, off, app_id)["site_visit"]
    assert view["date"] == b and view["original"]["round"] == 2 and view["counter"]["round"] == 3
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "keep_original"},
    )
    assert r.status_code == 200, r.text
    visit = r.json()["site_visit"]
    assert visit["status"] == "confirmed" and visit["date"] == b and visit["slot"] == "afternoon"
    outcomes = [
        p.outcome.value for p in db.scalars(select(SiteVisitProposal).order_by(SiteVisitProposal.round_no))
    ]
    assert outcomes == ["declined", "accepted", "declined"]
    mine = _operator_view(client, op, app_id)["site_visit"]
    assert mine["date"] == b and mine["status_label"] == "Confirmed"
    # the officer's own reschedule, countered, then kept: that pending proposal is the one marked kept
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/reschedule",
        headers=off,
        json={"date": c, "slot": "afternoon", "reason": "Inspector unavailable."},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/v1/applications/{app_id}/site-visit/counter",
        headers=op,
        json={"date": next_working_day(9), "slot": "morning", "reason": "Not that day."},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/site-visit/decide",
        headers=off,
        json={"action": "keep_original"},
    )
    assert r.status_code == 200 and r.json()["site_visit"]["date"] == c
    outcomes = [
        p.outcome.value for p in db.scalars(select(SiteVisitProposal).order_by(SiteVisitProposal.round_no))
    ]
    assert outcomes == ["declined", "accepted", "declined", "kept", "declined"]
