"""The site visit checklist (US-060, FR-036, FR-037): the template, create-or-get under the row lock,
the draft save, the states that allow it, who may read and write, and the guard it closes."""

import concurrent.futures as cf
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.checklist_schema import ITEM_KEYS
from app.domain.enums import Role
from app.models import AuditEvent, Checklist, ChecklistItem, ClarificationRequest, Notification
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
    # the case view carries the summary; after the visit the only offered exits are the checklist's
    # own submit (not a transition) and Reject: there is no route straight to approval (US-063)
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
    assert {a["target"] for a in view["actions"]} == {"rejected"}


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


def _submit(client: TestClient, off: Headers, app_id: str):  # type: ignore[no-untyped-def]
    return client.post(URL.format(app_id) + "/submit", headers=off)


def test_submit_guards_freeze_audit_order_and_one_notification(client: TestClient, db: Session) -> None:
    """US-062 and US-063: every item assessed and every unsatisfactory or flagged item commented; from
    Site Visit Scheduled the officer hop is recorded first, then the system hop; findings frozen;
    round-1 requests released for the flagged items; one operator notification with the count."""
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    body = _open(client, off, app_id)
    r = _submit(client, off, app_id)
    assert r.status_code == 422 and len(r.json()["error"]["details"]["items"]) == 17
    items = _items(
        "satisfactory",
        floor_trap_graded={"result": "unsatisfactory", "comment": None},  # needs a comment
        coved_edges={"result": "satisfactory", "needs_clarification": True},  # flagged: needs a comment
        chiller_temperature={
            "result": "unsatisfactory",
            "comment": "Reads 7 °C.",
            "needs_clarification": True,
        },
    )
    client.put(URL.format(app_id), headers=off, json={"items": items, "version": body["version"]})
    r = _submit(client, off, app_id)
    assert r.status_code == 422, r.text
    fields = r.json()["error"]["details"]["fields"]
    assert set(fields) == {"floor_trap_graded", "coved_edges"} and "comment" in fields["coved_edges"]
    assert "2 items need attention" in r.json()["error"]["message"]
    items = _items(
        "satisfactory",
        floor_trap_graded={"result": "unsatisfactory", "comment": "Floor slopes away from the trap."},
        coved_edges={
            "result": "satisfactory",
            "comment": "Confirm the coving work.",
            "needs_clarification": True,
        },
        chiller_temperature={
            "result": "unsatisfactory",
            "comment": "Reads 7 °C.",
            "needs_clarification": True,
        },
        food_hygiene_officer={"result": "not_applicable"},
    )
    client.put(URL.format(app_id), headers=off, json={"items": items, "version": 2})
    before = db.scalars(select(Notification).where(Notification.user_id == _operator_id(db, op))).all()
    r = _submit(client, off, app_id)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "submitted" and out["submitted_by"] and out["submitted_at"]
    assert out["counts"]["flagged"] == 2 and out["counts"]["missing_comments"] == 0
    by_key = {i["key"]: i for i in out["items"]}
    assert by_key["coved_edges"]["clarification_status"] == "open"
    assert by_key["chiller_temperature"]["clarification_status"] == "open"
    assert by_key["floor_trap_graded"]["clarification_status"] == "none"
    # the case moved twice: the officer's hop then the system's, audited in that order after the submit
    view = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert view["status"] == "awaiting_post_site_clarification"
    assert view["checklist"]["status"] == "submitted"
    events = [
        (e.event_type, e.payload)
        for e in db.scalars(
            select(AuditEvent).where(AuditEvent.application_id == app_id).order_by(AuditEvent.created_at)
        )
    ]
    types = [t for t, _ in events]
    i = types.index("checklist.submitted")
    assert types[i - 1 : i + 2] == ["status.changed", "checklist.submitted", "status.changed"]
    assert events[i - 1][1]["to"] == "site_visit_done" and events[i - 1][1]["trigger"] == "officer"
    assert (
        events[i + 1][1]["to"] == "awaiting_post_site_clarification"
        and events[i + 1][1]["trigger"] == "system"
    )
    assert events[i][1]["flagged_keys"] == ["coved_edges", "chiller_temperature"]
    assert events[i][1]["unsatisfactory"] == 2 and events[i][1]["not_applicable"] == 1
    # round-1 requests exist, released, carrying the officer's comment
    reqs = list(db.scalars(select(ClarificationRequest)))
    assert len(reqs) == 2 and all(q.round_no == 1 and q.released_at is not None for q in reqs)
    assert {q.message for q in reqs} == {"Confirm the coving work.", "Reads 7 °C."}
    # exactly one new notification for the operator, with the count
    after = db.scalars(select(Notification).where(Notification.user_id == _operator_id(db, op))).all()
    new = [n for n in after if n.id not in {b.id for b in before}]
    assert len(new) == 1 and "needs more information on 2 items" in new[0].body
    assert "Pending Post-Site Clarification" in new[0].title
    # frozen: a save or a second submit is refused; the operator sentence names the count
    r = client.put(URL.format(app_id), headers=off, json={"items": items, "version": out["version"]})
    assert r.status_code == 409 and "no longer change" in r.json()["error"]["message"]
    assert _submit(client, off, app_id).status_code == 409
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["status_label"] == "Pending Post-Site Clarification"
    assert "needs more information on 2 items" in mine["status_explanation"]
    # the officer's route to approval waits for the items
    route = next(a for a in view["actions"] if a["target"] == "pending_approval")
    assert route["enabled"] is False
    # the site visit itself is done
    assert view["site_visit"]["status"] == "done"


