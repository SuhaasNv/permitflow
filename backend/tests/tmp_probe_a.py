"""Throwaway probes. Run from backend dir with --rootdir=."""
import io
import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Feedback, VerificationRun, Document
from app.models.enums import Role, VerificationStatus
from tests.factories import login, make_user
from tests.journeys import (
    VALID_PREMISES, TXT, add_feedback, complete_draft, flag_and_request, submitted, transition, under_review, upload,
)


def _fb(app_id, fid, action):
    return f"/api/v1/officer/applications/{app_id}/feedback/{fid}/{action}"


def test_p1_restore_after_site_visit_scheduled_reopens_feedback(client: TestClient, db: Session) -> None:
    """Round 1: two items released. Operator addresses only premises. Round 2 under_review: floor_plan item is
    still open+released. Officer resolves it (allowed), schedules site visit (guard: 0 open), then undoes the
    resolve within 15 s -> open item in site_visit_scheduled."""
    app_id, op, off = flag_and_request(client, db)
    r = client.patch(f"/api/v1/applications/{app_id}/sections/premises", headers=op,
                     json={**VALID_PREMISES, "address_line_1": "10 Jalan Besar #01-21"})
    assert r.status_code == 200, r.text
    assert client.post(f"/api/v1/applications/{app_id}/resubmit", headers=op).status_code == 200
    transition(client, off, app_id, "under_review")
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    open_items = [f for f in case["feedback"] if f["resolution"] == "open"]
    assert len(open_items) == 1 and open_items[0]["document_type"] == "floor_plan"
    fid = open_items[0]["id"]
    # resolve the leftover open item
    assert client.post(_fb(app_id, fid, "resolve"), headers=off).status_code == 200
    # guard now passes
    view = transition(client, off, app_id, "site_visit_scheduled")
    assert view["status"] == "site_visit_scheduled"
    # undo within the window
    r = client.post(_fb(app_id, fid, "restore"), headers=off)
    print("restore status", r.status_code, r.text[:200])
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    print("status", case["status"], "open_feedback_count", case["open_feedback_count"])
    # Expected by the state machine: no open feedback in site_visit_scheduled
    assert not (case["status"] == "site_visit_scheduled" and case["open_feedback_count"] > 0), "BUG: open feedback in site_visit_scheduled via undo"


def test_p2_txt_multibyte_boundary(client: TestClient, db: Session) -> None:
    make_user(db, "op@example.sg", Role.OPERATOR)
    op = login(client, "op@example.sg")
    app_id = client.post("/api/v1/applications", headers=op).json()["id"]
    data = ("A" * 15 + "é " + "Tenancy agreement between landlord and tenant. " * 5).encode("utf-8")
    r = upload(client, op, app_id, "tenancy_agreement", "lease.txt", data, "text/plain")
    print("multibyte txt upload:", r.status_code, r.text[:200])
    assert r.status_code == 201, "BUG: valid UTF-8 text rejected"


def test_p3_operator_rerun_after_submission(client: TestClient, db: Session) -> None:
    app_id, op, off = submitted(client, db)
    view = client.get(f"/api/v1/applications/{app_id}", headers=op).json()
    doc_id = view["document_slots"][0]["document"]["id"]
    r = client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/verify", headers=op)
    print("operator rerun on submitted app:", r.status_code)
    transition(client, off, app_id, "under_review")
    r2 = client.post(f"/api/v1/applications/{app_id}/documents/{doc_id}/verify", headers=op)
    print("operator rerun under_review:", r2.status_code)
    runs = list(db.scalars(select(VerificationRun).where(VerificationRun.document_id == uuid.UUID(doc_id))))
    print("runs for doc:", len(runs))
    assert r2.status_code == 202  # documents the behaviour


def test_p4_officer_sees_unsubmitted_working_copy_doc(client: TestClient, db: Session) -> None:
    app_id, op, off = flag_and_request(client, db)
    new = ("Floor plan kitchen layout sqm. " * 10).encode()
    r = upload(client, op, app_id, "floor_plan", "new_plan.txt", new, "text/plain")
    assert r.status_code == 201, r.text
    new_doc_id = r.json()["document"]["id"]
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    fp = next(d for d in case["documents"] if d["document_type"] == "floor_plan")
    print("officer sees doc id", fp["id"], "new id", new_doc_id, "in_current_revision", fp["in_current_revision"])
    dl = client.get(f"/api/v1/applications/{app_id}/documents/{new_doc_id}/download", headers=off)
    print("officer download of unsubmitted doc:", dl.status_code)
    assert fp["id"] != new_doc_id, "officer case view shows the working-copy document, not the revision's"


def test_p5_queue_vs_detail_business_name(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    add_feedback(client, off, app_id, target_type="section", section_key="business", message="Fix name.")
    transition(client, off, app_id, "pending_pre_site_resubmission")
    from tests.journeys import VALID_BUSINESS
    r = client.patch(f"/api/v1/applications/{app_id}/sections/business", headers=op,
                     json={**VALID_BUSINESS, "business_name": "UNSUBMITTED NAME"})
    assert r.status_code == 200, r.text
    q = client.get("/api/v1/officer/applications", headers=off).json()["items"][0]
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    print("queue name:", q["business_name"], "| detail name:", case["business_name"])
    assert q["business_name"] == case["business_name"], "queue shows working copy, detail shows revision"


def test_p6_system_transition_by_officer_status_code(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    transition(client, off, app_id, "site_visit_scheduled")
    transition(client, off, app_id, "site_visit_done")
    case = client.get(f"/api/v1/officer/applications/{app_id}", headers=off).json()
    r = client.post(f"/api/v1/officer/applications/{app_id}/transition", headers=off,
                    json={"target": "awaiting_post_site_clarification", "expected_version": case["version"]})
    print("system-actor edge by officer:", r.status_code, r.json())
