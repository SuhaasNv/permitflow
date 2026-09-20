"""The site visit checklist (US-060, FR-036, FR-037): the template, create-or-get under the row lock,
the draft save, the states that allow it, who may read and write, and the guard it closes."""

import concurrent.futures as cf
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.checklist_schema import ITEM_KEYS
from app.domain.enums import Role
from app.models import AuditEvent, Checklist, ChecklistItem
from tests.factories import login, make_user
from tests.journeys import arrange_visit, transition, under_review

Headers = dict[str, str]
URL = "/api/v1/officer/applications/{}/checklist"


def _items(result: str = "satisfactory", **over: dict) -> list[dict]:  # type: ignore[type-arg]
    return [
        {"key": k, "result": result, "comment": None, "needs_clarification": False} | over.get(k, {})
        for k in ITEM_KEYS
    ]


def _open(client: TestClient, off: Headers, app_id: str) -> dict:  # type: ignore[type-arg]
    r = client.post(URL.format(app_id), headers=off)
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_schema_is_versioned_with_seventeen_items_in_five_sections(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    r = client.get("/api/v1/checklist-schema", headers=off)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version"] == 1 and body["item_count"] == 17
    assert [s["key"] for s in body["sections"]] == ["premises", "kitchen", "storage", "upkeep", "people"]
    assert sum(len(s["items"]) for s in body["sections"]) == 17
    assert "Singapore Food Agency" in body["description"] and "not an SFA document" in body["description"]
    assert client.get("/api/v1/checklist-schema", headers=op).status_code == 403


def test_open_creates_once_then_returns_the_same_draft(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    assert client.post(URL.format(app_id), headers=off).status_code == 409  # under review: no visit yet
    assert client.get(URL.format(app_id), headers=off).status_code == 404
    arrange_visit(client, off, op, app_id)
    r = client.post(URL.format(app_id), headers=off)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["visit_no"] == 1 and body["status"] == "draft" and body["version"] == 1
    assert [i["key"] for i in body["items"]] == list(ITEM_KEYS)
    assert all(i["result"] == "not_assessed" for i in body["items"])
    assert body["counts"] == {
        "total": 17,
        "assessed": 0,
        "flagged": 0,
        "unsatisfactory": 0,
        "not_applicable": 0,
        "missing_comments": 0,
    }
    assert body["remaining"] == "Assess 17 more items to submit."
    r = client.post(URL.format(app_id), headers=off)
    assert r.status_code == 200 and r.json()["id"] == body["id"]
    assert db.scalar(select(Checklist).where(Checklist.application_id == uuid.UUID(app_id))) is not None
    assert len(list(db.scalars(select(ChecklistItem)))) == 17
    events = [e.event_type for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == app_id))]
    assert events.count("checklist.created") == 1
    # the case view carries the summary and the transitional route to approval is closed
    view = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert view["checklist"]["visit_no"] == 1 and view["checklist"]["counts"]["assessed"] == 0
    transition(client, off, app_id, "site_visit_done")
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "pending_approval", "expected_version": view["version"] + 1},
    )
    assert r.status_code == 409, r.text
    view = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    route = next(a for a in view["actions"] if a["target"] == "pending_approval")
    assert route["enabled"] is False