def test_nothing_flagged_moves_on_and_a_second_visit_gets_its_own_checklist(
    client: TestClient, db: Session
) -> None:
    """No flag: the case still moves, the operator is told nothing is needed, the officer routes to
    approval; Return to review and a second appointment give visit 2 its own checklist while visit 1
    stays readable (the walk US-060 deferred to here)."""
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    first = _open(client, off, app_id)
    client.put(URL.format(app_id), headers=off, json={"items": _items(), "version": first["version"]})
    r = _submit(client, off, app_id)
    assert r.status_code == 200 and r.json()["counts"]["flagged"] == 0
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["status_explanation"].startswith("The site visit is recorded.")
    note = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert note is not None and "nothing is needed from you" in note.body
    view = transition(client, off, app_id, "pending_approval")
    assert view["status"] == "pending_approval"
    transition(client, off, app_id, "under_review")
    assert client.post(URL.format(app_id), headers=off).status_code == 409  # not in a site-visit state
    arrange_visit(client, off, op, app_id)  # visit 2
    r = client.post(URL.format(app_id), headers=off)
    assert r.status_code == 201, r.text
    second = r.json()
    assert second["visit_no"] == 2 and second["id"] != first["id"] and second["status"] == "draft"
    assert all(i["result"] == "not_assessed" for i in second["items"])
    r = client.get(URL.format(app_id) + "?visit=1", headers=off)
    assert r.status_code == 200 and r.json()["status"] == "submitted"
    assert client.get(URL.format(app_id), headers=off).json()["visit_no"] == 2
    row = next(
        i
        for i in client.get("/api/v1/officer/applications", headers=off).json()["items"]
        if i["id"] == app_id
    )
    assert row["next_action"] == "Continue the checklist"


