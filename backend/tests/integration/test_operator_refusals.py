"""An operator's refused action is explained in the operator's own words (FR-026, ADR-005): no internal
status code, no officer-only label and no `allowed` list of internal targets in any 409 body."""

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.enums import ApplicationStatus
from app.domain.labels import officer_label, operator_label
from tests.journeys import to_pending_approval, transition, under_review

# Codes that are also the operator's own word for the state ("draft", "approved") are plain English; the
# ones with an underscore are internal by construction and must never appear.
INTERNAL_CODES = [s.value for s in ApplicationStatus if s.value != operator_label(s).lower()]
OFFICER_ONLY = [officer_label(s) for s in ApplicationStatus if officer_label(s) != operator_label(s)]


def _assert_operator_safe(body: dict) -> None:  # type: ignore[type-arg]
    text = json.dumps(body)
    assert "allowed" not in body["error"].get("details", {}), body
    for code in INTERNAL_CODES:
        assert code not in text, f"internal code {code!r} in operator body: {text}"
    for label in OFFICER_ONLY:
        assert label not in text, f"officer label {label!r} in operator body: {text}"


def test_refused_operator_actions_carry_no_internal_status(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    to_pending_approval(client, off, op, app_id)

    r = client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op)
    assert r.status_code == 409, r.text
    _assert_operator_safe(r.json())
    assert r.json()["error"]["message"] == (
        "This application is Pending Approval. "
        "A resubmission is only possible while the office is waiting for your changes."
    )

    r = client.post(f"/api/v1/applications/{app_id}/submit", headers=op)
    assert r.status_code == 409, r.text
    _assert_operator_safe(r.json())
    assert (
        r.json()["error"]["message"] == "This application is Pending Approval. Only a draft can be submitted."
    )

    transition(client, off, app_id, "approved", note="ok")
    r = client.post(f"/api/v1/applications/{app_id}/withdraw", headers=op, json={})
    assert r.status_code == 409, r.text
    _assert_operator_safe(r.json())
    assert r.json()["error"]["message"] == "A decided application cannot be withdrawn."
