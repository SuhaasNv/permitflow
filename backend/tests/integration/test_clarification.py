"""The operator's clarification view (US-064, FR-041, SEC-004): only the flagged items with a released
question, in operator words, by construction; the application block and the Needs your response rule."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.checklist_schema import ITEM_KEYS
from app.domain.enums import Role
from tests.factories import login, make_user
from tests.journeys import arrange_visit, under_review

Headers = dict[str, str]
CHECKLIST = "/api/v1/officer/applications/{}/checklist"
FLAGGED = ("floor_trap_graded", "coved_edges", "chiller_temperature")


def _items() -> list[dict]:  # type: ignore[type-arg]
    out = []
    for k in ITEM_KEYS:
        row = {"key": k, "result": "satisfactory", "comment": None, "needs_clarification": False}
        if k in FLAGGED:
            row = {
                "key": k,
                "result": "unsatisfactory",
                "comment": f"Please confirm {k}.",
                "needs_clarification": True,
            }
        if k == "make_up_air":
            row = {
                "key": k,
                "result": "unsatisfactory",
                "comment": "Hood runs without make-up air.",
                "needs_clarification": False,
            }
        out.append(row)
    return out


def _submitted(client: TestClient, db: Session) -> tuple[str, Headers, Headers]:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    r = client.post(CHECKLIST.format(app_id), headers=off)
    client.put(
        CHECKLIST.format(app_id), headers=off, json={"items": _items(), "version": r.json()["version"]}
    )
    r = client.post(CHECKLIST.format(app_id) + "/submit", headers=off)
    assert r.status_code == 200, r.text
    return app_id, op, off


def test_operator_sees_exactly_the_flagged_items_and_no_result(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    r = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op)
    assert r.status_code == 200, r.text
    view = r.json()
    assert sorted(i["key"] for i in view["items"]) == sorted(FLAGGED)
    assert view["open_count"] == 3 and view["round"] == 1 and view["can_respond"] is True
    assert view["visit_no"] == 1 and view["can_send"] is False
    text = r.text
    # by construction: no result, no unflagged item, no officer-only wording
    assert "make_up_air" not in text and "unsatisfactory" not in text and "satisfactory" not in text
    assert "Hood runs without" not in text
    for i in view["items"]:
        assert set(i) == {
            "item_id",
            "key",
            "title",
            "guidance",
            "status",
            "round_no",
            "requests",
            "responses",
            "can_respond",
        }
        assert i["status"] == "Waiting for your response" and i["can_respond"] is True
        assert (
            i["requests"][0]["message"] == f"Please confirm {i['key']}." and i["requests"][0]["round_no"] == 1
        )
        assert i["responses"] == []
    # the application view carries the block and the case needs the operator
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["clarification"] == {"can_respond": True, "open_count": 3, "answered_count": 0, "round": 1}
    assert mine["needs_operator_action"] is True and mine["status_label"] == "Pending Post-Site Clarification"
    assert mine["can_edit"] is False
    listed = next(a for a in client.get("/api/v1/applications", headers=op).json() if a["id"] == app_id)
    assert listed["needs_operator_action"] is True


def test_unreleased_and_withdrawn_questions_stay_invisible(client: TestClient, db: Session) -> None:
    """A round-2 question the officer drafted but has not sent, or one withdrawn, never reaches the
    operator; the view is built from released, non-withdrawn requests only."""
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models import ChecklistItem, ClarificationRequest, User

    app_id, op, off = _submitted(client, db)
    officer = db.scalar(select(User).where(User.email == "off@example.sg"))
    assert officer is not None
    items = {i.item_key: i for i in db.scalars(select(ChecklistItem))}
    # an unreleased round-2 question on one flagged item, and a withdrawn question on another
    db.add(
        ClarificationRequest(
            item_id=items["coved_edges"].id,
            round_no=2,
            author_id=officer.id,
            message="Still unclear.",
            released_at=None,
        )
    )
    first = db.scalar(
        select(ClarificationRequest).where(ClarificationRequest.item_id == items["chiller_temperature"].id)
    )
    assert first is not None
    first.withdrawn_at = datetime.now(UTC)
    db.commit()
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert "Still unclear." not in str(view)
    coved = next(i for i in view["items"] if i["key"] == "coved_edges")
    assert [q["round_no"] for q in coved["requests"]] == [1]
    assert "chiller_temperature" not in [i["key"] for i in view["items"]]


def test_nothing_open_means_waiting_not_needs_response(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    r = client.post(CHECKLIST.format(app_id), headers=off)
    clean = [
        {"key": k, "result": "satisfactory", "comment": None, "needs_clarification": False} for k in ITEM_KEYS
    ]
    client.put(CHECKLIST.format(app_id), headers=off, json={"items": clean, "version": r.json()["version"]})
    assert client.post(CHECKLIST.format(app_id) + "/submit", headers=off).status_code == 200
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["needs_operator_action"] is False and mine["clarification"] is None
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert view["items"] == [] and view["can_respond"] is False
    listed = next(a for a in client.get("/api/v1/applications", headers=op).json() if a["id"] == app_id)
    assert listed["needs_operator_action"] is False


def test_ownership_and_roles(client: TestClient, db: Session) -> None:
    app_id, op, off = _submitted(client, db)
    make_user(db, "other-cl@example.sg", Role.OPERATOR)
    other = login(client, "other-cl@example.sg")
    assert client.get(f"/api/v1/applications/{app_id}/clarifications", headers=other).status_code == 404
    assert client.get(f"/api/v1/applications/{app_id}/clarifications", headers=off).status_code == 403
    assert client.get(f"/api/v1/applications/{uuid.uuid4()}/clarifications", headers=op).status_code == 404
