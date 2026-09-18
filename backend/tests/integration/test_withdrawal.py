"""US-038: the owner withdraws a submitted application; officers are told; nothing can follow."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Notification
from app.models.enums import Role
from tests.factories import login, make_user
from tests.journeys import draft, flag_and_request, submitted, transition, under_review


def _withdraw(client: TestClient, h: dict[str, str], app_id: str, reason: str | None = None) -> object:
    return client.post(f"/api/v1/applications/{app_id}/withdraw", headers=h, json={"reason": reason})


def test_owner_withdraws_after_submission_with_reason(client: TestClient, db: Session) -> None:
    app_id, op, off = submitted(client, db)
    before = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert before["can_withdraw"] is True and before["withdrawal_reason"] is None

    r = _withdraw(client, op, app_id, "  We are not opening the outlet after all.  ")
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["status_label"] == "Withdrawn" and view["status_tone"] == "neutral"
    assert view["withdrawal_reason"] == "We are not opening the outlet after all."
    assert view["can_withdraw"] is False and view["can_edit"] is False
    assert view["needs_operator_action"] is False and view["decision_note"] is None
    assert "withdrew" in view["status_explanation"]

    # audit: the operator is the actor of the status change
    events = db.scalars(select(AuditEvent).where(AuditEvent.application_id == app_id)).all()
    change = [e for e in events if e.event_type == "status.changed" and e.payload["to"] == "withdrawn"]
    assert len(change) == 1
    assert change[0].payload == {
        "from": "application_received",
        "to": "withdrawn",
        "trigger": "operator",
        "has_note": True,
    }
    trail = client.get(f"/api/v1/officer/applications/{app_id}/audit", headers=off).json()["events"]
    assert any("Withdrawn" in e["summary"] and e["actor_role"] == "operator" for e in trail)

    # officers are notified with the reason
    last = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert last is not None and last.title.endswith("Withdrawn") and "not opening" in last.body

    # the officer sees it as decided with no actions and the reason on the case
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    assert case["status"] == "withdrawn" and case["status_label"] == "Withdrawn"
    assert case["actions"] == [] and case["withdrawal_reason"] == "We are not opening the outlet after all."
    queue = client.get("/api/v1/officer/applications", headers=off).json()
    row = next(i for i in queue["items"] if i["id"] == app_id)
    assert row["decided"] is True and row["next_action"] == "View" and queue["decided_count"] == 1


def test_withdraw_while_feedback_is_pending_and_without_reason(client: TestClient, db: Session) -> None:
    app_id, op, off = flag_and_request(client, db)
    r = _withdraw(client, op, app_id)
    assert r.status_code == 200, r.text
    assert r.json()["withdrawal_reason"] is None
    last = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert last is not None and "No reason was given" in last.body
    # editing a previously flagged section is closed now
    r = client.patch(
        f"/api/v1/applications/{app_id}/sections/premises", headers=op, json={"address_line_1": "x"}
    )
    assert r.status_code == 403
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 409


def test_withdrawn_is_terminal_for_officers_too(client: TestClient, db: Session) -> None:
    app_id, op, off, version = under_review(client, db)
    assert _withdraw(client, op, app_id).status_code == 200
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "rejected", "note": "x", "expected_version": version + 1},
    )
    assert r.status_code == 409
    assert r.json()["error"]["details"]["allowed"] == []
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/feedback",
        headers=off,
        json={"target_type": "section", "section_key": "premises", "message": "late"},
    )
    assert r.status_code == 409
    # withdrawing twice is a 409, not a silent success
    assert _withdraw(client, op, app_id).status_code == 409


def test_draft_cannot_be_withdrawn(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = draft(client, op)
    r = _withdraw(client, op, app_id)
    assert r.status_code == 409 and "draft" in r.json()["error"]["message"].lower()
    assert client.get(f"/api/v1/applications/{app_id}", headers=op).json()["can_withdraw"] is False


def test_decided_cannot_be_withdrawn(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    transition(client, off, app_id, "rejected", note="Ineligible.")
    r = _withdraw(client, op, app_id)
    assert r.status_code == 409 and "decided" in r.json()["error"]["message"].lower()


def test_only_the_owner_can_withdraw(client: TestClient, db: Session) -> None:
    app_id, op, off = submitted(client, db)
    make_user(db, "other@example.sg", Role.OPERATOR)
    make_user(db, "admin@example.sg", Role.ADMIN)
    assert _withdraw(client, login(client, "other@example.sg"), app_id).status_code == 404
    assert _withdraw(client, off, app_id).status_code == 403
    assert _withdraw(client, login(client, "admin@example.sg"), app_id).status_code == 403
    assert _withdraw(client, op, app_id, "x" * 1001).status_code == 422
    assert client.get(f"/api/v1/applications/{app_id}", headers=op).json()["status_label"] == "Submitted"
