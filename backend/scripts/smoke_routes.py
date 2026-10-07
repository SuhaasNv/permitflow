"""Route-coverage smoke test (21 Sep 2026): every route in the OpenAPI document is called at least once
with the right role on a real lifecycle, plus wrong-role and unauthenticated probes. Uses the spare officer
(officer2), the administrator, and a fresh operator created through the admin endpoint, so the demo
operator's and the main officer's sessions are left alone. The operator it creates is deactivated at the end.

    cd backend && uv run python scripts/smoke_routes.py      # UAT_API_URL for another host

Run it with the per-client limits and the daily check quotas off (see OPERATIONS.md); never against
production (it creates applications and an account). Exit 1 on any failed check or an uncalled route."""

from __future__ import annotations

import datetime as dt
import json
import os
import struct
import sys
import time
import zlib

import httpx

API = os.environ.get("UAT_API_URL", "http://localhost:8000/api/v1")
PW = os.environ.get("SEED_PASSWORD", "PermitFlow!2026")
ADMIN = "admin@permitflow.example.sg"
OFFICER2 = "officer2@permitflow.example.sg"
NEW_OP_PW = "Smoke-Run-Only-2026!"

client = httpx.Client(base_url=API, timeout=60)
covered: dict[tuple[str, str], list[int]] = {}
results: list[tuple[str, bool, str]] = []
TXT = (
    "Tenancy agreement between landlord and tenant. Business profile ACRA UEN. Floor plan kitchen. "
    "Food hygiene certificate. " * 3
)
TXT_BYTES = TXT.encode()


def tiny_png() -> bytes:
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    raw = b"\x00" + b"\xff\x00\x00" * 4
    ihdr = struct.pack(">IIBBBBB", 4, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    )


def note(route: str, ok: bool, msg: str = "") -> None:
    results.append((route, ok, msg))
    print(("PASS " if ok else "FAIL ") + route + ("  :: " + msg if msg else ""))


def call(h: dict | None, method: str, path: str, template: str, expect, **kw) -> httpx.Response:
    r = client.request(method, path, headers=h or {}, **kw)
    covered.setdefault((method, template), []).append(r.status_code)
    exp = expect if isinstance(expect, (tuple, list, set)) else (expect,)
    body = ""
    if r.status_code not in exp:
        body = r.text[:200]
    note(
        f"{method} {template} -> {r.status_code}",
        r.status_code in exp,
        "" if r.status_code in exp else f"expected {exp}: {body}",
    )
    return r


def login(email: str, pw: str = PW) -> dict:
    r = client.post("/auth/login", json={"email": email, "password": pw, "take_over": True})
    covered.setdefault(("POST", "/auth/login"), []).append(r.status_code)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def working_day(n: int) -> str:
    d = dt.date.today()
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d.isoformat()


def upload(h, app_id, dtype, name=None, content=TXT_BYTES, mime="text/plain"):
    return call(
        h,
        "POST",
        f"/applications/{app_id}/documents",
        "/applications/{application_id}/documents",
        (201, 200),
        data={"document_type": dtype},
        files={"file": (name or f"{dtype}.txt", content, mime)},
    )


def docs_of(v: dict) -> list[dict]:
    return [slot["document"] for slot in v.get("document_slots", []) if slot.get("document")]


def wait_checks(h, app_id, timeout=40):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = client.get(f"/applications/{app_id}", headers=h).json()
        docs = docs_of(v)
        states = [(d.get("verification") or {}).get("status") for d in docs]
        if docs and all(s not in (None, "pending", "queued", "running") for s in states):
            return v
        time.sleep(1)
    return client.get(f"/applications/{app_id}", headers=h).json()


