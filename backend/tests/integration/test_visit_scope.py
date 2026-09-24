"""A second site visit, the visit day and the undo of a withdrawn question (UAT run 5, 24 Sep 2026).

F15: after Return to review from the post-site path the officer's case is a review again (feedback,
resubmission), with the first visit as history. F16: the operator answers the second visit's appointment.
F17 and F18: the second visit starts blank and the first stays readable, checklist and clarification
thread included, for both roles. F8: a confirmed date stands while the operator's request to move it waits.
F12: Mark site visit done and the checklist submit wait for the visit day. F19: a withdrawn question can
be restored inside the undo window."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.site_visit import today_in_singapore
from app.models import AuditEvent, ClarificationRequest, SiteVisit, SiteVisitProposal
from tests.integration.test_clarification import FLAGGED, _answer_all, _submitted
from tests.journeys import (
    arrange_visit,
    next_working_day,
    propose_visit,
    submit_clean_checklist,
    transition,
    under_review,
)

Headers = dict[str, str]
OFFICER = "/api/v1/officer/applications/{}"
OPERATOR = "/api/v1/applications/{}"


def _clarified_and_returned(client: TestClient, db: Session) -> tuple[str, Headers, Headers]:
    """Visit 1 with three flagged items, answered and clarified, routed to approval, then returned to
    review: the case the UAT run found stuck."""
    app_id, op, off = _submitted(client, db)
    _answer_all(client, op, app_id)
    view = client.get(OFFICER.format(app_id), headers=off).json()
    for t in view["clarification"]["items"]:
        r = client.post(f"{OFFICER.format(app_id)}/clarifications/{t['item_id']}/resolve", headers=off)
        assert r.status_code == 200, r.text
    transition(client, off, app_id, "pending_approval")
    transition(client, off, app_id, "under_review")
    return app_id, op, off


def test_return_to_review_is_a_review_again_with_the_visit_as_history(
    client: TestClient, db: Session
) -> None:
    app_id, op, off = _clarified_and_returned(client, db)
    view = client.get(OFFICER.format(app_id), headers=off).json()
    assert view["status"] == "under_review"
    # Nothing of visit 1 is presented as the active visit: the review panels are what the officer uses.
    assert view["site_visit"] is None and view["checklist"] is None and view["clarification"] is None
    assert view["feedback_editable"] is True
    [earlier] = view["earlier_visits"]
    assert earlier["visit_no"] == 1
    assert earlier["site_visit"]["status"] == "done" and earlier["site_visit"]["is_current"] is False
    assert earlier["checklist"]["status"] == "submitted" and earlier["checklist"]["counts"]["flagged"] == 3
    threads = earlier["clarification"]["items"]
    assert sorted(t["key"] for t in threads) == sorted(FLAGGED)
    assert not any(t["can_resolve"] or t["can_reopen"] or t["can_withdraw"] for t in threads)
    # F15: feedback and a resubmission are available again.
    r = client.post(
        f"{OFFICER.format(app_id)}/feedback",
        headers=off,
        json={"target_type": "section", "section_key": "operations", "message": "Add the split shifts."},
    )
    assert r.status_code == 201, r.text
    after = transition(client, off, app_id, "pending_pre_site_resubmission")
    assert after["status"] == "pending_pre_site_resubmission"
    # The operator sees the visit and every answer as history, read-only.
    mine = client.get(OPERATOR.format(app_id), headers=op).json()
    assert mine["site_visit"] is None and mine["clarification"] is None
    [past] = mine["earlier_visits"]
    assert past["visit_no"] == 1 and past["site_visit"]["can_accept"] is False
    assert sorted(i["key"] for i in past["clarification"]["items"]) == sorted(FLAGGED)
    assert all(i["status"] == "Clarified" and i["responses"] for i in past["clarification"]["items"])
    assert past["clarification"]["can_respond"] is False


def test_second_visit_is_answered_by_the_operator_and_starts_blank(client: TestClient, db: Session) -> None:
    app_id, op, off = _clarified_and_returned(client, db)
    propose_visit(client, off, app_id, date=next_working_day(4))
    # F16: the operator sees visit 2's proposal and can answer it; visit 1's thread is history.
    mine = client.get(OPERATOR.format(app_id), headers=op).json()
    assert mine["site_visit"]["visit_no"] == 2 and mine["site_visit"]["can_accept"] is True
    assert mine["clarification"] is None and mine["needs_operator_action"] is True
    assert [v["visit_no"] for v in mine["earlier_visits"]] == [1]
    # The active clarification endpoint is visit 2's (empty); visit 1's stays readable by number.
    now = client.get(f"{OPERATOR.format(app_id)}/clarifications", headers=op).json()
    assert now["items"] == [] and now["can_respond"] is False
    past = client.get(f"{OPERATOR.format(app_id)}/clarifications?visit=1", headers=op).json()
    assert past["visit_no"] == 1 and sorted(i["key"] for i in past["items"]) == sorted(FLAGGED)
    assert past["can_respond"] is False
    r = client.post(f"{OPERATOR.format(app_id)}/site-visit/accept", headers=op)
    assert r.status_code == 200, r.text
    # F17: the officer's card has no checklist for visit 2 until it is opened; visit 1 is history.
    view = client.get(OFFICER.format(app_id), headers=off).json()
    assert view["site_visit"]["visit_no"] == 2 and view["site_visit"]["date_stands"] is True
    assert view["checklist"] is None and view["clarification"] is None
    [earlier] = view["earlier_visits"]
    assert earlier["checklist"]["visit_no"] == 1 and earlier["site_visit"]["visit_no"] == 1
    opened = client.post(f"{OFFICER.format(app_id)}/checklist", headers=off).json()
    assert opened["visit_no"] == 2 and opened["counts"]["assessed"] == 0
    first = client.get(f"{OFFICER.format(app_id)}/checklist?visit=1", headers=off).json()
    assert first["visit_no"] == 1 and first["status"] == "submitted"
    submit_clean_checklist(client, off, app_id)
    view = client.get(OFFICER.format(app_id), headers=off).json()
    assert view["status"] == "awaiting_post_site_clarification"
    assert view["checklist"]["visit_no"] == 2
    assert view["clarification"]["visit_no"] == 2 and view["clarification"]["items"] == []
    # Nothing flagged on visit 2: the operator is waiting on nobody, visit 1's answers still on record.
    mine = client.get(OPERATOR.format(app_id), headers=op).json()
    assert mine["site_visit"]["visit_no"] == 2 and mine["site_visit"]["status"] == "done"
    assert mine["earlier_visits"][0]["clarification"] is not None


def test_a_confirmed_date_stands_while_the_operator_asks_to_move_it(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    r = client.post(
        f"{OPERATOR.format(app_id)}/site-visit/reschedule",
        headers=op,
        json={"date": next_working_day(6), "slot": "afternoon", "reason": "Contractor on site."},
    )
    assert r.status_code == 200, r.text
    view = client.get(OFFICER.format(app_id), headers=off).json()
    assert view["site_visit"]["status"] == "counter_proposed"
    # F8: the checklist stays open and the visit can be recorded on the date that stands.
    assert view["site_visit"]["date_stands"] is True
    done = next(a for a in view["actions"] if a["target"] == "site_visit_done")
    assert done["enabled"] is True, done
    assert client.post(f"{OFFICER.format(app_id)}/checklist", headers=off).status_code in (200, 201)
    submit_clean_checklist(client, off, app_id)
    visit = db.scalar(select(SiteVisit).where(SiteVisit.application_id == uuid.UUID(app_id)))
    assert visit is not None
    db.refresh(visit)
    assert visit.status.value == "done"
    proposals = list(db.scalars(select(SiteVisitProposal).where(SiteVisitProposal.site_visit_id == visit.id)))
    assert proposals[-1].outcome.value == "declined"
    events = [
        e.event_type
        for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == uuid.UUID(app_id)))
    ]
    assert "site_visit.move_request_closed" in events


def test_an_unconfirmed_counter_does_not_count_as_a_standing_date(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    propose_visit(client, off, app_id)
    r = client.post(
        f"{OPERATOR.format(app_id)}/site-visit/counter",
        headers=op,
        json={"date": next_working_day(5), "slot": "morning", "reason": "Away that day."},
    )
    assert r.status_code == 200, r.text
    view = client.get(OFFICER.format(app_id), headers=off).json()
    assert view["site_visit"]["date_stands"] is False
    done = next(a for a in view["actions"] if a["target"] == "site_visit_done")
    assert done["enabled"] is False and "Confirm the visit date" in done["reason"]


def test_the_visit_is_recorded_on_or_after_its_day(
    client: TestClient, db: Session, visit_day_guard: None
) -> None:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    view = client.get(OFFICER.format(app_id), headers=off).json()
    done = next(a for a in view["actions"] if a["target"] == "site_visit_done")
    assert done["enabled"] is False and "Mark it done on or after that day" in done["reason"]
    assert view["site_visit"]["visit_day_reached"] is False
    version = view["version"]
    r = client.post(
        f"{OFFICER.format(app_id)}/transition",
        headers=off,
        json={"target": "site_visit_done", "expected_version": version},
    )
    assert r.status_code == 409 and "on or after that day" in r.json()["error"]["message"]
    # The draft can be filled ahead of the day; the submit waits for it.
    r = client.post(f"{OFFICER.format(app_id)}/checklist", headers=off)
    assert r.status_code in (200, 201)
    from app.domain.checklist_schema import ITEM_KEYS

    items = [
        {"key": k, "result": "satisfactory", "comment": None, "needs_clarification": False} for k in ITEM_KEYS
    ]
    body = {"items": items, "version": r.json()["version"]}
    r = client.put(f"{OFFICER.format(app_id)}/checklist", headers=off, json=body)
    assert r.status_code == 200, r.text
    r = client.post(f"{OFFICER.format(app_id)}/checklist/submit", headers=off)
    assert r.status_code == 409 and "on or after that day" in r.json()["error"]["message"]
    # The visit day arrives (the calendar is walked in the database).
    visit = db.scalar(select(SiteVisit).where(SiteVisit.application_id == uuid.UUID(app_id)))
    assert visit is not None
    visit.date = today_in_singapore()
    db.commit()
    view = client.get(OFFICER.format(app_id), headers=off).json()
    assert next(a for a in view["actions"] if a["target"] == "site_visit_done")["enabled"] is True
    assert view["site_visit"]["visit_day_reached"] is True
    r = client.post(f"{OFFICER.format(app_id)}/checklist/submit", headers=off)
    assert r.status_code == 200, r.text


def test_a_withdrawn_question_can_be_restored_inside_the_window(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    view = client.get(OFFICER.format(app_id), headers=off).json()
    item = view["clarification"]["items"][0]
    base = f"{OFFICER.format(app_id)}/clarifications/{item['item_id']}"
    # Only a withdrawn question can be restored; the operator never can.
    assert client.post(f"{base}/restore", headers=off).status_code == 409
    assert client.post(f"{base}/withdraw", headers=off).status_code == 200
    assert client.post(f"{base}/restore", headers=op).status_code == 403
    r = client.post(f"{base}/restore", headers=off)
    assert r.status_code == 200, r.text
    restored = next(t for t in r.json()["clarification"]["items"] if t["item_id"] == item["item_id"])
    assert restored["status"] == "open"
    mine = client.get(f"{OPERATOR.format(app_id)}/clarifications", headers=op).json()
    assert item["key"] in [i["key"] for i in mine["items"]]
    # Outside the window: 409.
    assert client.post(f"{base}/withdraw", headers=off).status_code == 200
    request = db.scalars(
        select(ClarificationRequest).where(ClarificationRequest.item_id == uuid.UUID(item["item_id"]))
    ).all()[-1]
    request.withdrawn_at = datetime.now(UTC) - timedelta(minutes=5)
    db.commit()
    r = client.post(f"{base}/restore", headers=off)
    assert r.status_code == 409 and "no longer be restored" in r.json()["error"]["message"]
    events = [
        e.event_type
        for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == uuid.UUID(app_id)))
    ]
    assert events.count("clarification.restored") == 1
