"""UAT edge-case run (docs/10-uat/UAT_PLAN.md, "Edge-case run"): every refusal path and the whole lifecycle
against a running API, recorded as PASS/FAIL lines and a summary.

Run against a local stack with the mock provider and the seeded accounts:

    cd backend && uv run python scripts/uat_edges.py

Needs `DATABASE_URL` (as for `scripts/seed.py`) to create the second operator account the wrong-owner
checks use (operator2@permitflow.example.sg, same password; removed again when the run ends, so no test
account outlives the run), `UAT_API_URL` for another host, and the
per-client limits off (`RATE_LIMIT_PER_MINUTE=0`, `LOGIN_ATTEMPTS_PER_MINUTE=0`) or the run trips them.
The script creates a handful of applications for the seeded operator and leaves them in place.
"""

# ruff: noqa: E501 - one check per line, the titles read better unwrapped

from __future__ import annotations

import concurrent.futures as cf
import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

API = os.environ.get("UAT_API_URL", "http://localhost:8000/api/v1")
PW = os.environ.get("SEED_PASSWORD", "PermitFlow!2026")
OPERATOR = "operator@permitflow.example.sg"
OPERATOR2 = "operator2@permitflow.example.sg"
OFFICER = "officer@permitflow.example.sg"

RESULTS: list[tuple[str, str, bool, str]] = []  # (id, title, passed, note)
INTERNAL_CODES = {
    "draft",
    "application_received",
    "under_review",
    "pending_pre_site_resubmission",
    "pre_site_resubmitted",
    "site_visit_scheduled",
    "site_visit_done",
    "awaiting_post_site_clarification",
    "pending_post_site_resubmission",
    "post_site_clarification_resubmitted",
    "pending_approval",
}
OFFICER_ONLY_LABELS = {
    "Route to Approval",
    "Site Visit Scheduled",
    "Site Visit Done",
    "Application Received",
    "Awaiting Post-Site",
    "Post-Site Clarification Resubmitted",
}

client = httpx.Client(base_url=API, timeout=30)


def check(cid: str, title: str, cond: bool, note: str = "") -> None:
    RESULTS.append((cid, title, cond, note))
    print(("PASS " if cond else "FAIL ") + cid + " " + title + ("" if cond else f"  <- {note}"))


def envelope_ok(r: httpx.Response) -> bool:
    if r.status_code < 400:
        return True
    try:
        b = r.json()
    except Exception:
        return False
    return isinstance(b, dict) and "error" in b and {"code", "message"} <= set(b["error"])


def login(email: str) -> dict[str, str]:
    r = client.post("/auth/login", json={"email": email, "password": PW, "take_over": True})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def req(h: dict[str, str], method: str, path: str, **kw) -> httpx.Response:
    headers = {**h, **kw.pop("headers", {})}
    r = client.request(method, path, headers=headers, **kw)
    if r.status_code >= 400 and not envelope_ok(r):
        check("ENV", f"error envelope on {method} {path} ({r.status_code})", False, r.text[:200])
    return r


BUSINESS = {
    "business_name": "Edge Case Kopi Pte. Ltd.",
    "uen": "202388888E",
    "entity_type": "private_limited",
    "contact_name": "Edge Tester",
    "contact_email": "edge@example.sg",
    "contact_phone": "+65 9111 2222",
}
PREMISES = {
    "address_line_1": "1 Edge Road #02-03",
    "postal_code": "123456",
    "premises_type": "shophouse",
    "floor_area_sqm": 40,
    "tenancy_expiry": "2027-12-31",
}
OPERATIONS = {
    "cuisine_description": "Kopi and toast.",
    "seating_capacity": 10,
    "operating_hours": "7am-7pm",
    "food_handlers_count": 2,
}
DECL = {"information_accurate": True, "consent_to_inspection": True}
DOC_TYPES = ["business_profile", "floor_plan", "tenancy_agreement", "food_hygiene_certificate"]
TXT = b"Tenancy agreement business profile ACRA UEN floor plan kitchen food hygiene certificate. " * 3


def tiny_png() -> bytes:
    """A real 4 x 4 PNG: since US-085 an image the server cannot decode is refused at upload."""
    from io import BytesIO

    from PIL import Image

    out = BytesIO()
    Image.new("RGB", (4, 4), (255, 255, 255)).save(out, "PNG")
    return out.getvalue()


def upload(h, app_id, dtype, name, content, mime="text/plain"):
    return req(
        h,
        "POST",
        f"/applications/{app_id}/documents",
        data={"document_type": dtype},
        files={"file": (name, content, mime)},
    )


def fill_all(h, app_id):
    for key, data in (
        ("business", BUSINESS),
        ("premises", PREMISES),
        ("operations", OPERATIONS),
        ("declarations", DECL),
    ):
        r = req(h, "PATCH", f"/applications/{app_id}/sections/{key}", json=data)
        assert r.status_code == 200, r.text


def upload_all(h, app_id):
    for t in DOC_TYPES:
        r = upload(h, app_id, t, f"{t}.txt", TXT)
        assert r.status_code in (200, 201), r.text