def main() -> None:
    # ---- public ----
    call(None, "GET", "/health", "/health", 200)
    call(None, "GET", "/form-schema", "/form-schema", (200, 401))
    call(None, "GET", "/checklist-schema", "/checklist-schema", (200, 401))

    # ---- admin: create a fresh operator ----
    adm = login(ADMIN)
    call(adm, "GET", "/auth/me", "/auth/me", 200)
    stamp = int(time.time())
    email = f"smoke{stamp}@permitflow.example.sg"
    r = call(
        adm,
        "POST",
        "/admin/users",
        "/admin/users",
        (201, 200),
        json={"email": email, "full_name": "Smoke Operator", "role": "operator", "password": NEW_OP_PW},
    )
    new_user_id = r.json()["id"]
    users = call(adm, "GET", "/admin/users", "/admin/users", 200).json()
    ids = [
        u["id"] for u in (users if isinstance(users, list) else users.get("users", users.get("items", [])))
    ]
    note("new operator listed on /admin/users", new_user_id in ids)
    call(adm, "GET", "/admin/overview", "/admin/overview", 200)
    feed = call(adm, "GET", "/admin/audit-feed?limit=5", "/admin/audit-feed", 200).json()
    cursor = feed.get("next_before") or feed.get("next") or feed.get("cursor")
    if cursor:
        call(adm, "GET", f"/admin/audit-feed?limit=5&before={cursor}", "/admin/audit-feed", 200)
    # admin guards
    me = client.get("/auth/me", headers=adm).json()
    call(adm, "PATCH", f"/admin/users/{me['id']}", "/admin/users/{user_id}", 409, json={"is_active": False})

    # ---- operator lifecycle ----
    op = login(email, NEW_OP_PW)
    call(op, "GET", "/auth/me", "/auth/me", 200)
    call(op, "GET", "/form-schema", "/form-schema", 200)
    app = call(op, "POST", "/applications", "/applications", (201, 200)).json()
    aid = app["id"]
    sections = {
        "business": {
            "business_name": "Smoke Kopi Pte. Ltd.",
            "uen": "202388888S",
            "contact_name": "Smoke Operator",
            "contact_email": "smoke@uat.sg",
            "contact_phone": "+65 9123 0000",
            "entity_type": "private_limited",
        },
        "premises": {
            "address_line_1": "11 Jalan Besar #01-13",
            "postal_code": "208787",
            "floor_area_sqm": 40,
            "tenancy_expiry": "2027-10-31",
            "premises_type": "shophouse",
        },
        "operations": {
            "cuisine_description": "Kopi and toast.",
            "seating_capacity": 20,
            "operating_hours": "Mon-Sun 7am-9pm",
            "food_handlers_count": 3,
        },
        "declarations": {"information_accurate": True, "consent_to_inspection": True},
    }
    for k, v in sections.items():
        call(
            op,
            "PATCH",
            f"/applications/{aid}/sections/{k}",
            "/applications/{application_id}/sections/{key}",
            200,
            json=v,
        )
    for t in ["business_profile", "floor_plan", "tenancy_agreement", "food_hygiene_certificate"]:
        upload(op, aid, t)
    view = wait_checks(op, aid)
    first = docs_of(view)[0]
    doc_id = first["id"]
    call(
        op,
        "GET",
        f"/applications/{aid}/documents/{doc_id}/download",
        "/applications/{application_id}/documents/{document_id}/download",
        200,
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/documents/{doc_id}/verify",
        "/applications/{application_id}/documents/{document_id}/verify",
        (200, 202, 409),
    )
    time.sleep(2)
    # delete a document and re-upload it
    call(
        op,
        "DELETE",
        f"/applications/{aid}/documents/{doc_id}",
        "/applications/{application_id}/documents/{document_id}",
        (204, 200),
    )
    upload(op, aid, first["document_type"])
    wait_checks(op, aid)
    call(op, "GET", "/applications", "/applications", 200)
    call(op, "GET", f"/applications/{aid}", "/applications/{application_id}", 200)
    call(op, "POST", f"/applications/{aid}/submit", "/applications/{application_id}/submit", 200)

    # ---- officer ----
    off = login(OFFICER2)
    call(off, "GET", "/officer/applications", "/officer/applications", 200)
    ov = call(
        off, "GET", f"/officer/applications/{aid}", "/officer/applications/{application_id}", 200
    ).json()
    call(
        off, "GET", f"/officer/applications/{aid}/audit", "/officer/applications/{application_id}/audit", 200
    )
    call(off, "GET", "/officer/feedback-templates", "/officer/feedback-templates", 200)
    ov = call(
        off,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        200,
        json={"target": "under_review", "expected_version": ov["version"]},
    ).json()
    odoc = ov["documents"][0]["id"]
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/documents/{odoc}/verify",
        "/officer/applications/{application_id}/documents/{document_id}/verify",
        (200, 202, 409),
    )
    time.sleep(2)
    fb = call(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback",
        "/officer/applications/{application_id}/feedback",
        (201, 200),
        json={
            "target_type": "section",
            "section_key": "premises",
            "message": "Please confirm the floor area.",
        },
    ).json()
    fid = (fb.get("feedback") or [fb])[-1]["id"]
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback/{fid}/withdraw",
        "/officer/applications/{application_id}/feedback/{feedback_id}/withdraw",
        200,
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback/{fid}/restore",
        "/officer/applications/{application_id}/feedback/{feedback_id}/restore",
        200,
    )
    ov = client.get(f"/officer/applications/{aid}", headers=off).json()
    ov = call(
        off,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        200,
        json={"target": "pending_pre_site_resubmission", "expected_version": ov["version"]},
    ).json()
    # operator fixes the flagged section and resubmits
    call(
        op,
        "PATCH",
        f"/applications/{aid}/sections/premises",
        "/applications/{application_id}/sections/{key}",
        200,
        json={**sections["premises"], "floor_area_sqm": 42},
    )
    call(op, "POST", f"/applications/{aid}/resubmit", "/applications/{application_id}/resubmit", 200)
    call(op, "GET", f"/applications/{aid}/compare?from=1&to=2", "/applications/{application_id}/compare", 200)
    call(
        op,
        "GET",
        f"/applications/{aid}/compare?from=2&to=9",
        "/applications/{application_id}/compare",
        (404, 422),
    )
    ov = client.get(f"/officer/applications/{aid}", headers=off).json()
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback/{fid}/reopen",
        "/officer/applications/{application_id}/feedback/{feedback_id}/reopen",
        (200, 409),
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/feedback/{fid}/resolve",
        "/officer/applications/{application_id}/feedback/{feedback_id}/resolve",
        200,
    )
    ov = client.get(f"/officer/applications/{aid}", headers=off).json()
    if ov["status"] != "under_review":
        ov = call(
            off,
            "POST",
            f"/officer/applications/{aid}/transition",
            "/officer/applications/{application_id}/transition",
            200,
            json={"target": "under_review", "expected_version": ov["version"]},
        ).json()
    # appointment
    ov = call(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit",
        "/officer/applications/{application_id}/site-visit",
        (200, 201),
        json={
            "date": working_day(3),
            "slot": "morning",
            "note": "Kitchen operating.",
            "expected_version": ov["version"],
        },
    ).json()
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit/confirm",
        "/officer/applications/{application_id}/site-visit/confirm",
        409,
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/site-visit/counter",
        "/applications/{application_id}/site-visit/counter",
        200,
        json={"date": working_day(4), "slot": "afternoon", "reason": "Supplier delivery in the morning."},
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit/decide",
        "/officer/applications/{application_id}/site-visit/decide",
        200,
        json={"action": "accept_operator"},
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/site-visit/reschedule",
        "/applications/{application_id}/site-visit/reschedule",
        200,
        json={"date": working_day(5), "slot": "morning", "reason": "Tiler on site."},
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit/decide",
        "/officer/applications/{application_id}/site-visit/decide",
        200,
        json={"action": "keep_original"},
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit/reschedule",
        "/officer/applications/{application_id}/site-visit/reschedule",
        200,
        json={"date": working_day(6), "slot": "afternoon", "reason": "Officer roster."},
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/site-visit/accept",
        "/applications/{application_id}/site-visit/accept",
        200,
    )
    # checklist
    cl = call(
        off,
        "POST",
        f"/officer/applications/{aid}/checklist",
        "/officer/applications/{application_id}/checklist",
        (200, 201),
    ).json()
    items = []
    for i, it in enumerate(cl["items"]):
        entry = {"key": it["key"], "result": "satisfactory", "comment": None, "needs_clarification": False}
        if i < 2:
            entry.update(
                {"result": "unsatisfactory", "comment": f"Finding {i + 1}.", "needs_clarification": True}
            )
        items.append(entry)
    items.append(
        {
            "key": None,
            "result": "unsatisfactory",
            "comment": "Extra finding.",
            "needs_clarification": False,
            "custom_title": "Loose tiles",
        }
    )
    cl = call(
        off,
        "PUT",
        f"/officer/applications/{aid}/checklist",
        "/officer/applications/{application_id}/checklist",
        200,
        json={"items": items, "version": cl["version"], "save_id": "smoke-1"},
    ).json()
    call(
        off,
        "GET",
        f"/officer/applications/{aid}/checklist",
        "/officer/applications/{application_id}/checklist",
        200,
    )
    call(adm, "GET", f"/admin/applications/{aid}", "/admin/applications/{application_id}", 200)
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/checklist/submit",
        "/officer/applications/{application_id}/checklist/submit",
        200,
    )
    # clarifications
    cv = call(
        op, "GET", f"/applications/{aid}/clarifications", "/applications/{application_id}/clarifications", 200
    ).json()
    open_items = [i for i in cv["items"] if i.get("can_respond")]
    note("two flagged items reached the operator", len(open_items) == 2, str(len(open_items)))
    i1, i2 = open_items[0]["item_id"], open_items[1]["item_id"]
    ov2 = client.get(f"/officer/applications/{aid}", headers=off).json()
    # officer withdraws the second question before the operator answers
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i2}/withdraw",
        "/officer/applications/{application_id}/clarifications/{item_id}/withdraw",
        200,
    )
    # undo inside the window (UAT run 5, F19), then withdraw again so the flow below is unchanged
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i2}/restore",
        "/officer/applications/{application_id}/clarifications/{item_id}/restore",
        200,
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i2}/withdraw",
        "/officer/applications/{application_id}/clarifications/{item_id}/withdraw",
        200,
    )
    cv = call(
        op,
        "POST",
        f"/applications/{aid}/clarifications/{i1}/responses",
        "/applications/{application_id}/clarifications/{item_id}/responses",
        (200, 201),
        json={"message": "Fixed on 22 Sep."},
    ).json()
    resp = [r for it in cv["items"] for r in it["responses"] if r.get("sent_at") is None]
    rid = resp[-1]["id"]
    att = call(
        op,
        "POST",
        f"/applications/{aid}/clarifications/responses/{rid}/attachments",
        "/applications/{application_id}/clarifications/responses/{response_id}/attachments",
        (200, 201),
        files={"file": ("photo.png", tiny_png(), "image/png")},
    ).json()
    view = att.get("view", att)
    atts = [a for it in view["items"] for r in it["responses"] for a in r.get("attachments", [])]
    att_id = atts[-1]["id"]
    call(
        op,
        "GET",
        f"/applications/{aid}/clarifications/attachments/{att_id}/download",
        "/applications/{application_id}/clarifications/attachments/{attachment_id}/download",
        200,
    )
    call(
        op,
        "DELETE",
        f"/applications/{aid}/clarifications/responses/{rid}/attachments/{att_id}",
        "/applications/{application_id}/clarifications/responses/{response_id}/attachments/{attachment_id}",
        (200, 204),
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/clarifications/responses/{rid}/attachments",
        "/applications/{application_id}/clarifications/responses/{response_id}/attachments",
        (200, 201),
        files={"file": ("photo.png", tiny_png(), "image/png")},
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/clarifications/send",
        "/applications/{application_id}/clarifications/send",
        200,
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i1}/reopen",
        "/officer/applications/{application_id}/clarifications/{item_id}/reopen",
        200,
        json={"message": "Send a photo of the repair."},
    )
    ov2 = client.get(f"/officer/applications/{aid}", headers=off).json()
    ov2 = call(
        off,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        200,
        json={"target": "pending_post_site_resubmission", "expected_version": ov2["version"]},
    ).json()
    call(
        op,
        "POST",
        f"/applications/{aid}/clarifications/{i1}/responses",
        "/applications/{application_id}/clarifications/{item_id}/responses",
        (200, 201),
        json={"message": "Photo attached."},
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/clarifications/send",
        "/applications/{application_id}/clarifications/send",
        200,
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i1}/resolve",
        "/officer/applications/{application_id}/clarifications/{item_id}/resolve",
        200,
    )
    ov2 = client.get(f"/officer/applications/{aid}", headers=off).json()
    ov2 = call(
        off,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        200,
        json={"target": "pending_approval", "expected_version": ov2["version"]},
    ).json()
    # ---- second visit after Return to review (UAT run 5, F15 to F18) ----
    ov2 = call(
        off,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        200,
        json={"target": "under_review", "expected_version": ov2["version"]},
    ).json()
    note(
        "back in review: no active visit, visit 1 kept as history, feedback open",
        ov2["site_visit"] is None
        and ov2["clarification"] is None
        and ov2["feedback_editable"] is True
        and [v["visit_no"] for v in ov2.get("earlier_visits", [])] == [1],
        str([v["visit_no"] for v in ov2.get("earlier_visits", [])]),
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/site-visit",
        "/officer/applications/{application_id}/site-visit",
        (200, 201),
        json={"date": working_day(4), "slot": "afternoon", "expected_version": ov2["version"]},
    )
    mine = client.get(f"/applications/{aid}", headers=op).json()
    note(
        "operator sees visit 2 and can answer it",
        (mine.get("site_visit") or {}).get("visit_no") == 2 and mine["site_visit"]["can_accept"] is True,
        str(mine.get("site_visit")),
    )
    past = client.get(f"/applications/{aid}/clarifications?visit=1", headers=op).json()
    note(
        "visit 1 clarification readable, read-only",
        past.get("visit_no") == 1 and len(past.get("items", [])) >= 1 and past.get("can_respond") is False,
    )
    call(
        op,
        "POST",
        f"/applications/{aid}/site-visit/accept",
        "/applications/{application_id}/site-visit/accept",
        200,
    )
    cl2 = call(
        off,
        "POST",
        f"/officer/applications/{aid}/checklist",
        "/officer/applications/{application_id}/checklist",
        (200, 201),
    ).json()
    note("visit 2 checklist starts blank", cl2["visit_no"] == 2 and cl2["counts"]["assessed"] == 0)
    first = client.get(f"/officer/applications/{aid}/checklist?visit=1", headers=off).json()
    note(
        "visit 1 checklist readable by number",
        first.get("visit_no") == 1 and first.get("status") == "submitted",
    )
    clean = [
        {"key": it["key"], "result": "satisfactory", "comment": None, "needs_clarification": False}
        for it in cl2["items"]
    ]
    call(
        off,
        "PUT",
        f"/officer/applications/{aid}/checklist",
        "/officer/applications/{application_id}/checklist",
        200,
        json={"items": clean, "version": cl2["version"]},
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/checklist/submit",
        "/officer/applications/{application_id}/checklist/submit",
        200,
    )
    ov2 = client.get(f"/officer/applications/{aid}", headers=off).json()
    ov2 = call(
        off,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        200,
        json={"target": "pending_approval", "expected_version": ov2["version"]},
    ).json()
    call(
        off,
        "GET",
        f"/officer/applications/{aid}/licence/preview",
        "/officer/applications/{application_id}/licence/preview",
        200,
    )
    ov2 = call(
        off,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        200,
        json={"target": "approved", "note": "Smoke approval.", "expected_version": ov2["version"]},
    ).json()
    call(op, "GET", f"/applications/{aid}/licence", "/applications/{application_id}/licence", 200)
    call(adm, "GET", f"/admin/applications/{aid}", "/admin/applications/{application_id}", 200)
    # notifications
    n = call(op, "GET", "/notifications", "/notifications", 200).json()
    nid = (n.get("notifications") or n.get("items") or [{}])[0].get("id")
    if nid:
        call(op, "POST", f"/notifications/{nid}/read", "/notifications/{notification_id}/read", 200)
    call(op, "POST", "/notifications/read-all", "/notifications/read-all", 200)
    # withdraw and delete-draft on two more applications
    a2 = call(op, "POST", "/applications", "/applications", (201, 200)).json()["id"]
    for k, v in sections.items():
        client.patch(f"/applications/{a2}/sections/{k}", headers=op, json=v)
    for t in ["business_profile", "floor_plan", "tenancy_agreement", "food_hygiene_certificate"]:
        client.post(
            f"/applications/{a2}/documents",
            headers=op,
            data={"document_type": t},
            files={"file": (f"{t}.txt", TXT.encode(), "text/plain")},
        )
    wait_checks(op, a2)
    call(op, "POST", f"/applications/{a2}/submit", "/applications/{application_id}/submit", 200)
    call(
        op,
        "POST",
        f"/applications/{a2}/withdraw",
        "/applications/{application_id}/withdraw",
        200,
        json={"reason": "Smoke run."},
    )
    a3 = client.post("/applications", headers=op).json()["id"]
    call(op, "DELETE", f"/applications/{a3}", "/applications/{application_id}", (204, 200))

    # ---- wrong-role and unauthenticated probes ----
    call(op, "GET", "/officer/applications", "/officer/applications", 403)
    call(
        op,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i2}/restore",
        "/officer/applications/{application_id}/clarifications/{item_id}/restore",
        403,
    )
    call(
        None,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i2}/restore",
        "/officer/applications/{application_id}/clarifications/{item_id}/restore",
        401,
    )
    call(
        off,
        "POST",
        f"/officer/applications/{aid}/clarifications/{i2}/restore",
        "/officer/applications/{application_id}/clarifications/{item_id}/restore",
        409,
    )
    call(op, "GET", f"/officer/applications/{aid}", "/officer/applications/{application_id}", 403)
    call(op, "GET", "/admin/overview", "/admin/overview", 403)
    call(off, "GET", "/applications", "/applications", 403)
    call(off, "GET", "/admin/users", "/admin/users", 403)
    call(
        adm,
        "POST",
        f"/officer/applications/{aid}/transition",
        "/officer/applications/{application_id}/transition",
        403,
        json={"target": "rejected", "note": "x", "expected_version": 1},
    )
    call(
        adm,
        "PUT",
        f"/officer/applications/{aid}/checklist",
        "/officer/applications/{application_id}/checklist",
        403,
        json={"items": [], "version": 1},
    )
    call(adm, "POST", "/applications", "/applications", 403)
    call(None, "GET", "/applications", "/applications", 401)
    call(None, "GET", "/officer/applications", "/officer/applications", 401)
    call(None, "GET", "/admin/overview", "/admin/overview", 401)
    call(None, "GET", "/notifications", "/notifications", 401)
    call(None, "GET", "/auth/me", "/auth/me", 401)

    # ---- logout ----
    call(off, "POST", "/auth/logout", "/auth/logout", (200, 204))
    call(off, "GET", "/auth/me", "/auth/me", 401)
    call(op, "POST", "/auth/logout", "/auth/logout", (200, 204))
    # deactivate the smoke operator, then reactivate to prove both halves, then deactivate for good
    call(
        adm, "PATCH", f"/admin/users/{new_user_id}", "/admin/users/{user_id}", 200, json={"is_active": False}
    )
    r = client.post("/auth/login", json={"email": email, "password": NEW_OP_PW, "take_over": True})
    note("deactivated operator cannot sign in (401)", r.status_code == 401, str(r.status_code))
    call(adm, "PATCH", f"/admin/users/{new_user_id}", "/admin/users/{user_id}", 200, json={"is_active": True})
    call(
        adm, "PATCH", f"/admin/users/{new_user_id}", "/admin/users/{user_id}", 200, json={"is_active": False}
    )
    call(adm, "POST", "/auth/logout", "/auth/logout", (200, 204))

    # ---- coverage against the OpenAPI document ----
    spec = httpx.get(API.replace("/api/v1", "") + "/api/openapi.json", timeout=30).json()
    missing = []
    for path, ops in spec["paths"].items():
        t = path.replace("/api/v1", "")
        for m in ops:
            if (m.upper(), t) not in covered:
                missing.append(f"{m.upper()} {t}")
    total = sum(len(ops) for ops in spec["paths"].values())
    print()
    print(f"routes in the OpenAPI document: {total}; called: {total - len(missing)}; missing: {missing}")
    failed = [r for r in results if not r[1]]
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed of {len(results)}")
    for r in failed:
        print("  FAIL", r[0], r[2])
    print(json.dumps({"application": aid, "operator": email}))
    sys.exit(1 if failed or missing else 0)


if __name__ == "__main__":
    main()
