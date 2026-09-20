from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification
from tests.journeys import arrange_visit, transition, under_review


def test_site_visit_to_approval_with_note(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    view = transition(client, off, app_id, "site_visit_scheduled")
    assert view["status_label"] == "Site Visit Scheduled"
    assert (
        client.get(f"/api/v1/applications/{app_id}", headers=op).json()["status_label"]
        == "Pending Site Visit"
    )
    # Marking the visit done needs a confirmed appointment (US-084); the reason names it.
    done = next(a for a in view["actions"] if a["target"] == "site_visit_done")
    assert done["enabled"] is False and "Confirm the visit date" in done["reason"]
    arrange_visit(client, off, op, app_id)
    view = transition(client, off, app_id, "site_visit_done")
    assert {a["target"] for a in view["actions"]} == {"pending_approval", "rejected"}
    view = transition(client, off, app_id, "pending_approval")
    assert view["status_label"] == "Route to Approval"
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["status_label"] == "Pending Approval" and mine["decision_note"] is None
    view = transition(client, off, app_id, "approved", note="Premises meet the hygiene requirements.")
    assert (
        view["status_label"] == "Approved"
        and view["decision_note"] == "Premises meet the hygiene requirements."
    )
    assert view["actions"] == []
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert (
        mine["status_label"] == "Approved"
        and mine["decision_note"] == "Premises meet the hygiene requirements."
    )
    assert mine["can_edit"] is False and mine["needs_operator_action"] is False
    last = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert last is not None and "Approved" in last.title and "hygiene" in last.body
    queue = client.get("/api/v1/officer/applications", headers=off).json()
    assert queue["decided_count"] == 1


def test_reject_needs_a_note_and_is_final(client: TestClient, db: Session) -> None:
    app_id, op, off, version = under_review(client, db)
    r = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "rejected", "expected_version": version},
    )
    assert r.status_code == 409 and r.json()["error"]["details"]["kind"] == "guard"
    view = transition(client, off, app_id, "rejected", note="Tenancy does not cover the licence period.")
    assert view["status_label"] == "Rejected" and view["actions"] == []
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["status_label"] == "Rejected" and "Tenancy" in mine["decision_note"]
    # Nothing can follow a decision.
    again = client.post(
        f"/api/v1/officer/applications/{app_id}/transition",
        headers=off,
        json={"target": "under_review", "expected_version": view["version"]},
    )
    assert again.status_code == 409


def test_return_to_review_from_pending_approval(client: TestClient, db: Session) -> None:
    """An officer who spots something at the decision step goes back instead of rejecting (US-031)."""
    app_id, op, off, _ = under_review(client, db)
    transition(client, off, app_id, "site_visit_scheduled")
    arrange_visit(client, off, op, app_id)
    transition(client, off, app_id, "site_visit_done")
    view = transition(client, off, app_id, "pending_approval")
    actions = {a["target"]: a["label"] for a in view["actions"]}
    assert actions == {"approved": "Approve", "under_review": "Return to review", "rejected": "Reject"}

    view = transition(client, off, app_id, "under_review")
    assert view["status_label"] == "Under Review"
    assert "pending_pre_site_resubmission" in {a["target"] for a in view["actions"]}
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert mine["status_label"] == "Under Review"
    last = db.scalars(select(Notification).order_by(Notification.created_at.desc())).first()
    assert last is not None and "Under Review" in last.title
