import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.journeys import VALID_PREMISES, flag_and_request, transition


def test_audit_trail_covers_the_whole_journey_in_order(client: TestClient, db: Session) -> None:
    app_id, op, off = flag_and_request(client, db)
    premises = dict(VALID_PREMISES)
    premises["address_line_1"] = "10 Jalan Besar #01-21"
    assert (
        client.patch(
            f"/api/v1/applications/{app_id}/sections/premises", headers=op, json=premises
        ).status_code
        == 200
    )
    r = client.post(
        f"/api/v1/applications/{app_id}/documents",
        headers=op,
        data={"document_type": "floor_plan"},
        files={"file": ("plan2.txt", io.BytesIO(b"Floor plan kitchen preparation area " * 10), "text/plain")},
    )
    assert r.status_code == 201
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 200
    transition(client, off, app_id, "under_review")
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    fid = case["feedback"][0]["id"]
    assert (
        client.post(f"/api/v1/officer/applications/{app_id}/feedback/{fid}/resolve", headers=off).status_code
        == 200
    )

    r = client.get(f"/api/v1/officer/applications/{app_id}/audit", headers=off)
    assert r.status_code == 200, r.text
    events = r.json()["events"]
    types = [e["event_type"] for e in events]
    # Chronological, and every family of event is present.
    assert types[0] == "application.created"
    for expected in (
        "section.updated",
        "document.uploaded",
        "verification.completed",
        "revision.submitted",
        "status.changed",
        "feedback.created",
        "feedback.released",
        "document.replaced",
        "feedback.addressed",
        "feedback.resolved",
    ):
        assert expected in types, expected
    assert (
        types.index("feedback.created") < types.index("feedback.released") < types.index("feedback.addressed")
    )
    assert types.index("feedback.addressed") < types.index("feedback.resolved")
    created = [e["created_at"] for e in events]
    assert created == sorted(created)
    # Actors and summaries are human: the operator on submit, the officer on status changes.
    submit = next(e for e in events if e["event_type"] == "revision.submitted")
    assert submit["actor_role"] == "operator" and submit["summary"] == "Revision 1 submitted"
    review = next(
        e for e in events if e["event_type"] == "status.changed" and e["payload"]["to"] == "under_review"
    )
    assert (
        review["actor_role"] == "officer"
        and review["summary"] == "Status: Application Received → Under Review"
    )
    resub = [e for e in events if e["event_type"] == "revision.submitted"][1]
    assert resub["summary"] == "Revision 2 resubmitted (2 targets changed)"
    check = next(e for e in events if e["event_type"] == "verification.completed")
    assert check["actor_name"] is None  # system event
    # Officer-only; operators get 403 (their history is the operator view).
    assert client.get(f"/api/v1/officer/applications/{app_id}/audit", headers=op).status_code == 403
    mine = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    assert [r["number"] for r in mine["revisions"]] == [1, 2]