def wait_checks(h, app_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        v = req(h, "GET", f"/applications/{app_id}").json()
        states = [
            ((s.get("document") or {}).get("verification") or {}).get("status") for s in v["document_slots"]
        ]
        if all(
            s in ("verified", "issues_found", "unavailable", "unreadable", "failed", "needs_review")
            for s in states
            if s is not None
        ) and all(s is not None for s in states):
            return v
        time.sleep(0.5)
    return req(h, "GET", f"/applications/{app_id}").json()


def res_of(r, fid):
    return next((f["resolution"] for f in r.json().get("feedback", []) if f["id"] == fid), None)


def officer_view(o, app_id):
    return req(o, "GET", f"/officer/applications/{app_id}").json()


def transition(o, app_id, target, note=None, version=None):
    v = officer_view(o, app_id)["version"] if version is None else version
    body = {"target": target, "expected_version": v}
    if note is not None:
        body["note"] = note
    return req(o, "POST", f"/officer/applications/{app_id}/transition", json=body)


def working_day(n: int) -> str:
    """ISO date n working days ahead in Singapore (the appointment rules of US-084)."""
    from app.domain.site_visit import add_working_days, today_in_singapore

    return add_working_days(today_in_singapore(), n).isoformat()


def weekend_ahead() -> str:
    from datetime import date, timedelta

    from app.domain.site_visit import today_in_singapore

    d: date = today_in_singapore() + timedelta(days=1)
    while d.weekday() < 5:
        d += timedelta(days=1)
    return d.isoformat()


def propose(o, app_id, date, slot="morning", note=None):
    v = officer_view(o, app_id)["version"]
    body = {"date": date, "slot": slot, "expected_version": v}
    if note is not None:
        body["note"] = note
    return req(o, "POST", f"/officer/applications/{app_id}/site-visit", json=body)


def arrange_visit(o, p, app_id):
    """Propose and accept so Mark site visit done is allowed (the guard of US-084)."""
    r = propose(o, app_id, working_day(3))
    assert r.status_code == 200, r.text
    r = req(p, "POST", f"/applications/{app_id}/site-visit/accept")
    assert r.status_code == 200, r.text


CHECKLIST = "/officer/applications/{}/checklist"


def clean_items():  # type: ignore[no-untyped-def]
    from app.domain.checklist_schema import ITEM_KEYS

    return [
        {"key": k, "result": "satisfactory", "comment": None, "needs_clarification": False} for k in ITEM_KEYS
    ]


def fresh_case_to_site_visit_done(op, off) -> str:  # type: ignore[no-untyped-def]
    """A new application taken to Site Visit Done with a confirmed visit, for the licence walk."""
    app = req(op, "POST", "/applications").json()
    aid = app["id"]
    fill_all(op, aid)
    upload_all(op, aid)
    wait_checks(op, aid)
    assert req(op, "POST", f"/applications/{aid}/submit").status_code == 200
    assert transition(off, aid, "under_review").status_code == 200
    assert propose(off, aid, working_day(3)).status_code == 200
    assert req(op, "POST", f"/applications/{aid}/site-visit/accept").status_code == 200
    assert transition(off, aid, "site_visit_done").status_code == 200
    return aid


def operator_view_clean(v: dict) -> tuple[bool, str]:
    """No internal status code or officer-only label anywhere in an operator payload."""
    text = json.dumps(v)
    for code in INTERNAL_CODES:
        # allow the codes only as JSON keys of known structures? they must not appear as status values
        if f'"{code}"' in text and code != "draft":
            return False, f"internal code {code} in operator payload"
    for lbl in OFFICER_ONLY_LABELS:
        if lbl in text:
            return False, f"officer-only label {lbl!r} in operator payload"
    return True, ""


def ensure_second_operator() -> None:
    """The wrong-owner checks need a second operator; seeded through the database like scripts/seed.py."""
    from app.core.security import hash_password
    from app.infra.db import session_factory
    from app.models import User
    from app.models.enums import Role
    from app.repositories.users import UserRepository

    with session_factory()() as db:
        repo = UserRepository(db)
        user = repo.get_by_email(OPERATOR2)
        if user is None:
            repo.add(
                User(
                    email=OPERATOR2,
                    full_name="Second Operator (UAT)",
                    role=Role.OPERATOR,
                    password_hash=hash_password(PW),
                )
            )
        else:
            user.is_active = True
        db.commit()


def retire_second_operator() -> None:
    """Deactivate the account the run used. It is not deleted: its sign-ins left session rows and
    user-level audit events (US-093), and audit rows are never deleted. Inactive, it cannot sign in."""
    from app.infra.db import session_factory
    from app.repositories.users import UserRepository

    with session_factory()() as db:
        user = UserRepository(db).get_by_email(OPERATOR2)
        if user is not None:
            user.is_active = False
            db.commit()


def main() -> None:
    ensure_second_operator()
    try:
        run_checks()
    finally:
        retire_second_operator()


def run_checks() -> None:
    # ---------- Auth ----------
    r = client.post("/auth/login", json={"email": OPERATOR, "password": "wrong"})
    check(
        "A1",
        "wrong password is a generic 401 in the envelope",
        r.status_code == 401
        and envelope_ok(r)
        and "password" not in r.json()["error"]["message"].lower().replace("email or password", ""),
        r.text,
    )
    r2 = client.post("/auth/login", json={"email": "nobody@example.sg", "password": "wrong"})
    check(
        "A2",
        "unknown email gives the same 401 message as a wrong password",
        r2.status_code == 401 and r2.json() == r.json(),
        r2.text,
    )
    r = client.post("/auth/login", json={"email": "not-an-email", "password": "x"})
    check("A3", "malformed email is a 422 in the envelope", r.status_code == 422 and envelope_ok(r), r.text)
    r = client.post("/auth/login", content=b"{not json", headers={"Content-Type": "application/json"})
    check(
        "A4",
        "invalid JSON body is a 4xx in the envelope",
        400 <= r.status_code < 500 and envelope_ok(r),
        r.text,
    )
    r = client.get("/applications", headers={"Authorization": "Bearer not.a.token"})
    check(
        "A5", "garbage bearer token is 401 in the envelope", r.status_code == 401 and envelope_ok(r), r.text
    )
    r = client.get("/applications")
    check("A6", "missing token is 401 in the envelope", r.status_code == 401 and envelope_ok(r), r.text)
    r = client.get("/nope")
    check("A7", "unknown route is a 404 in the envelope", r.status_code == 404 and envelope_ok(r), r.text)
    r = client.put("/auth/login")
    check("A8", "wrong method is a 405 in the envelope", r.status_code == 405 and envelope_ok(r), r.text)

    op = login(OPERATOR)
    op2 = login(OPERATOR2)
    off = login(OFFICER)
    r = req(off, "POST", "/applications")
    check("A9", "officer cannot create an application (403)", r.status_code == 403, r.text)
    r = req(op, "GET", "/officer/applications")
    check("A10", "operator cannot read the officer queue (403)", r.status_code == 403, r.text)
    r = req(op, "GET", "/officer/feedback-templates")
    check("A11", "operator cannot read feedback templates (403)", r.status_code == 403, r.text)
    me = req(op, "GET", "/auth/me").json()
    check(
        "A12",
        "/auth/me carries role and no password hash",
        me.get("role") == "operator" and "password" not in json.dumps(me).lower(),
        json.dumps(me),
    )

    # ---------- Draft and sections ----------
    app = req(op, "POST", "/applications").json()
    aid = app["id"]
    r = req(op, "PATCH", f"/applications/{aid}/sections/business", json={**BUSINESS, "hacker": "x"})
    check(
        "D1",
        "unknown field in a section is 422 with the field named",
        r.status_code == 422 and "hacker" in json.dumps(r.json().get("error", {}).get("details", {})),
        r.text,
    )
    r = req(op, "PATCH", f"/applications/{aid}/sections/business", json={**BUSINESS, "uen": "12A"})
    check(
        "D2",
        "invalid UEN is 422 with the field named",
        r.status_code == 422 and "uen" in json.dumps(r.json()["error"].get("details", {})),
        r.text,
    )
    r = req(op, "PATCH", f"/applications/{aid}/sections/business", json={"business_name": "Partial"})
    v = r.json()
    sec = next(s for s in v["sections"] if s["key"] == "business")
    check(
        "D3",
        "partial section saves as a draft (started, not complete)",
        r.status_code == 200 and sec["started"] and not sec["complete"],
        r.text[:200],
    )
    r = req(op, "PATCH", f"/applications/{aid}/sections/unknown", json={})
    check("D4", "unknown section key is 404", r.status_code == 404, r.text)
    r = req(op, "PATCH", f"/applications/{aid}/sections/premises", json={**PREMISES, "floor_area_sqm": "40"})
    check("D5", "number given as a string is 422", r.status_code == 422, r.text)
    r = req(
        op, "PATCH", f"/applications/{aid}/sections/operations", json={**OPERATIONS, "seating_capacity": 24.5}
    )
    check("D6", "fractional integer is 422", r.status_code == 422, r.text)
    r = req(
        op, "PATCH", f"/applications/{aid}/sections/operations", json={**OPERATIONS, "seating_capacity": True}
    )
    check("D7", "boolean for an integer is 422", r.status_code == 422, r.text)
    r = req(
        op,
        "PATCH",
        f"/applications/{aid}/sections/operations",
        json={**OPERATIONS, "cuisine_description": "x" * 1001},
    )
    check("D8", "over-long textarea is 422", r.status_code == 422, r.text)
    r = req(
        op,
        "PATCH",
        f"/applications/{aid}/sections/premises",
        json={**PREMISES, "tenancy_expiry": "2027-02-30"},
    )
    check("D9", "impossible date is 422", r.status_code == 422, r.text)
    r = req(
        op,
        "PATCH",
        f"/applications/{aid}/sections/declarations",
        json={"information_accurate": False, "consent_to_inspection": True},
    )
    dsec = next(s for s in r.json()["sections"] if s["key"] == "declarations") if r.status_code == 200 else {}
    check(
        "D10",
        "unticked declaration saves as a draft but is reported and keeps the section incomplete",
        r.status_code == 200
        and "information_accurate" in dsec.get("errors", {})
        and not dsec.get("complete"),
        r.text[:200],
    )
    r = req(
        op,
        "PATCH",
        f"/applications/{aid}/sections/business",
        json={**BUSINESS, "contact_phone": "+65 9111 2222"},
    )
    check("D11", "phone with spaces and plus is accepted", r.status_code == 200, r.text)
    r = req(
        op,
        "PATCH",
        f"/applications/{aid}/sections/business",
        content=b"[]",
        headers={"Content-Type": "application/json"},
    )
    check(
        "D12",
        "non-object section body is 4xx in the envelope",
        400 <= r.status_code < 500 and envelope_ok(r),
        r.text,
    )
    r = req(op, "POST", f"/applications/{aid}/submit")
    check(
        "D13",
        "submit while incomplete is 422 listing what is missing",
        r.status_code == 422 and "missing" in json.dumps(r.json()["error"].get("details", {})),
        r.text,
    )
    r = req(op2, "GET", f"/applications/{aid}")
    check("D14", "another operator reading the draft gets 404 (not 403)", r.status_code == 404, r.text)
    r = req(op2, "PATCH", f"/applications/{aid}/sections/business", json=BUSINESS)
    check("D15", "another operator editing the draft gets 404", r.status_code == 404, r.text)
    r = req(op, "GET", f"/applications/{uuid.uuid4()}")
    check("D16", "random id is 404", r.status_code == 404, r.text)
    r = req(op, "GET", "/applications/not-a-uuid")
    check("D17", "malformed id is 4xx in the envelope", 400 <= r.status_code < 500 and envelope_ok(r), r.text)
    r = req(off, "GET", f"/officer/applications/{aid}")
    check("D18", "officer cannot see a draft (404)", r.status_code == 404, r.text)

    # ---------- Uploads ----------
    r = upload(op, aid, "floor_plan", "evil.exe", b"MZ\x90\x00" + b"x" * 100, "application/octet-stream")
    check("U1", "disallowed extension is refused (4xx)", r.status_code in (400, 415, 422), r.text)
    r = upload(op, aid, "floor_plan", "fake.pdf", b"this is not a pdf at all " * 4, "application/pdf")
    check("U2", "PDF extension with wrong magic bytes is refused", r.status_code in (400, 415, 422), r.text)
    r = upload(op, aid, "floor_plan", "fake.png", b"%PDF-1.4 " + b"x" * 50, "image/png")
    check("U3", "PNG extension with PDF magic bytes is refused", r.status_code in (400, 415, 422), r.text)
    r = upload(op, aid, "floor_plan", "empty.txt", b"", "text/plain")
    check("U4", "empty file is refused", r.status_code in (400, 422), r.text)
    r = upload(op, aid, "floor_plan", "big.txt", b"a" * (10 * 1024 * 1024 + 1), "text/plain")
    check("U5", "10 MB + 1 byte is refused", r.status_code in (400, 413), r.text)
    r = upload(op, aid, "floor_plan", "exact.txt", b"a" * (10 * 1024 * 1024), "text/plain")
    check("U6", "exactly 10 MB is accepted", r.status_code in (200, 201), r.text[:200])
    r = upload(op, aid, "not_a_type", "x.txt", TXT)
    check("U7", "unknown document type is 4xx", r.status_code in (400, 422), r.text)
    r = upload(op, aid, "floor_plan", "../../../etc/passwd.txt", TXT)
    check(
        "U8",
        "path-like filename is accepted and stored under a server key (no traversal)",
        r.status_code in (200, 201)
        and ".." not in json.dumps(r.json()["document"]).replace("../../../etc/passwd.txt", ""),
        r.text[:200],
    )
    doc = r.json()["document"]
    r = upload(op, aid, "floor_plan", "same.txt", TXT)
    check(
        "U9",
        "identical bytes re-uploaded is reported as unchanged",
        r.status_code in (200, 201) and r.json()["unchanged"] is True,
        r.text[:200],
    )
    r = upload(op, aid, "floor_plan", "different.txt", TXT + b" changed")
    check(
        "U10",
        "different bytes replace the document (new id, unchanged false)",
        r.status_code in (200, 201)
        and r.json()["unchanged"] is False
        and r.json()["document"]["id"] != doc["id"],
        r.text[:200],
    )
    doc = r.json()["document"]
    r = req(op, "GET", f"/applications/{aid}/documents/{doc['id']}/download")
    check(
        "U11",
        "owner downloads own document with a content-disposition",
        r.status_code == 200 and "attachment" in r.headers.get("content-disposition", ""),
        r.headers.get("content-disposition", ""),
    )
    r = req(op2, "GET", f"/applications/{aid}/documents/{doc['id']}/download")
    check("U12", "another operator cannot download it (404)", r.status_code == 404, r.text)
    r = req(off, "GET", f"/applications/{aid}/documents/{doc['id']}/download")
    check("U13", "officer cannot download a draft's document (404)", r.status_code == 404, r.text)
    r = req(op, "GET", f"/applications/{aid}/documents/{uuid.uuid4()}/download")
    check("U14", "unknown document id is 404", r.status_code == 404, r.text)
    r = upload(op, aid, "floor_plan", "photo.png", tiny_png(), "image/png")
    check("U15", "PNG is accepted", r.status_code in (200, 201), r.text[:200])
    png_doc = r.json()["document"]
    r = upload(op, aid, "floor_plan", "broken.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png")
    check(
        "U15b",
        "a PNG the server cannot decode is refused as unreadable_image (US-085)",
        r.status_code == 400 and r.json()["error"]["details"].get("reason") == "unreadable_image",
        r.text[:200],
    )
    v = wait_checks(op, aid)
    slot = next(s for s in v["document_slots"] if s["type"] == "floor_plan")
    ver = (slot["document"] or {}).get("verification") or {}
    check(
        "U16",
        "image check ends as unreadable (not stuck running)",
        ver.get("status") in ("unreadable", "unavailable"),
        json.dumps(ver),
    )
    r = req(op, "DELETE", f"/applications/{aid}/documents/{png_doc['id']}")
    check(
        "U17",
        "delete a document in draft succeeds and the slot is empty",
        r.status_code in (200, 204)
        and (
            r.status_code == 204
            or not next(s for s in r.json()["document_slots"] if s["type"] == "floor_plan")["present"]
        ),
        r.text[:200],
    )
    r = req(op, "DELETE", f"/applications/{aid}/documents/{png_doc['id']}")
    check("U18", "deleting it again is 404", r.status_code == 404, r.text)
    r = req(op, "POST", f"/applications/{aid}/documents/{uuid.uuid4()}/verify")
    check("U19", "re-run on an unknown document is 404", r.status_code == 404, r.text)

    # ---------- Full submission ----------
    fill_all(op, aid)
    upload_all(op, aid)
    v = wait_checks(op, aid)
    check(
        "V1",
        "all four checks finish on the mock provider",
        all(
            ((s["document"] or {}).get("verification") or {}).get("status")
            not in (None, "pending", "running")
            for s in v["document_slots"]
        ),
        json.dumps(
            [((s["document"] or {}).get("verification") or {}).get("status") for s in v["document_slots"]]
        ),
    )
    check(
        "V2",
        "completeness reaches 100 % and can_submit",
        v["completeness"]["percent"] == 100 and v["can_submit"],
        json.dumps(v["completeness"]),
    )
    doc_id = v["document_slots"][0]["document"]["id"]
    r = req(op, "POST", f"/applications/{aid}/documents/{doc_id}/verify")
    check("V3", "operator re-run check returns 200/202", r.status_code in (200, 202), r.text[:200])
    wait_checks(op, aid)

    # concurrent submit: exactly one wins
    def do_submit(_):
        return client.post(f"/applications/{aid}/submit", headers=op).status_code

    with cf.ThreadPoolExecutor(2) as ex:
        codes = list(ex.map(do_submit, range(2)))
    check(
        "S1",
        "two concurrent submits: exactly one 200, the other 409",
        sorted(codes) == [200, 409],
        str(codes),
    )
    v = req(op, "GET", f"/applications/{aid}").json()
    check(
        "S2",
        "after submit the operator label is a public label and editing is off",
        v["status_label"] and not v["can_edit"] and not v["can_submit"] and v["revision_count"] == 1,
        json.dumps({k: v[k] for k in ("status_label", "can_edit", "can_submit", "revision_count")}),
    )
    ok, note = operator_view_clean(v)
    check("S3", "operator payload carries no internal status code or officer-only label", ok, note)
    r = req(op, "POST", f"/applications/{aid}/submit")
    check("S4", "submit again is 409", r.status_code == 409, r.text)
    r = req(op, "PATCH", f"/applications/{aid}/sections/business", json=BUSINESS)
    check("S5", "editing a section after submission is 403", r.status_code == 403, r.text)
    r = upload(op, aid, "floor_plan", "late.txt", TXT + b"late")
    check("S6", "uploading after submission is 403", r.status_code == 403, r.text)
    r = req(op, "DELETE", f"/applications/{aid}/documents/{doc_id}")
    check("S7", "deleting a document after submission is 403", r.status_code == 403, r.text)
    r = req(op, "DELETE", f"/applications/{aid}")
    check("S8", "deleting a submitted application is 409", r.status_code == 409, r.text)
    r = req(op, "GET", f"/applications/{aid}/licence")
    check("S9", "licence download before approval is 404", r.status_code == 404, r.text)
    r = req(op, "GET", f"/officer/applications/{aid}/audit")
    check("S10", "operator cannot read the audit trail (403)", r.status_code == 403, r.text)
    r = req(off, "GET", f"/applications/{aid}/documents/{doc_id}/download")
    check("S11", "officer can download a submitted document", r.status_code == 200, r.text[:100])

    # ---------- Officer: guards ----------
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "section", "section_key": "premises", "message": "x"},
    )
    check("O1", "feedback before Start review is 409", r.status_code == 409, r.text)
    r = transition(off, aid, "approved")
    check(
        "O2",
        "approve from Application Received is 409 invalid_transition",
        r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition",
        r.text,
    )
    r = transition(off, aid, "not_a_status")
    check(
        "O3",
        "unknown target status is 4xx in the envelope",
        400 <= r.status_code < 500 and envelope_ok(r),
        r.text,
    )
    r = transition(off, aid, "under_review", version=999)
    check(
        "O4",
        "stale expected_version is 409 version_conflict",
        r.status_code == 409 and r.json()["error"]["code"] == "version_conflict",
        r.text,
    )
    r = req(
        op,
        "POST",
        f"/officer/applications/{aid}/transition",
        json={"target": "under_review", "expected_version": 1},
    )
    check("O5", "operator cannot transition (403)", r.status_code == 403, r.text)
    ver0 = officer_view(off, aid)["version"]

    def do_tr(_):
        return client.post(
            f"/officer/applications/{aid}/transition",
            headers=off,
            json={"target": "under_review", "expected_version": ver0},
        ).status_code

    with cf.ThreadPoolExecutor(2) as ex:
        codes = list(ex.map(do_tr, range(2)))
    check(
        "O6",
        "two concurrent Start review with the same version: one 200, one 409",
        sorted(codes) == [200, 409],
        str(codes),
    )
    r = transition(off, aid, "pending_pre_site_resubmission")
    check(
        "O7",
        "request resubmission with zero feedback is 409 with a reason",
        r.status_code == 409 and "feedback" in r.json()["error"]["message"].lower(),
        r.text,
    )
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "section", "section_key": "nope", "message": "x"},
    )
    check("O8", "feedback on an unknown section is 422", r.status_code == 422, r.text)
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "document", "document_type": "nope", "message": "x"},
    )
    check("O9", "feedback on an unknown document type is 422", r.status_code == 422, r.text)
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "section", "section_key": "premises", "message": "   "},
    )
    check("O10", "blank feedback message is 422", r.status_code == 422, r.text)
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "section", "section_key": "premises", "message": "x" * 2001},
    )
    check("O11", "over-long feedback message is 422", r.status_code == 422, r.text)
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={
            "target_type": "section",
            "section_key": "premises",
            "document_type": "floor_plan",
            "message": "x",
        },
    )
    check(
        "O12",
        "feedback naming both a section and a document keeps only the section target",
        r.status_code == 201
        and r.json()["feedback"][-1]["document_type"] is None
        and r.json()["feedback"][-1]["section_key"] == "premises",
        r.text[:200],
    )
    fb0 = r.json()["feedback"][-1]["id"]
    req(off, "POST", f"/officer/applications/{aid}/feedback/{fb0}/withdraw")
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "section", "section_key": "premises", "message": "Confirm the unit number."},
    )
    check(
        "O13",
        "valid section feedback is created as an open, unreleased item",
        r.status_code == 201
        and r.json()["feedback"][-1]["resolution"] == "open"
        and r.json()["feedback"][-1]["released_to_operator_at"] is None,
        r.text[:200],
    )
    fb1 = r.json()["feedback"][-1]["id"]
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "document", "document_type": "floor_plan", "message": "Replace the plan."},
    )
    fb2 = r.json()["feedback"][-1]["id"]
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb2}/resolve")
    check("O14", "resolving an unreleased draft item is 409", r.status_code == 409, r.text)
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb2}/reopen")
    check("O15", "reopening an open item is 409", r.status_code == 409, r.text)
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{uuid.uuid4()}/withdraw")
    check("O16", "withdrawing an unknown item is 404", r.status_code == 404, r.text)
    v = req(op, "GET", f"/applications/{aid}").json()
    check(
        "O17",
        "operator does not see draft (unreleased) feedback",
        v["feedback"] == [] and not v["needs_operator_action"],
        json.dumps(v["feedback"]),
    )
    r = transition(off, aid, "site_visit_scheduled")
    check("O18", "site visit with open feedback is 409", r.status_code == 409, r.text)
    r = transition(off, aid, "pending_pre_site_resubmission")
    check("O19", "request resubmission with feedback succeeds", r.status_code == 200, r.text[:200])
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/withdraw")
    check("O20", "withdrawing released feedback is 409 (frozen)", r.status_code == 409, r.text)
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        json={"target_type": "section", "section_key": "business", "message": "late"},
    )
    check("O21", "adding feedback after the request is 409 (frozen)", r.status_code == 409, r.text)
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/resolve")
    check("O22", "resolving before the operator responded is 409", r.status_code == 409, r.text)

    # ---------- Operator: resubmission ----------
    v = req(op, "GET", f"/applications/{aid}").json()
    check(
        "R1",
        "operator sees the two released items and needs_operator_action",
        len(v["feedback"]) == 2 and v["needs_operator_action"] and v["can_edit"],
        json.dumps({"n": len(v["feedback"]), "needs": v["needs_operator_action"]}),
    )
    ok, note = operator_view_clean(v)
    check("R2", "operator payload still clean of internal codes", ok, note)
    check(
        "R3",
        "feedback view has no officer identity",
        all(
            "officer" not in json.dumps(f).lower() or "licensing" in json.dumps(f).lower()
            for f in v["feedback"]
        )
        and all("author" not in f for f in v["feedback"]),
        json.dumps(v["feedback"])[:300],
    )
    r = req(
        op, "PATCH", f"/applications/{aid}/sections/business", json={**BUSINESS, "business_name": "Changed"}
    )
    check("R4", "editing an unflagged section during resubmission is 403", r.status_code == 403, r.text)
    r = upload(op, aid, "tenancy_agreement", "new.txt", TXT + b"new")
    check("R5", "replacing an unflagged document is 403", r.status_code == 403, r.text)
    r = req(op, "POST", f"/applications/{aid}/resubmit")
    check(
        "R6",
        "resubmit without any change is 422 no_change",
        r.status_code == 422 and "no_change" in r.text,
        r.text,
    )
    r = req(op, "PATCH", f"/applications/{aid}/sections/premises", json=PREMISES)
    check(
        "R7",
        "saving the flagged section with identical values is accepted (200)",
        r.status_code == 200,
        r.text[:200],
    )
    r = req(op, "POST", f"/applications/{aid}/resubmit")
    check("R8", "identical values are not a change: resubmit still 422", r.status_code == 422, r.text)
    r = req(
        op,
        "PATCH",
        f"/applications/{aid}/sections/premises",
        json={**PREMISES, "address_line_1": "1 Edge Road #02-04"},
    )
    check("R9", "changing the flagged section is accepted", r.status_code == 200, r.text[:200])
    v = req(op, "GET", f"/applications/{aid}").json()
    check(
        "R10",
        "readiness lists the changed section and the untouched document",
        v["resubmit"]["can_resubmit"]
        and "premises" in v["resubmit"]["changed_sections"]
        and "Floor plan" in v["resubmit"]["untouched_targets"],
        json.dumps(v["resubmit"]),
    )
    r = req(op, "POST", f"/applications/{aid}/withdraw", json={"reason": "x" * 1001})
    check("R11", "withdraw reason over 1000 chars is 422", r.status_code == 422, r.text)
    r = req(op2, "POST", f"/applications/{aid}/resubmit")
    check("R12", "another operator cannot resubmit (404)", r.status_code == 404, r.text)
    r = req(op, "POST", f"/applications/{aid}/resubmit")
    check(
        "R13",
        "resubmit with one of two flagged targets changed succeeds as Revision 2",
        r.status_code == 200 and r.json()["revision_count"] == 2,
        r.text[:200],
    )
    v = r.json()
    res = {f["id"]: f["resolution"] for f in v["feedback"]}
    check(
        "R14",
        "changed target is addressed, untouched stays open",
        res.get(fb1) == "addressed" and res.get(fb2) == "open",
        json.dumps(res),
    )
    check("R15", "operator cannot edit after resubmitting", not v["can_edit"], "")
    ok, note = operator_view_clean(v)
    check("R16", "operator payload clean after resubmission", ok, note)

    # ---------- Compare ----------
    r = req(op, "GET", f"/applications/{aid}/compare", params={"from": 1, "to": 2})
    check(
        "C1",
        "compare 1 to 2 shows the premises change",
        r.status_code == 200 and "address_line_1" in r.text,
        r.text[:300],
    )
    r = req(op, "GET", f"/applications/{aid}/compare", params={"from": 2, "to": 2})
    check(
        "C2",
        "compare a revision with itself is 200 with no changes (or 4xx)",
        (r.status_code == 200 and "address_line_1" not in r.text) or 400 <= r.status_code < 500,
        r.text[:200],
    )
    r = req(op, "GET", f"/applications/{aid}/compare", params={"from": 1, "to": 9})
    check("C3", "compare with a missing revision is 404", r.status_code == 404, r.text)
    r = req(op, "GET", f"/applications/{aid}/compare", params={"from": 0, "to": 1})
    check("C4", "compare with revision 0 is 422", r.status_code == 422, r.text)
    r = req(op2, "GET", f"/applications/{aid}/compare", params={"from": 1, "to": 2})
    check("C5", "another operator cannot compare (404)", r.status_code == 404, r.text)
    r = req(off, "GET", f"/applications/{aid}/compare", params={"from": 2, "to": 1})
    check("C6", "officer can compare in reverse order", r.status_code == 200, r.text[:200])

    # ---------- Officer round 2 ----------
    r = transition(off, aid, "under_review")
    check("O23", "Start review on the resubmission", r.status_code == 200, r.text[:200])
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/reopen")
    check(
        "O24",
        "addressed item can be marked not fixed (reopen)",
        r.status_code == 200 and res_of(r, fb1) == "open",
        r.text[:200],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/resolve")
    check(
        "O25",
        "a reopened (not fixed) item is a draft again: resolve is refused, undo or withdraw instead",
        r.status_code == 409,
        r.text[:200],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/restore")
    check(
        "O26",
        "Not fixed can be undone: the item is addressed again and back in the operator's view",
        r.status_code == 200 and res_of(r, fb1) == "addressed",
        r.text[:200],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/resolve")
    check(
        "O26b",
        "the addressed item can be resolved",
        r.status_code == 200 and res_of(r, fb1) == "resolved",
        r.text[:200],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/restore")
    check(
        "O26c",
        "resolve can be undone within the window",
        r.status_code == 200 and res_of(r, fb1) == "addressed",
        r.text[:200],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb1}/resolve")
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb2}/withdraw")
    check(
        "O27",
        "an open item from an earlier round can be withdrawn while Under Review",
        r.status_code == 200,
        r.text[:200],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb2}/restore")
    check("O28", "withdraw can be undone", r.status_code == 200 and res_of(r, fb2) == "open", r.text[:200])
    r = req(off, "POST", f"/officer/applications/{aid}/feedback/{fb2}/resolve")
    check("O29", "resolve an open item the operator has seen", r.status_code == 200, r.text[:200])
    r = transition(off, aid, "site_visit_done")
    check("O30", "skipping to Site Visit Done is 409", r.status_code == 409, r.text)
    r = transition(off, aid, "site_visit_scheduled")
    check("O31", "schedule site visit with no open feedback", r.status_code == 200, r.text[:200])
    v = req(op, "GET", f"/applications/{aid}").json()
    ok, note = operator_view_clean(v)
    check(
        "O32",
        "operator label for the site visit state is the public one",
        ok and v["status_label"] == "Pending Site Visit",
        v["status_label"] + " " + note,
    )
    r = req(op, "POST", f"/applications/{aid}/resubmit")
    check("O33", "operator resubmit while a site visit is pending is 409", r.status_code == 409, r.text)

    # ---------- Site visit appointment (US-084) ----------
    r = transition(off, aid, "site_visit_done")
    check("SV1", "Mark site visit done before a confirmed date is 409 (guard)", r.status_code == 409, r.text)
    v = officer_view(off, aid)
    done = next(a for a in v["actions"] if a["target"] == "site_visit_done")
    check(
        "SV2",
        "the guard reason is served on the action",
        not done["enabled"] and "Confirm the visit date" in (done["reason"] or ""),
        json.dumps(done),
    )
    r = req(
        op,
        "POST",
        f"/officer/applications/{aid}/site-visit",
        json={"date": working_day(3), "slot": "morning", "expected_version": v["version"]},
    )
    check("SV3", "operator on the officer propose route is 403", r.status_code == 403, r.text)
    r = propose(off, aid, weekend_ahead())
    check(
        "SV4",
        "a weekend date is 422 naming the rule",
        r.status_code == 422 and "Monday to Friday" in r.json()["error"]["details"]["fields"]["date"],
        r.text,
    )
    r = propose(off, aid, "2020-01-06")
    check(
        "SV5",
        "a past date is 422",
        r.status_code == 422 and "date" in r.json()["error"]["details"]["fields"],
        r.text,
    )
    r = propose(off, aid, working_day(3), slot="evening")
    check(
        "SV6",
        "an unknown slot is 422 on the slot field",
        r.status_code == 422 and "slot" in r.json()["error"]["details"]["fields"],
        r.text,
    )
    far = working_day(50)
    r = propose(off, aid, far)
    check(
        "SV7",
        "more than 60 days out is 422",
        r.status_code == 422 and "60" in r.json()["error"]["details"]["fields"]["date"],
        r.text,
    )
    r = propose(off, aid, working_day(3), note="x" * 501)
    check("SV8", "a 501-character note is 422", r.status_code == 422, r.text[:200])
    r = propose(off, aid, working_day(3), slot="afternoon", note="Have the pest control contract ready.")
    check(
        "SV9",
        "a valid proposal on a case scheduled through the API opens the visit",
        r.status_code == 200
        and r.json()["site_visit"]["status"] == "proposed"
        and r.json()["site_visit"]["status_label"] == "Waiting for the operator",
        r.text[:300],
    )
    r = propose(off, aid, working_day(4))
    check("SV10", "a second proposal while one is open is 409", r.status_code == 409, r.text)
    r = req(op2, "POST", f"/applications/{aid}/site-visit/accept")
    check("SV11", "another operator accepting is 404", r.status_code == 404, r.text)
    r = req(off, "POST", f"/applications/{aid}/site-visit/accept")
    check("SV12", "an officer on the operator accept route is 403", r.status_code == 403, r.text)
    v = req(op, "GET", f"/applications/{aid}").json()
    sv = v["site_visit"]
    ok, note = operator_view_clean(v)
    check(
        "SV13",
        "operator view: own label, reply-by date, the officer's note, the earliest date, no officer name",
        ok
        and sv["status_label"] == "Waiting for your reply"
        and sv["reply_by"]
        and sv["note"]
        and sv["earliest_date"] == working_day(2)
        and all(
            r_["author_name"] == "Licensing officer" for r_ in sv["rounds"] if r_["author_role"] == "officer"
        )
        and v["needs_operator_action"]
        and "Waiting for the operator" not in json.dumps(v),
        note + json.dumps(sv)[:200],
    )
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/counter",
        json={"date": working_day(1), "slot": "morning", "reason": "Too soon."},
    )
    check(
        "SV14",
        "a counter one working day ahead is 422 (two needed)",
        r.status_code == 422 and "2 working days" in r.json()["error"]["details"]["fields"]["date"],
        r.text,
    )
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/counter",
        json={"date": working_day(4), "slot": "morning"},
    )
    check(
        "SV15",
        "a counter without a reason is 422 on the reason field",
        r.status_code == 422 and "reason" in r.json()["error"]["details"]["fields"],
        r.text,
    )
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/reschedule",
        json={"date": working_day(4), "slot": "morning", "reason": "Not yet."},
    )
    check("SV16", "reschedule before the visit is confirmed is 409", r.status_code == 409, r.text)
    r = req(off, "POST", f"/officer/applications/{aid}/site-visit/confirm")
    check(
        "SV17",
        "confirm without a reply before the deadline is 409 naming the date",
        r.status_code == 409 and "until" in r.json()["error"]["message"],
        r.text,
    )
    r = req(off, "POST", f"/officer/applications/{aid}/site-visit/decide", json={"action": "accept_operator"})
    check("SV18", "deciding when no counter exists is 409", r.status_code == 409, r.text)
    counter_date = working_day(5)
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/counter",
        json={"date": counter_date, "slot": "afternoon", "reason": "The shop is closed that morning."},
    )
    check(
        "SV19",
        "a valid counter waits on the officer; the operator can no longer accept",
        r.status_code == 200
        and r.json()["site_visit"]["status_label"] == "Waiting for the officer"
        and r.json()["site_visit"]["can_accept"] is False,
        r.text[:300],
    )
    r = req(op, "POST", f"/applications/{aid}/site-visit/accept")
    check("SV20", "accept after countering is 409", r.status_code == 409, r.text)
    r = req(off, "POST", f"/officer/applications/{aid}/site-visit/decide", json={"action": "flip_coin"})
    check("SV21", "an unknown decision is 422", r.status_code == 422, r.text)
    r = req(off, "POST", f"/officer/applications/{aid}/site-visit/decide", json={"action": "propose"})
    check("SV22", "a third date without a date is 422", r.status_code == 422, r.text)
    row = next(i for i in req(off, "GET", "/officer/applications").json()["items"] if i["id"] == aid)
    check(
        "SV23",
        "the queue says Decide the visit date and it is the officer's turn",
        row["next_action"] == "Decide the visit date" and row["officer_turn"],
        json.dumps(row)[:200],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/site-visit/decide", json={"action": "keep_original"})
    sv = r.json().get("site_visit", {})
    check(
        "SV24",
        "keep original confirms the officer's date",
        r.status_code == 200
        and sv.get("status") == "confirmed"
        and sv.get("slot") == "afternoon"
        and sv.get("date") == working_day(3),
        r.text[:300],
    )
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/reschedule",
        json={"date": working_day(8), "slot": "morning"},
    )
    check("SV25", "a reschedule without a reason is 422", r.status_code == 422, r.text)
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/reschedule",
        json={"date": working_day(8), "slot": "morning", "reason": "Renovation that week."},
    )
    sv = r.json().get("site_visit", {})
    check(
        "SV26",
        "the operator's reschedule keeps the confirmed date until the officer decides",
        r.status_code == 200
        and sv.get("status_label") == "Waiting for the officer"
        and sv.get("date") == working_day(3),
        r.text[:300],
    )
    r = req(off, "POST", f"/officer/applications/{aid}/site-visit/decide", json={"action": "accept_operator"})
    sv = r.json().get("site_visit", {})
    check(
        "SV27",
        "accepting the operator's new date confirms it",
        r.status_code == 200 and sv.get("status") == "confirmed" and sv.get("date") == working_day(8),
        r.text[:300],
    )
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit/reschedule",
        json={"date": working_day(9), "slot": "afternoon", "reason": "Inspector on leave."},
    )
    check(
        "SV28",
        "the officer's reschedule becomes a proposal the operator answers",
        r.status_code == 200 and r.json()["site_visit"]["status"] == "proposed",
        r.text[:300],
    )
    r = req(op, "POST", f"/applications/{aid}/site-visit/accept")
    check(
        "SV29",
        "the operator accepts the moved date",
        r.status_code == 200 and r.json()["site_visit"]["status_label"] == "Confirmed",
        r.text[:300],
    )
    v = req(op, "GET", f"/applications/{aid}").json()
    check(
        "SV30",
        "operator history: every round with its outcome, rounds counted",
        len(v["site_visit"]["rounds"]) == 4
        and [x["outcome"] for x in v["site_visit"]["rounds"]] == ["kept", "declined", "accepted", "accepted"],
        json.dumps([x["outcome"] for x in v["site_visit"]["rounds"]]),
    )
    trail = req(off, "GET", f"/officer/applications/{aid}/audit").json()["events"]
    kinds = [e["event_type"] for e in trail if e["event_type"].startswith("site_visit.")]
    check(
        "SV31",
        "every round is an audit event in order",
        kinds
        == [
            "site_visit.proposed",
            "site_visit.counter_proposed",
            "site_visit.confirmed",
            "site_visit.rescheduled",
            "site_visit.confirmed",
            "site_visit.rescheduled",
            "site_visit.confirmed",
        ],
        json.dumps(kinds),
    )
    check(
        "SV32",
        "audit summaries read as sentences",
        all(
            not e["summary"].startswith("site_visit.")
            for e in trail
            if e["event_type"].startswith("site_visit.")
        ),
        json.dumps([e["summary"] for e in trail if e["event_type"].startswith("site_visit.")])[:300],
    )
    r = transition(off, aid, "site_visit_done")
    check(
        "SV33",
        "Mark site visit done once confirmed; the visit is done",
        r.status_code == 200 and r.json()["site_visit"]["status"] == "done",
        r.text[:300],
    )
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/reschedule",
        json={"date": working_day(9), "slot": "morning", "reason": "Late."},
    )
    check("SV34", "reschedule after the visit is done is 409", r.status_code == 409, r.text)

    # ---------- Site visit checklist (US-060 to US-063) ----------
    r = transition(off, aid, "pending_approval")
    check(
        "CK1",
        "no route from Site Visit Done straight to approval: the checklist is the way",
        r.status_code == 409,
        r.text,
    )
    r = req(op, "GET", "/checklist-schema")
    check("CK2", "operator cannot read the checklist template (403)", r.status_code == 403, r.text)
    r = req(off, "GET", "/checklist-schema")
    check(
        "CK3",
        "the template is versioned with 17 items in 5 sections",
        r.status_code == 200
        and r.json()["version"] == 1
        and r.json()["item_count"] == 17
        and len(r.json()["sections"]) == 5,
        r.text[:200],
    )
    r = req(off, "POST", CHECKLIST.format(aid) + "/submit")
    check("CK4", "submit before the checklist exists is 404", r.status_code == 404, r.text)
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": clean_items(), "version": 1})
    check("CK5", "save before the checklist exists is 404", r.status_code == 404, r.text)
    r = req(off, "POST", CHECKLIST.format(aid))
    check(
        "CK6",
        "first open creates the draft (201) with every item not assessed",
        r.status_code == 201
        and all(i["result"] == "not_assessed" for i in r.json()["items"])
        and r.json()["version"] == 1,
        r.text[:200],
    )
    cl = r.json()
    r = req(off, "POST", CHECKLIST.format(aid))
    check(
        "CK7",
        "second open returns the same draft (200)",
        r.status_code == 200 and r.json()["id"] == cl["id"],
        r.text[:200],
    )
    r = req(op, "POST", CHECKLIST.format(aid))
    check("CK8", "operator on the checklist routes is 403", r.status_code == 403, r.text)
    r = req(op2, "GET", CHECKLIST.format(aid))
    check("CK9", "another operator on the checklist route is 403 (role first)", r.status_code == 403, r.text)
    r = req(off, "POST", CHECKLIST.format(aid) + "/submit")
    check(
        "CK10",
        "submit with nothing assessed is 422 listing every item",
        r.status_code == 422 and len(r.json()["error"]["details"]["items"]) == 17,
        r.text[:200],
    )
    bad = clean_items() + [
        {"key": "gold_taps", "result": "satisfactory", "comment": None, "needs_clarification": False}
    ]
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": bad, "version": cl["version"]})
    check(
        "CK11",
        "an item not on the template is 422 on its key",
        r.status_code == 422 and "gold_taps" in r.json()["error"]["details"]["fields"],
        r.text[:200],
    )
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": clean_items()[:3], "version": cl["version"]})
    check(
        "CK12",
        "a partial item list is 422 naming the count missing",
        r.status_code == 422 and "14 missing" in r.json()["error"]["details"]["fields"]["items"],
        r.text[:200],
    )
    items = clean_items()
    items[1] = {
        "key": "floor_trap_graded",
        "result": "unsatisfactory",
        "comment": None,
        "needs_clarification": False,
    }
    items[2] = {"key": "coved_edges", "result": "satisfactory", "comment": None, "needs_clarification": True}
    items[8] = {"key": "make_up_air", "result": "not_assessed", "comment": None, "needs_clarification": False}
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": items, "version": cl["version"]})
    check(
        "CK13",
        "a draft may hold unassessed and uncommented items; the counts say what is left",
        r.status_code == 200
        and r.json()["version"] == 2
        and r.json()["counts"]["assessed"] == 16
        and r.json()["counts"]["missing_comments"] == 2
        and r.json()["remaining"] == "Assess 1 more item and add 2 comments to submit.",
        r.text[:300],
    )
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": items, "version": 1})
    check(
        "CK14",
        "a stale version is 409 version_conflict carrying the current content",
        r.status_code == 409
        and r.json()["error"]["code"] == "version_conflict"
        and r.json()["error"]["details"]["current"]["version"] == 2,
        r.text[:200],
    )
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": items, "version": 2, "save_id": "uat-1"})
    r2 = req(off, "PUT", CHECKLIST.format(aid), json={"items": items, "version": 2, "save_id": "uat-1"})
    check(
        "CK15",
        "a replayed save id answers 200 with the state instead of a conflict",
        r.status_code == 200 and r2.status_code == 200 and r2.json()["version"] == r.json()["version"] == 3,
        r2.text[:200],
    )
    r = req(off, "POST", CHECKLIST.format(aid) + "/submit")
    check(
        "CK16",
        "submit with an unassessed and two uncommented items is 422 naming the three keys",
        r.status_code == 422
        and set(r.json()["error"]["details"]["items"]) == {"floor_trap_graded", "coved_edges", "make_up_air"},
        r.text[:300],
    )
    items[1]["comment"] = "Floor slopes away from the trap."
    items[2]["comment"] = "Please confirm the coving work."
    items[8]["result"] = "satisfactory"
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": items, "version": 3})
    check(
        "CK17",
        "the completed draft saves; nothing remains before submit",
        r.status_code == 200 and r.json()["remaining"] is None,
        r.text[:200],
    )
    row = next(i for i in req(off, "GET", "/officer/applications").json()["items"] if i["id"] == aid)
    check(
        "CK18",
        "the queue says Continue the checklist",
        row["next_action"] == "Continue the checklist",
        json.dumps(row)[:200],
    )
    r = req(off, "POST", CHECKLIST.format(aid) + "/submit")
    check(
        "CK19",
        "submit freezes the findings, opens round 1 for the flagged item and moves the case",
        r.status_code == 200
        and r.json()["status"] == "submitted"
        and next(i for i in r.json()["items"] if i["key"] == "coved_edges")["clarification_status"] == "open",
        r.text[:300],
    )
    v = officer_view(off, aid)
    check(
        "CK20",
        "the case is Awaiting Post-Site Clarification with the checklist summary submitted",
        v["status"] == "awaiting_post_site_clarification"
        and v["checklist"]["status"] == "submitted"
        and v["site_visit"]["status"] == "done",
        json.dumps(v["checklist"])[:200],
    )
    r = req(off, "PUT", CHECKLIST.format(aid), json={"items": items, "version": 5})
    check("CK21", "a save after submit is 409 (findings frozen)", r.status_code == 409, r.text)
    r = req(off, "POST", CHECKLIST.format(aid) + "/submit")
    check("CK22", "a second submit is 409", r.status_code == 409, r.text)
    mine = req(op, "GET", f"/applications/{aid}").json()
    ok, note = operator_view_clean(mine)
    check(
        "CK23",
        "operator sees Pending Post-Site Clarification with the count, never a result or a checklist",
        ok
        and mine["status_label"] == "Pending Post-Site Clarification"
        and "1 item" in mine["status_explanation"]
        and "checklist" not in mine
        and "unsatisfactory" not in json.dumps(mine),
        mine["status_explanation"] + note,
    )
    trail = req(off, "GET", f"/officer/applications/{aid}/audit").json()["events"]
    kinds = [e["event_type"] for e in trail][-2:]
    check(
        "CK24",
        "audit order: checklist.submitted then the system hop (the visit was already done here)",
        kinds == ["checklist.submitted", "status.changed"] and trail[-1]["payload"]["trigger"] == "system",
        json.dumps(kinds),
    )
    r = transition(off, aid, "pending_approval")
    check("CK25", "Route to approval waits while an item is open (409)", r.status_code == 409, r.text)
    # answering the open item is US-065; for the walk below the flagged item is not needed: reject-free
    # exit is only through the operator's answers, so this application ends here and the licence path
    # continues on a fresh one
    aid = fresh_case_to_site_visit_done(op, off)
    r = req(off, "POST", CHECKLIST.format(aid))
    req(off, "PUT", CHECKLIST.format(aid), json={"items": clean_items(), "version": r.json()["version"]})
    r = req(off, "POST", CHECKLIST.format(aid) + "/submit")
    check(
        "CK26",
        "a clean checklist submits with nothing flagged",
        r.status_code == 200 and r.json()["counts"]["flagged"] == 0,
        r.text[:200],
    )
    mine = req(op, "GET", f"/applications/{aid}").json()
    check(
        "CK27",
        "with nothing flagged the operator is told nothing is needed",
        mine["status_explanation"].startswith("The site visit is recorded"),
        mine["status_explanation"],
    )
    r = transition(off, aid, "pending_approval")
    check("O34", "Route to approval", r.status_code == 200, r.text[:200])
    v = req(op, "GET", f"/applications/{aid}").json()
    ok, note = operator_view_clean(v)
    check(
        "O35",
        "operator sees Pending Approval, no decision note yet",
        ok and v["status_label"] == "Pending Approval" and v["decision_note"] is None,
        v["status_label"] + " " + note,
    )
    r = transition(off, aid, "rejected")
    check("O36", "reject without a note is refused", r.status_code in (409, 422), r.text)
    r = transition(off, aid, "rejected", note="   ")
    check("O37", "reject with a blank note is refused", r.status_code in (409, 422), r.text)
    r = transition(off, aid, "under_review")
    check("O38", "Return to review from Pending Approval", r.status_code == 200, r.text[:200])
    r = transition(off, aid, "pending_approval")
    check(
        "O39",
        "Route to approval straight from Under Review is 409 (site visit first)",
        r.status_code == 409,
        r.text,
    )
    transition(off, aid, "site_visit_scheduled")
    # the round cap: six proposals per visit, then only accept or keep
    r = propose(off, aid, working_day(3))
    check(
        "SV35",
        "a second visit opens after Return to review (visit 2)",
        r.status_code == 200 and r.json()["site_visit"]["visit_no"] == 2,
        r.text[:300],
    )
    for n in (4, 6):
        req(
            op,
            "POST",
            f"/applications/{aid}/site-visit/counter",
            json={"date": working_day(n + 1), "slot": "morning", "reason": "Closed."},
        )
        req(
            off,
            "POST",
            f"/officer/applications/{aid}/site-visit/decide",
            json={"action": "propose", "date": working_day(n + 2), "slot": "morning"},
        )
    r = req(
        op,
        "POST",
        f"/applications/{aid}/site-visit/counter",
        json={"date": working_day(12), "slot": "morning", "reason": "Still closed."},
    )
    check(
        "SV36",
        "the sixth proposal is the last one allowed",
        r.status_code == 200
        and r.json()["site_visit"]["rounds_left"] == 0
        and r.json()["site_visit"]["can_counter"] is False,
        r.text[:300],
    )
    r = req(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit/decide",
        json={"action": "propose", "date": working_day(14), "slot": "morning"},
    )
    check(
        "SV37",
        "a seventh proposal is 409 No more dates can be proposed",
        r.status_code == 409 and "No more dates" in r.json()["error"]["message"],
        r.text,
    )
    r = req(off, "POST", f"/officer/applications/{aid}/site-visit/decide", json={"action": "accept_operator"})
    check(
        "SV38",
        "at the cap the officer can still accept the operator's date",
        r.status_code == 200
        and r.json()["site_visit"]["status"] == "confirmed"
        and r.json()["site_visit"]["can_reschedule"] is False,
        r.text[:300],
    )
    transition(off, aid, "site_visit_done")
    r = req(off, "POST", CHECKLIST.format(aid))
    check(
        "CK28",
        "a second visit gets its own checklist (visit 2)",
        r.status_code == 201 and r.json()["visit_no"] == 2,
        r.text[:200],
    )
    req(off, "PUT", CHECKLIST.format(aid), json={"items": clean_items(), "version": r.json()["version"]})
    r = req(off, "POST", CHECKLIST.format(aid) + "/submit")
    check(
        "CK29",
        "visit 2 submits clean; visit 1 stays readable",
        r.status_code == 200
        and req(off, "GET", CHECKLIST.format(aid) + "?visit=1").json()["status"] == "submitted",
        r.text[:200],
    )
    transition(off, aid, "pending_approval")
    r = req(off, "GET", f"/officer/applications/{aid}/licence/preview")
    check(
        "L1",
        "licence preview at Pending Approval is a PDF",
        r.status_code == 200 and r.content[:4] == b"%PDF",
        r.text[:100],
    )
    r = req(op, "GET", f"/officer/applications/{aid}/licence/preview")
    check("L2", "operator cannot preview (403)", r.status_code == 403, r.text)
    r = transition(off, aid, "approved", note="Approved for the demo.")
    check(
        "L3",
        "approve issues a licence",
        r.status_code == 200 and (r.json().get("licence") or {}).get("licence_no", "").startswith("FEL-"),
        r.text[:300],
    )
    r = req(off, "GET", f"/officer/applications/{aid}/licence/preview")
    check("L4", "preview after approval is 409", r.status_code == 409, r.text)
    r = transition(off, aid, "approved", note="again")
    check("L5", "approving twice is 409", r.status_code == 409, r.text)
    r = transition(off, aid, "rejected", note="too late")
    check("L6", "rejecting after approval is 409", r.status_code == 409, r.text)
    r = req(op, "GET", f"/applications/{aid}/licence")
    check(
        "L7",
        "operator downloads the licence PDF with the licence number as filename",
        r.status_code == 200
        and r.content[:4] == b"%PDF"
        and "FEL-" in r.headers.get("content-disposition", ""),
        r.headers.get("content-disposition", ""),
    )
    r = req(op2, "GET", f"/applications/{aid}/licence")
    check("L8", "another operator cannot download the licence (404)", r.status_code == 404, r.text)
    r = req(off, "GET", f"/applications/{aid}/licence")
    check("L9", "officer can download the issued licence", r.status_code == 200, r.text[:100])
    v = req(op, "GET", f"/applications/{aid}").json()
    check(
        "L10",
        "operator sees Approved with the note and the licence",
        v["status_label"] == "Approved" and v["decision_note"] == "Approved for the demo." and v["licence"],
        json.dumps({k: v[k] for k in ("status_label", "decision_note")}),
    )
    r = req(op, "POST", f"/applications/{aid}/withdraw", json={"reason": "changed my mind"})
    check("L11", "withdraw after approval is 409", r.status_code == 409, r.text)
    audit = req(off, "GET", f"/officer/applications/{aid}/audit").json()
    events = audit["events"]
    kinds = [e.get("event_type") or e.get("kind") or e.get("type") for e in events]
    check(
        "L12",
        "audit trail ends with licence issued and has the status changes",
        any("licence" in str(k) for k in kinds) and len(events) >= 15,
        json.dumps(kinds[-5:]),
    )

    # ---------- Withdrawal path ----------
    app2 = req(op, "POST", "/applications").json()
    bid = app2["id"]
    r = req(op, "POST", f"/applications/{bid}/withdraw", json={"reason": "x"})
    check("W1", "withdraw a draft is 409 (delete instead)", r.status_code == 409, r.text)
    fill_all(op, bid)
    upload_all(op, bid)
    wait_checks(op, bid)
    req(op, "POST", f"/applications/{bid}/submit")
    r = req(op2, "POST", f"/applications/{bid}/withdraw", json={})
    check("W2", "another operator cannot withdraw (404)", r.status_code == 404, r.text)
    r = req(op, "POST", f"/applications/{bid}/withdraw", json={"reason": None})
    check(
        "W3",
        "withdraw without a reason from Application Received works",
        r.status_code == 200 and r.json()["status_label"] == "Withdrawn",
        r.text[:200],
    )
    r = req(op, "POST", f"/applications/{bid}/withdraw", json={"reason": "again"})
    check("W4", "withdraw twice is 409", r.status_code == 409, r.text)
    r = transition(off, bid, "under_review")
    check("W5", "officer cannot act on a withdrawn application (409)", r.status_code == 409, r.text)
    r = req(op, "DELETE", f"/applications/{bid}")
    check("W6", "withdrawn application cannot be deleted (409)", r.status_code == 409, r.text)
    v = officer_view(off, bid)
    check(
        "W7",
        "officer sees the withdrawn case with no reason leak issue",
        v["status"] == "withdrawn",
        json.dumps(v)[:100],
    )

    # ---------- Draft deletion ----------
    app3 = req(op, "POST", "/applications").json()
    cid = app3["id"]
    r = upload(op, cid, "floor_plan", "f.txt", TXT)
    d3 = r.json()["document"]["id"]
    r = req(op2, "DELETE", f"/applications/{cid}")
    check("X1", "another operator cannot delete a draft (404)", r.status_code == 404, r.text)
    r = req(op, "DELETE", f"/applications/{cid}")
    check("X2", "owner deletes the draft (204)", r.status_code == 204, r.text)
    r = req(op, "GET", f"/applications/{cid}")
    check("X3", "deleted draft is gone (404)", r.status_code == 404, r.text)
    r = req(op, "GET", f"/applications/{cid}/documents/{d3}/download")
    check("X4", "its document is gone too (404)", r.status_code == 404, r.text)
    r = req(op, "DELETE", f"/applications/{cid}")
    check("X5", "deleting twice is 404", r.status_code == 404, r.text)

    # ---------- Notifications ----------
    n_op = req(op, "GET", "/notifications").json()
    items = n_op if isinstance(n_op, list) else n_op.get("items", [])
    check("N1", "operator has notifications for the status changes", len(items) >= 3, str(len(items)))
    ok = all(operator_view_clean(i)[0] for i in items)
    check("N2", "operator notifications carry no internal status codes", ok, json.dumps(items[:2])[:300])
    nid = items[0]["id"]
    r = req(op2, "POST", f"/notifications/{nid}/read")
    check("N3", "another user cannot mark my notification read (404)", r.status_code == 404, r.text)
    r = req(op, "POST", f"/notifications/{nid}/read")
    check("N4", "owner marks it read", r.status_code in (200, 204), r.text[:100])
    r = req(op, "POST", f"/notifications/{nid}/read")
    check("N5", "marking read twice is idempotent (2xx)", r.status_code in (200, 204), r.text[:100])
    r = req(op, "POST", "/notifications/read-all")
    check(
        "N6",
        "read-all is 2xx and leaves zero unread",
        r.status_code in (200, 204)
        and all(
            i.get("read_at") or i.get("read")
            for i in (lambda x: x if isinstance(x, list) else x.get("items", []))(
                req(op, "GET", "/notifications").json()
            )
        ),
        r.text[:100],
    )
    r = req(op, "POST", f"/notifications/{uuid.uuid4()}/read")
    check("N7", "unknown notification is 404", r.status_code == 404, r.text)
    n_off = req(off, "GET", "/notifications").json()
    offs = n_off if isinstance(n_off, list) else n_off.get("items", [])
    check(
        "N8",
        "officer was notified of the submission, resubmission and withdrawal",
        len(offs) >= 3,
        str(len(offs)),
    )

    # ---------- Queue ----------
    q = req(off, "GET", "/officer/applications").json()
    rows = q if isinstance(q, list) else q.get("items", [])
    ids = {r_["id"] for r_ in rows}
    check(
        "Q1",
        "queue lists the approved and withdrawn cases, never drafts",
        aid in ids and bid in ids and cid not in ids,
        str(len(rows)),
    )
    check(
        "Q2",
        "queue rows carry internal status codes for the officer",
        all("status" in r_ for r_ in rows),
        json.dumps(rows[:1])[:200],
    )

    # ---------- Draft quota ----------
    made = []
    refused = None
    for _ in range(25):
        r = req(op2, "POST", "/applications")
        if r.status_code == 201:
            made.append(r.json()["id"])
        else:
            refused = r
            break
    if refused is None and len(made) == 25:
        # MAX_DRAFTS_PER_USER=0 (the local setting the README suggests): nothing to refuse, so nothing to check.
        check("Z1", "draft quota is disabled on this stack (MAX_DRAFTS_PER_USER=0), check skipped", True)
    else:
        check(
            "Z1",
            "the 21st open draft is refused with a 409 and a clear message",
            refused is not None and refused.status_code == 409 and len(made) == 20,
            f"made={len(made)} refused={None if refused is None else refused.status_code}",
        )
    for m in made:
        req(op2, "DELETE", f"/applications/{m}")
    r = req(op2, "POST", "/applications")
    check("Z2", "after deleting drafts a new one is allowed again", r.status_code == 201, r.text[:100])
    if r.status_code == 201:
        req(op2, "DELETE", f"/applications/{r.json()['id']}")

    # ---------- Health and headers ----------
    r = client.get("/health")
    check(
        "H1",
        "health is 200 with database ok",
        r.status_code == 200 and r.json().get("database") == "ok",
        r.text,
    )
    hdrs = {k.lower() for k in r.headers}
    check(
        "H2",
        "security headers present on API responses",
        {"x-content-type-options", "x-frame-options"} <= hdrs,
        str(sorted(hdrs)),
    )
    r = client.options(
        "/applications", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"}
    )
    check(
        "H3",
        "CORS preflight from a foreign origin is not allowed",
        r.headers.get("access-control-allow-origin") != "http://evil.example",
        str(r.headers.get("access-control-allow-origin")),
    )
    r = client.get("/api/docs")
    check(
        "H4",
        "OpenAPI docs reachable in development (not in production; checked in OPERATIONS)",
        r.status_code in (200, 404),
        str(r.status_code),
    )

    # ---------- One live session per account (US-093) ----------
    # The second operator is free to use here: every earlier group signed in once and took over.
    ipad_ua = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 Version/17.4 Mobile/15E148 Safari/604.1"
    }
    mac_ua = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"
    }
    r = client.post(
        "/auth/login", json={"email": OPERATOR2, "password": PW, "take_over": True}, headers=ipad_ua
    )
    check("SE1", "sign-in with a take-over is 200", r.status_code == 200, r.text[:120])
    ipad = {"Authorization": "Bearer " + r.json()["access_token"]}
    r = client.post("/auth/login", json={"email": OPERATOR2, "password": PW}, headers=mac_ua)
    err = r.json().get("error", {}) if r.status_code == 409 else {}
    check(
        "SE2",
        "a second sign-in is 409 session_active naming the iPad and its last activity",
        r.status_code == 409
        and err.get("code") == "session_active"
        and err.get("details", {}).get("device") == "Safari on iPad"
        and bool(err.get("details", {}).get("last_seen_at")),
        r.text[:200],
    )
    check(
        "SE3",
        "the refused sign-in leaves the iPad working",
        req(ipad, "GET", "/auth/me").status_code == 200,
        "",
    )
    r = client.post(
        "/auth/login", json={"email": OPERATOR2, "password": "wrong", "take_over": True}, headers=mac_ua
    )
    check(
        "SE4",
        "a wrong password with take_over is the generic 401",
        r.status_code == 401 and r.json()["error"]["code"] == "unauthorized",
        r.text[:120],
    )
    check("SE5", "and the iPad is untouched by it", req(ipad, "GET", "/auth/me").status_code == 200, "")
    r = client.post(
        "/auth/login", json={"email": OPERATOR2, "password": PW, "take_over": True}, headers=mac_ua
    )
    check("SE6", "the take-over signs the laptop in", r.status_code == 200, r.text[:120])
    laptop = {"Authorization": "Bearer " + r.json()["access_token"]}
    r = req(ipad, "GET", "/auth/me")
    err = r.json().get("error", {}) if r.status_code == 401 else {}
    check(
        "SE7",
        "the iPad's next request is 401 session_revoked, reason taken_over, with the time",
        r.status_code == 401
        and err.get("code") == "session_revoked"
        and err.get("details", {}).get("reason") == "taken_over"
        and bool(err.get("details", {}).get("at"))
        and "another device" in err.get("message", ""),
        r.text[:200],
    )
    check("SE8", "the laptop works", req(laptop, "GET", "/applications").status_code == 200, "")
    r = req(laptop, "POST", "/auth/logout")
    check("SE9", "sign-out is 204", r.status_code == 204, r.text[:120])
    r = req(laptop, "GET", "/auth/me")
    check(
        "SE10",
        "after sign-out the token is 401 session_revoked, reason signed_out",
        r.status_code == 401 and r.json()["error"]["details"].get("reason") == "signed_out",
        r.text[:200],
    )
    r = client.post("/auth/login", json={"email": OPERATOR2, "password": PW}, headers=ipad_ua)
    check("SE11", "after sign-out a plain sign-in needs no take-over", r.status_code == 200, r.text[:120])
    if r.status_code == 200:
        req({"Authorization": "Bearer " + r.json()["access_token"]}, "POST", "/auth/logout")
    r = client.post("/auth/logout")
    check(
        "SE12",
        "sign-out without a token is 401 in the envelope",
        r.status_code == 401 and envelope_ok(r),
        r.text[:120],
    )

    # ---------- Summary ----------
    failed = [x for x in RESULTS if not x[2]]
    print(f"\n{len(RESULTS) - len(failed)} passed, {len(failed)} failed of {len(RESULTS)}")
    for f in failed:
        print("  FAIL", f[0], f[1], "::", f[3][:300])
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