def test_two_tabs_opening_at_once_create_one_checklist(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        codes = sorted(
            f.result().status_code
            for f in [pool.submit(client.post, URL.format(app_id), headers=off) for _ in range(2)]
        )
    assert codes == [200, 201], codes
    rows = list(db.scalars(select(Checklist).where(Checklist.application_id == uuid.UUID(app_id))))
    assert len(rows) == 1


def test_draft_save_checks_the_template_and_the_version(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    body = _open(client, off, app_id)
    items = _items(
        "satisfactory",
        floor_trap_graded={"result": "unsatisfactory", "comment": "Floor slopes away from the trap."},
        coved_edges={"result": "unsatisfactory", "comment": None, "needs_clarification": True},
        food_hygiene_officer={"result": "not_applicable"},
        make_up_air={"result": "not_assessed"},
    )
    r = client.put(URL.format(app_id), headers=off, json={"items": items, "version": body["version"]})
    assert r.status_code == 200, r.text
    saved = r.json()
    assert saved["version"] == 2
    assert saved["counts"] == {
        "total": 17,
        "assessed": 16,
        "flagged": 1,
        "unsatisfactory": 2,
        "not_applicable": 1,
        "missing_comments": 1,
    }
    assert saved["remaining"] == "Assess 1 more item and add 1 comment to submit."
    by_key = {i["key"]: i for i in saved["items"]}
    assert by_key["floor_trap_graded"]["comment"] == "Floor slopes away from the trap."
    assert by_key["coved_edges"]["needs_clarification"] is True
    # a stale version is refused with the current content
    r = client.put(URL.format(app_id), headers=off, json={"items": items, "version": 1})
    assert r.status_code == 409 and r.json()["error"]["code"] == "version_conflict"
    assert r.json()["error"]["details"]["current"]["version"] == 2
    # unknown key, unknown result, missing items, over-long comment
    bad = _items() + [
        {"key": "gold_taps", "result": "satisfactory", "comment": None, "needs_clarification": False}
    ]
    r = client.put(URL.format(app_id), headers=off, json={"items": bad, "version": 2})
    assert r.status_code == 422 and "gold_taps" in r.json()["error"]["details"]["fields"]
    r = client.put(URL.format(app_id), headers=off, json={"items": _items("great"), "version": 2})
    assert r.status_code == 422 and "layout_matches_plan" in r.json()["error"]["details"]["fields"]
    r = client.put(URL.format(app_id), headers=off, json={"items": _items()[:5], "version": 2})
    assert r.status_code == 422 and "12 missing" in r.json()["error"]["details"]["fields"]["items"]
    r = client.put(
        URL.format(app_id),
        headers=off,
        json={"items": _items("satisfactory", ducting={"comment": "x" * 2001}), "version": 2},
    )
    assert r.status_code == 422
    # the replay of a lost response answers with the state, not a conflict
    r = client.put(URL.format(app_id), headers=off, json={"items": _items(), "version": 2, "save_id": "s-1"})
    assert r.status_code == 200 and r.json()["version"] == 3
    r = client.put(URL.format(app_id), headers=off, json={"items": _items(), "version": 2, "save_id": "s-1"})
    assert r.status_code == 200 and r.json()["version"] == 3
    # the queue names the next step
    row = next(
        i
        for i in client.get("/api/v1/officer/applications", headers=off).json()["items"]
        if i["id"] == app_id
    )
    assert row["next_action"] == "Continue the checklist"


def test_authorization_and_ownership(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    make_user(db, "admin-cl@example.sg", Role.ADMIN)
    admin = login(client, "admin-cl@example.sg")
    assert client.post(URL.format(app_id), headers=op).status_code == 403
    assert client.get(URL.format(app_id), headers=op).status_code == 403
    assert (
        client.put(URL.format(app_id), headers=op, json={"items": _items(), "version": 1}).status_code == 403
    )
    assert client.post(URL.format(app_id), headers=admin).status_code == 403
    assert (
        client.put(URL.format(app_id), headers=admin, json={"items": _items(), "version": 1}).status_code
        == 403
    )
    _open(client, off, app_id)
    r = client.get(URL.format(app_id), headers=admin)
    assert r.status_code == 200 and r.json()["visit_no"] == 1
    assert client.get("/api/v1/checklist-schema", headers=admin).status_code == 200
    assert client.get(URL.format(uuid.uuid4()), headers=off).status_code == 404
    assert client.get(URL.format(app_id) + "?visit=2", headers=off).status_code == 404
    # the operator's own view never carries the checklist
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert "checklist" not in mine and "items" not in mine


# The second-visit walk (approve path, Return to review, a second appointment, checklist visit 2, the
# first one readable with ?visit=1) needs the submit of US-063: with a draft on record the only exits
# from Site Visit Done are the submit and Reject. It lands with that story.
