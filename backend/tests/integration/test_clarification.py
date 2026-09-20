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


# US-065: responses, attachments, send -----------------------------------------------------------

from tests.journeys import PDF  # noqa: E402


def _respond(client: TestClient, op: Headers, app_id: str, item_id: str, text: str):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/applications/{app_id}/clarifications/{item_id}/responses",
        headers=op,
        json={"message": text},
    )


def _attach(
    client: TestClient,
    op: Headers,
    app_id: str,
    response_id: str,
    name: str,
    content: bytes,
    mime: str = "application/pdf",
):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/applications/{app_id}/clarifications/responses/{response_id}/attachments",
        headers=op,
        files={"file": (name, content, mime)},
    )


def test_respond_attach_and_send_move_the_case(client: TestClient, db: Session) -> None:
    from sqlalchemy import select

    from app.models import AuditEvent, Notification

    app_id, op, off = _submitted(client, db)
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    items = {i["key"]: i for i in view["items"]}
    # send before answering: 422 naming the three keys
    r = client.post(f"/api/v1/applications/{app_id}/clarifications/send", headers=op)
    assert r.status_code == 422 and sorted(r.json()["error"]["details"]["items"]) == sorted(FLAGGED)
    # an empty or over-long answer is refused
    assert _respond(client, op, app_id, items["coved_edges"]["item_id"], "   ").status_code == 422
    assert _respond(client, op, app_id, items["coved_edges"]["item_id"], "x" * 2001).status_code == 422
    # draft, then rewrite
    r = _respond(client, op, app_id, items["coved_edges"]["item_id"], "Coving done on 24 Sep.")
    assert r.status_code == 200, r.text
    r = _respond(
        client, op, app_id, items["coved_edges"]["item_id"], "Coving done on 24 Sep; photo attached."
    )
    assert r.status_code == 200
    coved = next(i for i in r.json()["items"] if i["key"] == "coved_edges")
    assert len(coved["responses"]) == 1 and coved["responses"][0]["message"].endswith("photo attached.")
    assert coved["responses"][0]["sent_at"] is None and coved["status"] == "Waiting for your response"
    response_id = coved["responses"][0]["id"]
    # attachments: the document rules, three at most, an identical file is no change, removable
    r = _attach(client, op, app_id, response_id, "coving.pdf", PDF)
    assert r.status_code == 201 and r.json()["unchanged"] is False, r.text
    att_id = next(i for i in r.json()["view"]["items"] if i["key"] == "coved_edges")["responses"][0][
        "attachments"
    ][0]["id"]
    r = _attach(client, op, app_id, response_id, "coving-copy.pdf", PDF)
    assert r.status_code == 201 and r.json()["unchanged"] is True
    assert (
        _attach(
            client, op, app_id, response_id, "notes.exe", b"MZ" + b"x" * 40, "application/octet-stream"
        ).status_code
        == 400
    )
    assert _attach(client, op, app_id, response_id, "fake.pdf", b"GIF89a" + b"x" * 40).status_code == 400
    assert _attach(client, op, app_id, response_id, "empty.pdf", b"").status_code == 400
    assert _attach(client, op, app_id, response_id, "second.pdf", PDF + b"2").status_code == 201
    assert _attach(client, op, app_id, response_id, "third.pdf", PDF + b"3").status_code == 201
    r = _attach(client, op, app_id, response_id, "fourth.pdf", PDF + b"4")
    assert r.status_code == 422 and r.json()["error"]["details"]["reason"] == "attachment_cap"
    r = client.get(f"/api/v1/applications/{app_id}/clarifications/attachments/{att_id}/download", headers=op)
    assert r.status_code == 200 and r.content == PDF and "coving.pdf" in r.headers["content-disposition"]
    assert (
        client.get(
            f"/api/v1/applications/{app_id}/clarifications/attachments/{att_id}/download", headers=off
        ).status_code
        == 200
    )
    r = client.delete(
        f"/api/v1/applications/{app_id}/clarifications/responses/{response_id}/attachments/{att_id}",
        headers=op,
    )
    assert r.status_code == 200
    assert (
        client.get(
            f"/api/v1/applications/{app_id}/clarifications/attachments/{att_id}/download", headers=op
        ).status_code
        == 404
    )
    # the other two items, then send
    _respond(client, op, app_id, items["floor_trap_graded"]["item_id"], "Regraded on 23 Sep.")
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert view["can_send"] is False
    _respond(client, op, app_id, items["chiller_temperature"]["item_id"], "Serviced; now 3 °C.")
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert view["can_send"] is True
    officer_notes_before = len(db.scalars(select(Notification)).all())
    r = client.post(f"/api/v1/applications/{app_id}/clarifications/send", headers=op)
    assert r.status_code == 200, r.text
    sent = r.json()
    assert sent["open_count"] == 0 and sent["answered_count"] == 3 and sent["can_send"] is False
    assert all(i["status"] == "Sent" and i["responses"][0]["sent_at"] for i in sent["items"])
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["status_label"] == "Post-Site Resubmitted" and mine["needs_operator_action"] is False
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert case["status"] == "post_site_clarification_resubmitted"
    events = [
        e.event_type
        for e in db.scalars(
            select(AuditEvent).where(AuditEvent.application_id == app_id).order_by(AuditEvent.created_at)
        )
    ]
    assert events.count("clarification.answered") == 3 and events[-1] == "status.changed"
    assert events.index("clarification.answered") < events.index(
        "status.changed", events.index("clarification.answered")
    )
    assert len(db.scalars(select(Notification)).all()) > officer_notes_before
    # sent: no rewrite, no more files, no second send
    assert _respond(client, op, app_id, items["coved_edges"]["item_id"], "again").status_code == 409
    assert _attach(client, op, app_id, response_id, "late.pdf", PDF + b"late").status_code == 409
    assert client.post(f"/api/v1/applications/{app_id}/clarifications/send", headers=op).status_code == 409


