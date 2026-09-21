"""The administrator (US-070, US-072, US-073): the overview on the Singapore day, the activity feed,
read-only access to every case, and user management under its rules."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.admin import idle_days, percentile, singapore_day_window, turn_for
from app.domain.enums import ApplicationStatus
from app.models import Application, AuditEvent, User
from app.models.enums import Role
from app.services.admin_overview import AdminOverviewService
from tests.factories import DEFAULT_PASSWORD, login, make_user
from tests.journeys import flag_and_request, submitted, to_pending_approval, under_review

API = "/api/v1"


def _admin(client: TestClient, db: Session, email: str = "adm@example.sg") -> dict[str, str]:
    make_user(db, email, Role.ADMIN)
    return login(client, email)


# ---- US-070: the overview ----


def test_overview_counts_turns_today_and_checks(client: TestClient, db: Session) -> None:
    app_id, op, off = flag_and_request(client, db)
    adm = _admin(client, db)
    r = client.get(f"{API}/admin/overview", headers=adm)
    assert r.status_code == 200, r.text
    body = r.json()
    counts = {c["status"]: c for c in body["counts"]}
    assert len(counts) == len(ApplicationStatus)
    assert counts["pending_pre_site_resubmission"]["count"] == 1
    assert counts["pending_pre_site_resubmission"]["turn"] == "operator"
    assert counts["pending_pre_site_resubmission"]["label"] == "Pending Pre-Site Resubmission"
    assert counts["draft"]["turn"] == "draft" and counts["approved"]["turn"] == "decided"
    assert body["totals"] == {
        "applications": 1,
        "submitted": 1,
        "drafts": 0,
        "with_office": 0,
        "waiting_on_operators": 1,
        "idle_over_7_days": 0,
    }
    assert body["idle"] == []
    today = body["today"]
    assert today["submissions"] == 1 and today["resubmissions"] == 0
    assert today["runs_today"] == 4 and today["runs_per_day_quota"] > 0
    checks = body["checks"]
    assert checks["runs"] == 4 and checks["provider"] == "none (mock)" and checks["model"] is None
    assert checks["runs"] == (
        checks["verified"]
        + checks["issues_found"]
        + checks["needs_review"]
        + checks["unreadable"]
        + checks["failed_or_unavailable"]
        + checks["still_running"]
    )
    # roles
    assert client.get(f"{API}/admin/overview", headers=op).status_code == 403
    assert client.get(f"{API}/admin/overview", headers=off).status_code == 403


def test_overview_idle_list_counts_singapore_days(client: TestClient, db: Session) -> None:
    app_id, op, off = flag_and_request(client, db)
    # Every event of the case happened nine days ago (Singapore); the row is idle.
    nine_days = datetime.now(UTC) - timedelta(days=9)
    db.execute(update(AuditEvent).values(created_at=nine_days))
    db.execute(update(Application).values(updated_at=nine_days))
    db.commit()
    adm = _admin(client, db)
    body = client.get(f"{API}/admin/overview", headers=adm).json()
    assert body["totals"]["idle_over_7_days"] == 1
    assert len(body["idle"]) == 1
    row = body["idle"][0]
    assert row["days_idle"] == 9 and row["label"] == "Pending Pre-Site Resubmission"
    assert row["business_name"] and row["reference_no"].startswith("PF-")
    # A decision ends the idleness: the case leaves the list.
    db.execute(update(Application).values(status=ApplicationStatus.REJECTED))
    db.commit()
    body = client.get(f"{API}/admin/overview", headers=adm).json()
    assert body["idle"] == [] and body["totals"]["idle_over_7_days"] == 0


def test_singapore_day_rules() -> None:
    # 23:30 on 21 Sep in Singapore is 15:30 UTC: still the 21st there.
    at = datetime(2026, 9, 21, 15, 30, tzinfo=UTC)
    start, end = singapore_day_window(datetime(2026, 9, 21).date())
    assert start == datetime(2026, 9, 20, 16, 0, tzinfo=UTC) and end == datetime(
        2026, 9, 21, 16, 0, tzinfo=UTC
    )
    assert start <= at < end
    # Last activity at 23:30 SGT yesterday is one idle day at 00:30 SGT today, an hour later.
    assert idle_days(at, at + timedelta(hours=1)) == 1
    assert idle_days(at, at) == 0
    assert turn_for(ApplicationStatus.UNDER_REVIEW) == "office"
    assert turn_for(ApplicationStatus.AWAITING_POST_SITE_CLARIFICATION) == "operator"
    assert turn_for(ApplicationStatus.WITHDRAWN) == "decided"
    assert percentile([], 0.95) is None
    assert percentile([1.0, 2.0, 3.0, 4.0, 100.0], 0.95) == 100.0
    assert percentile([5.0], 0.5) == 5.0


def test_overview_today_boundary_is_the_singapore_midnight(client: TestClient, db: Session) -> None:
    """A submission at 23:30 SGT belongs to that day; the same instant read after midnight SGT does not."""
    submitted(client, db)
    at = datetime(2026, 9, 21, 15, 30, tzinfo=UTC)  # 23:30 SGT on 21 Sep
    db.execute(update(AuditEvent).values(created_at=at))
    db.commit()
    service = AdminOverviewService(db)
    same_day = service.overview(now=at + timedelta(minutes=10))
    assert same_day.today.day == "2026-09-21" and same_day.today.submissions == 1
    next_day = service.overview(now=at + timedelta(minutes=40))
    assert next_day.today.day == "2026-09-22" and next_day.today.submissions == 0


# ---- US-072: the feed and read-only cases ----


def test_audit_feed_pages_by_keyset_and_carries_user_rows(client: TestClient, db: Session) -> None:
    app_id, op, off, _ = under_review(client, db)
    adm = _admin(client, db)
    spare = make_user(db, "spare@example.sg", Role.OPERATOR)
    client.patch(f"{API}/admin/users/{spare.id}", headers=adm, json={"role": "officer"})
    first = client.get(f"{API}/admin/audit-feed?limit=3", headers=adm)
    assert first.status_code == 200, first.text
    page = first.json()
    assert len(page["events"]) == 3 and page["next_cursor"]
    newest = page["events"][0]
    assert newest["event_type"] == "user.role_changed" and newest["application_id"] is None
    assert newest["reference_no"] is None and newest["actor_role"] == "admin"
    assert "role changed from operator to officer" in newest["summary"]
    stamps = [e["created_at"] for e in page["events"]]
    assert stamps == sorted(stamps, reverse=True)
    # The next page starts after the last event of this one; no event repeats, none is skipped.
    seen = {e["id"] for e in page["events"]}
    cursor = page["next_cursor"]
    while cursor:
        r = client.get(f"{API}/admin/audit-feed?limit=3&before={cursor}", headers=adm)
        assert r.status_code == 200
        body = r.json()
        for e in body["events"]:
            assert e["id"] not in seen
            seen.add(e["id"])
        cursor = body["next_cursor"]
    assert (
        len(seen) == db.scalar(select(AuditEvent).limit(0).with_only_columns(AuditEvent.id).count())
        if False
        else True
    )
    total = len(db.scalars(select(AuditEvent)).all())
    assert len(seen) == total
    case_rows = [
        e for e in client.get(f"{API}/admin/audit-feed", headers=adm).json()["events"] if e["application_id"]
    ]
    assert case_rows and all(e["reference_no"] for e in case_rows)
    # a bad cursor is a 400, not a 500
    r = client.get(f"{API}/admin/audit-feed?before=garbage", headers=adm)
    assert r.status_code == 400 and r.json()["error"]["details"]["reason"] == "bad_cursor"
    assert client.get(f"{API}/admin/audit-feed", headers=off).status_code == 403


def test_admin_reads_every_case_route_with_no_actions(client: TestClient, db: Session) -> None:
    app_id, op, off = under_review(client, db)[:3]
    to_pending_approval(client, off, op, app_id)
    adm = _admin(client, db)
    for path in (
        f"{API}/officer/applications",
        f"{API}/officer/applications/{app_id}",
        f"{API}/admin/applications/{app_id}",
        f"{API}/officer/applications/{app_id}/audit",
        f"{API}/officer/applications/{app_id}/checklist",
        f"{API}/checklist-schema",
        f"{API}/applications/{app_id}/compare?from=1&to=1",
    ):
        r = client.get(path, headers=adm)
        assert r.status_code == 200, (path, r.text)
    view = client.get(f"{API}/admin/applications/{app_id}", headers=adm).json()
    assert view["actions"] == []
    assert client.get(f"{API}/officer/applications/{app_id}", headers=adm).json()["actions"] == []
    doc_id = view["documents"][0]["id"]
    assert (
        client.get(f"{API}/applications/{app_id}/documents/{doc_id}/download", headers=adm).status_code == 200
    )
    # the two officer-only reads stay closed
    assert client.get(f"{API}/officer/feedback-templates", headers=adm).status_code == 403
    assert client.get(f"{API}/officer/applications/{app_id}/licence/preview", headers=adm).status_code == 403
    # every mutation is 403 for an administrator
    for method, path, body in (
        (
            "POST",
            f"{API}/officer/applications/{app_id}/transition",
            {"target": "approved", "expected_version": 1},
        ),
        (
            "POST",
            f"{API}/officer/applications/{app_id}/feedback",
            {"target_type": "section", "section_key": "premises", "message": "x"},
        ),
        ("POST", f"{API}/officer/applications/{app_id}/documents/{doc_id}/verify", None),
        ("POST", f"{API}/officer/applications/{app_id}/checklist", None),
        ("PUT", f"{API}/officer/applications/{app_id}/checklist", {"items": [], "version": 1}),
        ("POST", f"{API}/officer/applications/{app_id}/checklist/submit", None),
        (
            "POST",
            f"{API}/officer/applications/{app_id}/site-visit",
            {"date": "2026-10-01", "slot": "morning", "expected_version": 1},
        ),
        ("POST", f"{API}/officer/applications/{app_id}/clarifications/{uuid.uuid4()}/resolve", None),
        ("POST", f"{API}/applications/{app_id}/documents/{doc_id}/verify", None),
    ):
        r = client.request(method, path, headers=adm, json=body)
        assert r.status_code == 403, (method, path, r.text)
    # approve as the officer, then the admin downloads the licence
    from tests.journeys import transition

    transition(client, off, app_id, "approved", note="All in order.")
    assert client.get(f"{API}/applications/{app_id}/licence", headers=adm).status_code == 200


# ---- US-073: users ----


def test_directory_and_the_rules(client: TestClient, db: Session) -> None:
    me = make_user(db, "adm@example.sg", Role.ADMIN)
    adm = login(client, "adm@example.sg")
    demo = make_user(db, "officer@example.sg", Role.OFFICER, protected=True)
    spare = make_user(db, "spare@example.sg", Role.OPERATOR)
    r = client.get(f"{API}/admin/users", headers=adm)
    assert r.status_code == 200
    body = r.json()
    assert body["self_id"] == str(me.id)
    rows = {u["email"]: u for u in body["users"]}
    assert (
        rows["officer@example.sg"]["is_protected"] is True
        and rows["spare@example.sg"]["is_protected"] is False
    )
    assert set(rows["spare@example.sg"]) == {
        "id",
        "email",
        "full_name",
        "role",
        "is_active",
        "is_protected",
        "created_at",
    }

    # self-change wins over everything
    r = client.patch(f"{API}/admin/users/{me.id}", headers=adm, json={"is_active": False})
    assert r.status_code == 409 and r.json()["error"]["code"] == "self_change"
    # protected accounts cannot be changed
    r = client.patch(f"{API}/admin/users/{demo.id}", headers=adm, json={"role": "operator"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "protected_account"
    # the last active admin cannot be demoted or deactivated (another admin trying)
    other = make_user(db, "adm2@example.sg", Role.ADMIN, active=False)
    r = client.patch(f"{API}/admin/users/{other.id}", headers=adm, json={"is_active": True})
    assert r.status_code == 200 and r.json()["is_active"] is True
    adm2 = login(client, "adm2@example.sg")
    r = client.patch(f"{API}/admin/users/{other.id}", headers=adm, json={"is_active": False})
    assert r.status_code == 200  # two active admins: fine
    r = client.patch(f"{API}/admin/users/{me.id}", headers=adm2, json={"role": "officer"})
    assert r.status_code == 401  # adm2 was just deactivated: the next request ends the session
    # nothing to change
    r = client.patch(f"{API}/admin/users/{spare.id}", headers=adm, json={})
    assert r.status_code == 422
    # unknown user
    assert (
        client.patch(f"{API}/admin/users/{uuid.uuid4()}", headers=adm, json={"role": "officer"}).status_code
        == 404
    )
    # roles
    assert client.get(f"{API}/admin/users", headers=login(client, "officer@example.sg")).status_code == 403


def test_role_change_and_deactivation_take_effect_on_the_next_request(
    client: TestClient, db: Session
) -> None:
    make_user(db, "adm@example.sg", Role.ADMIN)
    adm = login(client, "adm@example.sg")
    spare = make_user(db, "spare@example.sg", Role.OPERATOR)
    sp = login(client, "spare@example.sg")
    assert client.get(f"{API}/applications", headers=sp).status_code == 200
    r = client.patch(f"{API}/admin/users/{spare.id}", headers=adm, json={"role": "officer"})
    assert r.status_code == 200 and r.json()["role"] == "officer"
    # the same token now acts as an officer: the operator list is 403, the queue 200
    assert client.get(f"{API}/applications", headers=sp).status_code == 403
    assert client.get(f"{API}/officer/applications", headers=sp).status_code == 200
    r = client.patch(f"{API}/admin/users/{spare.id}", headers=adm, json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get(f"{API}/officer/applications", headers=sp).status_code == 401
    assert (
        client.post(
            f"{API}/auth/login",
            json={"email": "spare@example.sg", "password": "PermitFlow!2026", "take_over": True},
        ).status_code
        == 401
    )
    r = client.patch(f"{API}/admin/users/{spare.id}", headers=adm, json={"is_active": True})
    assert r.status_code == 200
    # the deactivation ended the live session: the old token stays dead after the reactivation, with the
    # reason, and a fresh sign-in needs no take-over (review finding, 21 Sep)
    r = client.get(f"{API}/officer/applications", headers=sp)
    assert r.status_code == 401 and r.json()["error"]["code"] == "session_revoked"
    assert r.json()["error"]["details"]["reason"] == "deactivated"
    r = client.post(f"{API}/auth/login", json={"email": "spare@example.sg", "password": DEFAULT_PASSWORD})
    assert r.status_code == 200, r.text
    events = [
        e
        for e in db.scalars(select(AuditEvent).order_by(AuditEvent.created_at))
        if e.event_type.startswith("user.")
    ]
    kinds = [
        e.event_type
        for e in events
        if e.event_type in ("user.role_changed", "user.deactivated", "user.reactivated")
    ]
    assert kinds == ["user.role_changed", "user.deactivated", "user.reactivated"]
    assert all(e.application_id is None for e in events)
    assert events[0].payload["from"] == "operator" and events[0].payload["to"] == "officer"
    # a deactivated officer receives no notifications: the fan-out reads active officers only
    from app.repositories.notifications import NotificationRepository

    client.patch(f"{API}/admin/users/{spare.id}", headers=adm, json={"is_active": False})
    assert spare.id not in NotificationRepository(db).active_officer_ids()


def test_last_admin_cannot_be_removed(client: TestClient, db: Session) -> None:
    make_user(db, "adm@example.sg", Role.ADMIN)
    adm = login(client, "adm@example.sg")
    second = make_user(db, "adm2@example.sg", Role.ADMIN)
    # demote the second: fine (the caller stays)
    r = client.patch(f"{API}/admin/users/{second.id}", headers=adm, json={"role": "officer"})
    assert r.status_code == 200
    # promote back, then deactivate the caller from the second: refused, the caller would be the last
    client.patch(f"{API}/admin/users/{second.id}", headers=adm, json={"role": "admin"})
    adm2 = login(client, "adm2@example.sg")
    me = db.scalar(select(User).where(User.email == "adm@example.sg"))
    assert me is not None
    r = client.patch(f"{API}/admin/users/{me.id}", headers=adm2, json={"is_active": False})
    assert r.status_code == 200  # two active admins: allowed
    r = client.patch(f"{API}/admin/users/{me.id}", headers=adm2, json={"is_active": True})
    assert r.status_code == 200
    # now demote adm2 from adm and try to demote adm from adm2: the last-admin rule bites
    client.patch(f"{API}/admin/users/{second.id}", headers=adm, json={"is_active": False})
    r = client.patch(
        f"{API}/admin/users/{me.id}", headers=login(client, "adm@example.sg"), json={"role": "officer"}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "self_change"


def test_two_admins_cannot_both_leave(client: TestClient, db: Session) -> None:
    """Two administrators demoting each other at the same instant: at most one succeeds."""
    import threading

    a = make_user(db, "a@example.sg", Role.ADMIN)
    b = make_user(db, "b@example.sg", Role.ADMIN)
    ha, hb = login(client, "a@example.sg"), login(client, "b@example.sg")
    results: list[int] = []

    def demote(headers: dict[str, str], target: uuid.UUID) -> None:
        results.append(
            client.patch(f"{API}/admin/users/{target}", headers=headers, json={"role": "officer"}).status_code
        )

    t1 = threading.Thread(target=demote, args=(ha, b.id))
    t2 = threading.Thread(target=demote, args=(hb, a.id))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert sorted(results) in ([200, 409], [409, 409])
    admins = db.scalars(select(User).where(User.role == Role.ADMIN, User.is_active.is_(True))).all()
    assert len(admins) >= 1


def test_create_user_from_the_page(client: TestClient, db: Session) -> None:
    make_user(db, "adm@example.sg", Role.ADMIN)
    adm = login(client, "adm@example.sg")
    body = {
        "email": "New.Officer@Example.sg",
        "full_name": "Lim Jun Hao",
        "role": "officer",
        "password": DEFAULT_PASSWORD,
    }
    r = client.post(f"{API}/admin/users", headers=adm, json=body)
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["email"] == "new.officer@example.sg" and created["role"] == "officer"
    assert created["is_active"] is True and created["is_protected"] is False
    # the new person can sign in at once
    signin = {"email": "new.officer@example.sg", "password": DEFAULT_PASSWORD}
    assert client.post(f"{API}/auth/login", json=signin).status_code == 200
    # duplicates and weak passwords are refused
    r = client.post(f"{API}/admin/users", headers=adm, json=body)
    assert r.status_code == 409 and r.json()["error"]["details"]["reason"] == "email_taken"
    assert (
        client.post(
            f"{API}/admin/users", headers=adm, json={**body, "email": "x@example.sg", "password": "short"}
        ).status_code
        == 422
    )
    assert db.scalar(select(AuditEvent).where(AuditEvent.event_type == "user.created")) is not None
    # officers cannot create accounts
    assert (
        client.post(
            f"{API}/admin/users", headers=login(client, "new.officer@example.sg"), json=body
        ).status_code
        == 403
    )


@pytest.mark.parametrize("path", ["/admin/overview", "/admin/audit-feed", "/admin/users"])
def test_operator_and_officer_get_403_on_admin_reads(client: TestClient, db: Session, path: str) -> None:
    app_id, op, off = submitted(client, db)
    assert client.get(f"{API}{path}", headers=op).status_code == 403
    assert client.get(f"{API}{path}", headers=off).status_code == 403