def test_submit_authorization_and_wrong_state(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    assert _submit(client, off, app_id).status_code == 409  # under review
    arrange_visit(client, off, op, app_id)
    assert _submit(client, off, app_id).status_code == 404  # no checklist yet
    _open(client, off, app_id)
    assert client.post(URL.format(app_id) + "/submit", headers=op).status_code == 403
    make_user(db, "admin-cl2@example.sg", Role.ADMIN)
    admin = login(client, "admin-cl2@example.sg")
    assert client.post(URL.format(app_id) + "/submit", headers=admin).status_code == 403


def _operator_id(db: Session, op: Headers) -> uuid.UUID:
    from app.models import User

    user = db.scalar(select(User).where(User.email == "op@example.sg"))
    assert user is not None
    return user.id


def test_scheduled_again_before_a_new_date_does_not_reuse_the_done_visit(
    client: TestClient, db: Session
) -> None:
    """Return to review, Mark site visit scheduled through the transition, no new date proposed yet:
    the checklist of the done visit is not handed back; a fresh draft for visit 2 opens instead and the
    queue asks for a date."""
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    first = _open(client, off, app_id)
    client.put(URL.format(app_id), headers=off, json={"items": _items(), "version": first["version"]})
    assert _submit(client, off, app_id).status_code == 200
    transition(client, off, app_id, "pending_approval")
    transition(client, off, app_id, "under_review")
    transition(client, off, app_id, "site_visit_scheduled")  # the plain transition, no proposal yet
    r = client.post(URL.format(app_id), headers=off)
    assert r.status_code == 201 and r.json()["visit_no"] == 2 and r.json()["status"] == "draft", r.text
    row = next(
        i
        for i in client.get("/api/v1/officer/applications", headers=off).json()["items"]
        if i["id"] == app_id
    )
    assert row["next_action"] == "Propose a visit date"


def test_extra_findings_free_and_linked(client: TestClient, db: Session) -> None:
    """US-092: the officer adds a free finding and a second finding under a template item; both carry a
    result, a comment and the flag; the title is required; a removed one goes; they count and flow to
    the operator like any item."""
    app_id, op, off, _ = under_review(client, db)
    arrange_visit(client, off, op, app_id)
    body = _open(client, off, app_id)
    items = _items()
    items.append(
        {
            "key": None,
            "result": "unsatisfactory",
            "comment": "Loose tiles by the rear door.",
            "needs_clarification": True,
            "custom_title": "Loose floor tiles at the rear exit",
        }
    )
    items.append(
        {
            "key": None,
            "result": "unsatisfactory",
            "comment": "Second trap under the sink also blocked.",
            "needs_clarification": False,
            "custom_title": "Second floor trap blocked",
            "parent_key": "floor_trap_graded",
        }
    )
    r = client.put(URL.format(app_id), headers=off, json={"items": items, "version": body["version"]})
    assert r.status_code == 200, r.text
    saved = r.json()
    extras = [i for i in saved["items"] if i["is_extra"]]
    assert len(extras) == 2 and all(i["key"].startswith("extra_") for i in extras)
    free = next(i for i in extras if i["parent_key"] is None)
    linked = next(i for i in extras if i["parent_key"] == "floor_trap_graded")
    assert free["title"] == "Loose floor tiles at the rear exit" and free["section"] == "other"
    assert linked["title"] == "Second floor trap blocked" and linked["section"] == "premises"
    assert (
        saved["counts"]["total"] == 19
        and saved["counts"]["flagged"] == 1
        and saved["counts"]["unsatisfactory"] == 2
    )
    # the title is required; a parent must be a template item
    bad = _items() + [
        {
            "key": None,
            "result": "satisfactory",
            "comment": None,
            "needs_clarification": False,
            "custom_title": "  ",
        }
    ]
    r = client.put(URL.format(app_id), headers=off, json={"items": bad, "version": saved["version"]})
    assert r.status_code == 422 and "title" in str(r.json()["error"]["details"]["fields"])
    bad = _items() + [
        {
            "key": None,
            "result": "satisfactory",
            "comment": None,
            "needs_clarification": False,
            "custom_title": "x",
            "parent_key": "gold_taps",
        }
    ]
    r = client.put(URL.format(app_id), headers=off, json={"items": bad, "version": saved["version"]})
    assert r.status_code == 422
    # keep the linked one, rename it, drop the free one
    keep = _items() + [
        {
            "key": linked["key"],
            "result": "unsatisfactory",
            "comment": "Second trap under the sink also blocked.",
            "needs_clarification": True,
            "custom_title": "Second floor trap blocked (under the sink)",
            "parent_key": "floor_trap_graded",
        }
    ]
    r = client.put(URL.format(app_id), headers=off, json={"items": keep, "version": saved["version"]})
    assert r.status_code == 200, r.text
    extras = [i for i in r.json()["items"] if i["is_extra"]]
    assert (
        len(extras) == 1
        and extras[0]["title"] == "Second floor trap blocked (under the sink)"
        and r.json()["counts"]["total"] == 18
    )
    # submit: the flagged extra reaches the operator with its parent's title first
    r = _submit(client, off, app_id)
    assert r.status_code == 200, r.text
    mine = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert [i["title"] for i in mine["items"]] == [
        "Floor trap in the food preparation area: Second floor trap blocked (under the sink)"
    ]
    assert mine["items"][0]["requests"][0]["message"] == "Second trap under the sink also blocked."
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert case["clarification"]["items"][0]["title"].startswith("Floor trap in the food preparation area: ")
    from sqlalchemy import select

    from app.models import AuditEvent

    submitted = next(
        e
        for e in db.scalars(select(AuditEvent).where(AuditEvent.application_id == app_id))
        if e.event_type == "checklist.submitted"
    )
    assert submitted.payload["extra_titles"] == ["Second floor trap blocked (under the sink)"]
    # frozen: an extra cannot be added after submit
    r = client.put(URL.format(app_id), headers=off, json={"items": keep, "version": r.json()["version"]})
    assert r.status_code == 409