def test_withdrawn_before_send_is_left_out_and_idor_is_404(client: TestClient, db: Session) -> None:
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models import ChecklistItem, ClarificationRequest

    app_id, op, off = _submitted(client, db)
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    items = {i["key"]: i for i in view["items"]}
    for key in ("floor_trap_graded", "coved_edges"):
        assert _respond(client, op, app_id, items[key]["item_id"], f"About {key}.").status_code == 200
    # the officer withdraws the third question before the send (US-066 does this through a route)
    chiller = db.scalar(select(ChecklistItem).where(ChecklistItem.item_key == "chiller_temperature"))
    assert chiller is not None
    q = db.scalar(select(ClarificationRequest).where(ClarificationRequest.item_id == chiller.id))
    assert q is not None
    q.withdrawn_at = datetime.now(UTC)
    from app.domain.enums import ClarificationStatus

    chiller.clarification_status = ClarificationStatus.WITHDRAWN
    db.commit()
    r = client.post(f"/api/v1/applications/{app_id}/clarifications/send", headers=op)
    assert r.status_code == 200, r.text
    assert r.json()["answered_count"] == 2 and "chiller_temperature" not in [
        i["key"] for i in r.json()["items"]
    ]
    # another operator, another application, an officer on the operator routes
    from tests.factories import login, make_user

    make_user(db, "other-cl2@example.sg", Role.OPERATOR)
    other = login(client, "other-cl2@example.sg")
    coved = items["coved_edges"]
    assert _respond(client, other, app_id, coved["item_id"], "mine").status_code == 404
    other_app, other_op, _, _ = under_review(client, db) if False else (None, None, None, None)
    assert client.post(f"/api/v1/applications/{app_id}/clarifications/send", headers=off).status_code == 403
    assert (
        client.get(
            f"/api/v1/applications/{uuid.uuid4()}/clarifications/attachments/{uuid.uuid4()}/download",
            headers=op,
        ).status_code
        == 404
    )


# US-066: rounds -----------------------------------------------------------------------------------

OFF_URL = "/api/v1/officer/applications/{}/clarifications/{}/{}"


def _answer_all(client: TestClient, op: Headers, app_id: str, text: str = "Done.") -> dict:  # type: ignore[type-arg]
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    for i in view["items"]:
        if i["status"] == "Waiting for your response":
            assert _respond(client, op, app_id, i["item_id"], f"{text} ({i['key']})").status_code == 200
    r = client.post(f"/api/v1/applications/{app_id}/clarifications/send", headers=op)
    assert r.status_code == 200, r.text
    return r.json()


def test_two_rounds_resolve_reopen_withdraw_and_route_to_approval(client: TestClient, db: Session) -> None:
    from sqlalchemy import select

    from app.models import AuditEvent, Notification

    app_id, op, off = _submitted(client, db)
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert (
        case["clarification"]["turn"] == "Round 1, waiting on operator"
        and case["clarification"]["open_count"] == 3
    )
    threads = {t["key"]: t for t in case["clarification"]["items"]}
    # the officer's own finding sits on each thread; nothing can be decided before the answers
    assert threads["coved_edges"]["result"] == "unsatisfactory" and threads["coved_edges"]["comment"]
    assert threads["coved_edges"]["can_resolve"] is False and threads["coved_edges"]["can_withdraw"] is True
    r = client.post(OFF_URL.format(app_id, threads["coved_edges"]["item_id"], "resolve"), headers=off)
    assert r.status_code == 409
    _answer_all(client, op, app_id)
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert case["status"] == "post_site_clarification_resubmitted"
    assert (
        case["clarification"]["turn"] == "Round 1, your turn" and case["clarification"]["answered_count"] == 3
    )
    threads = {t["key"]: t for t in case["clarification"]["items"]}
    assert threads["coved_edges"]["requests"][0]["response"]["message"].startswith("Done.")
    actions = {a["target"]: a for a in case["actions"]}
    assert (
        actions["pending_approval"]["enabled"] is False
        and "clarified" in actions["pending_approval"]["reason"]
    )
    assert actions["pending_post_site_resubmission"]["enabled"] is False
    # mark one clarified, ask again on another, withdraw is not possible on an answered item
    r = client.post(OFF_URL.format(app_id, threads["coved_edges"]["item_id"], "resolve"), headers=off)
    assert r.status_code == 200, r.text
    r = client.post(OFF_URL.format(app_id, threads["floor_trap_graded"]["item_id"], "withdraw"), headers=off)
    assert r.status_code == 409
    r = client.post(
        OFF_URL.format(app_id, threads["floor_trap_graded"]["item_id"], "reopen"),
        headers=off,
        json={"message": "Please send a photo once the floor is regraded."},
    )
    assert r.status_code == 200, r.text
    view = r.json()["clarification"]
    trap = next(t for t in view["items"] if t["key"] == "floor_trap_graded")
    assert trap["status"] == "open" and trap["pending_release"] is True and trap["round_no"] == 2
    assert trap["requests"][1]["released_at"] is None and trap["can_withdraw"] is True
    assert view["unreleased_count"] == 1
    # the operator does not see the drafted round-2 question yet
    mine = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert "regraded" not in str(mine) and mine["can_respond"] is False
    # Route to approval still refused (one open, one answered); Request another round is on
    actions = {a["target"]: a for a in r.json()["actions"]}
    assert actions["pending_post_site_resubmission"]["enabled"] is True
    assert actions["pending_approval"]["enabled"] is False
    # the third item: mark clarified too
    r = client.post(OFF_URL.format(app_id, threads["chiller_temperature"]["item_id"], "resolve"), headers=off)
    assert r.status_code == 200
    # Request another round releases the drafted question and tells the operator
    from tests.journeys import transition

    view = transition(client, off, app_id, "pending_post_site_resubmission")
    assert view["status"] == "pending_post_site_resubmission"
    assert (
        view["clarification"]["turn"] == "Round 2, waiting on operator"
        and view["clarification"]["unreleased_count"] == 0
    )
    note = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert note is not None and "needs more information on 1 item after your answers" in note.body
    mine = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert mine["round"] == 2 and mine["open_count"] == 1 and mine["can_respond"] is True
    trap = next(i for i in mine["items"] if i["key"] == "floor_trap_graded")
    assert [q["round_no"] for q in trap["requests"]] == [1, 2] and trap["requests"][1]["message"].startswith(
        "Please send"
    )
    assert next(i for i in mine["items"] if i["key"] == "coved_edges")["status"] == "Clarified"
    listed = next(a for a in client.get("/api/v1/applications", headers=op).json() if a["id"] == app_id)
    assert (
        listed["needs_operator_action"] is True and listed["status_label"] == "Pending Post-Site Resubmission"
    )
    # round 2 answered and sent; the officer resolves; Route to approval opens
    _answer_all(client, op, app_id, "Photo attached")
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert case["clarification"]["turn"] == "Round 2, your turn"
    trap = next(t for t in case["clarification"]["items"] if t["key"] == "floor_trap_graded")
    assert trap["requests"][1]["response"]["message"].startswith("Photo attached")
    r = client.post(OFF_URL.format(app_id, trap["item_id"], "resolve"), headers=off)
    assert r.status_code == 200
    actions = {a["target"]: a for a in r.json()["actions"]}
    assert actions["pending_approval"]["enabled"] is True
    view = transition(client, off, app_id, "pending_approval")
    assert view["status"] == "pending_approval"
    kinds = [
        e.event_type
        for e in db.scalars(
            select(AuditEvent).where(AuditEvent.application_id == app_id).order_by(AuditEvent.created_at)
        )
    ]
    for k in (
        "clarification.resolved",
        "clarification.reopened",
        "clarification.released",
        "clarification.answered",
    ):
        assert k in kinds
    assert kinds.index("clarification.reopened") < kinds.index("clarification.released")


def test_five_rounds_lose_nothing(client: TestClient, db: Session) -> None:
    from tests.journeys import transition

    app_id, op, off = _submitted(client, db)
    threads = {
        t["key"]: t
        for t in client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()["clarification"][
            "items"
        ]
    }
    trap = threads["floor_trap_graded"]["item_id"]
    _answer_all(client, op, app_id, "Round 1 answer")
    # two items done at once; one item goes five rounds
    for key in ("coved_edges", "chiller_temperature"):
        assert (
            client.post(OFF_URL.format(app_id, threads[key]["item_id"], "resolve"), headers=off).status_code
            == 200
        )
    for n in range(2, 6):
        r = client.post(
            OFF_URL.format(app_id, trap, "reopen"), headers=off, json={"message": f"Question {n}"}
        )
        assert r.status_code == 200, r.text
        transition(client, off, app_id, "pending_post_site_resubmission")
        _answer_all(client, op, app_id, f"Answer {n}")
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    thread = next(t for t in case["clarification"]["items"] if t["key"] == "floor_trap_graded")
    assert [q["round_no"] for q in thread["requests"]] == [1, 2, 3, 4, 5]
    assert [q["response"]["message"].split(" (")[0] for q in thread["requests"]] == [
        "Round 1 answer",
        "Answer 2",
        "Answer 3",
        "Answer 4",
        "Answer 5",
    ]
    assert case["clarification"]["turn"] == "Round 5, your turn"
    mine = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    mine_trap = next(i for i in mine["items"] if i["key"] == "floor_trap_graded")
    assert len(mine_trap["requests"]) == 5 and len(mine_trap["responses"]) == 5
    assert client.post(OFF_URL.format(app_id, trap, "resolve"), headers=off).status_code == 200
    assert transition(client, off, app_id, "pending_approval")["status"] == "pending_approval"


def test_withdraw_racing_a_send_has_one_outcome(client: TestClient, db: Session) -> None:
    """The officer withdraws a question while the operator sends: both lock the application row, so
    the send either sees the withdrawal (and leaves the item out) or lands first (and the withdraw is
    refused because the item is answered). Never a half state."""
    import concurrent.futures as cf

    app_id, op, off = _submitted(client, db)
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    items = {i["key"]: i for i in view["items"]}
    for i in view["items"]:
        _respond(client, op, app_id, i["item_id"], "Answer.")
    chiller = items["chiller_temperature"]["item_id"]
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        send = pool.submit(client.post, f"/api/v1/applications/{app_id}/clarifications/send", headers=op)
        wd = pool.submit(client.post, OFF_URL.format(app_id, chiller, "withdraw"), headers=off)
        s, w = send.result(), wd.result()
    assert s.status_code == 200, s.text
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    thread = next(t for t in case["clarification"]["items"] if t["key"] == "chiller_temperature")
    if w.status_code == 200:
        assert thread["status"] == "withdrawn" and case["clarification"]["answered_count"] == 2
    else:
        assert (
            w.status_code == 409
            and thread["status"] == "answered"
            and case["clarification"]["answered_count"] == 3
        )


def test_reject_mid_round_keeps_the_trail(client: TestClient, db: Session) -> None:
    from tests.journeys import transition

    app_id, op, off = _submitted(client, db)
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    _respond(client, op, app_id, view["items"][0]["item_id"], "Draft never sent.")
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={
            "target": "rejected",
            "note": "Premises unsafe.",
            "expected_version": client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()[
                "version"
            ],
        },
    )
    assert r.status_code == 200, r.text
    case = r.json()
    assert case["status"] == "rejected" and case["clarification"] is not None
    assert case["clarification"]["open_count"] == 3  # the questions stay as they were
    mine = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    assert mine["can_respond"] is False and mine["items"][0]["responses"][0]["sent_at"] is None
    assert _respond(client, op, app_id, view["items"][0]["item_id"], "Too late.").status_code == 409
    assert transition  # the helper import is used above; keep the walk readable


def test_no_evidence_on_a_withdrawn_or_decided_item(client: TestClient, db: Session) -> None:
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.domain.enums import ClarificationStatus
    from app.models import ChecklistItem, ClarificationRequest

    app_id, op, off = _submitted(client, db)
    view = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    coved = next(i for i in view["items"] if i["key"] == "coved_edges")
    r = _respond(client, op, app_id, coved["item_id"], "Coving done.")
    response_id = next(i for i in r.json()["items"] if i["key"] == "coved_edges")["responses"][0]["id"]
    assert _attach(client, op, app_id, response_id, "before.pdf", PDF).status_code == 201
    att = client.get(f"/api/v1/applications/{app_id}/clarifications", headers=op).json()
    att_id = next(i for i in att["items"] if i["key"] == "coved_edges")["responses"][0]["attachments"][0][
        "id"
    ]
    item = db.scalar(select(ChecklistItem).where(ChecklistItem.item_key == "coved_edges"))
    assert item is not None
    q = db.scalar(select(ClarificationRequest).where(ClarificationRequest.item_id == item.id))
    assert q is not None
    q.withdrawn_at = datetime.now(UTC)
    item.clarification_status = ClarificationStatus.WITHDRAWN
    db.commit()
    assert _attach(client, op, app_id, response_id, "after.pdf", PDF + b"after").status_code == 409
    r = client.delete(
        f"/api/v1/applications/{app_id}/clarifications/responses/{response_id}/attachments/{att_id}",
        headers=op,
    )
    assert r.status_code == 409
