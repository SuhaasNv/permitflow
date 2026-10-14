"""Abuse case 1 (US-105; THREAT_MODEL T1, T2, T3, T15, T19; SEC-003, SEC-004): every route, called as
anonymous, as operator A (the owner), as operator B (another tenant, using A's ids), as an officer and
as an administrator.

The routes are read from the app, so a new route is covered the moment it exists; it fails
`test_every_route_has_a_row` until `access_table.ACCESS` says who may call it. What each principal must get:

- anonymous: 401 on every route that is not public;
- a role the route does not list: 403;
- operator B on a route that names A's resource: 403 or 404, never 2xx, and nothing in the database moves;
- a role the route lists: not refused. Only safe methods are executed for these (an unsafe call would change
  the shared world); the owner must reach the resource (200), so a 404 cannot hide a missing id.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.abuse.access_table import ACCESS, OWNER_NOT_200, QUERY, Row
from tests.abuse.conftest import World, fingerprint
from tests.journeys import PDF, VALID_BUSINESS, next_working_day
from tests.unit.test_routes_locked import _routes

API = "/api/v1"
Key = tuple[str, str]


def _live_keys() -> set[Key]:
    return {(m, r.path) for r in _routes() for m in r.methods}


def test_every_route_has_a_row() -> None:
    live = _live_keys()
    missing = sorted(live - ACCESS.keys())
    stale = sorted(ACCESS.keys() - live)
    assert not missing, (
        "New route without a row in tests/abuse/access_table.py::ACCESS. Add (method, path) with the roles "
        f"allowed to call it and the scope of its data: {missing}"
    )
    assert not stale, f"Rows in tests/abuse/access_table.py::ACCESS for routes that no longer exist: {stale}"


def test_the_table_agrees_with_the_documented_role_split() -> None:
    """The table is written by hand; these are the invariants the project states in prose (ADR-014): the
    administrator never writes to a case, and an operator-only route is never open to the officer."""
    admin_writes = {k for k, (roles, _) in ACCESS.items() if "admin" in roles and k[0] != "GET"}
    assert admin_writes == {
        ("POST", "/notifications/read-all"),
        ("POST", "/notifications/{notification_id}/read"),
        ("POST", "/auth/logout"),
        ("POST", "/admin/users"),
        ("PATCH", "/admin/users/{user_id}"),
        ("PUT", "/admin/settings/{key}"),
        ("POST", "/admin/settings/history/{event_id}/revert"),
    }


def _fill(world: World, path: str) -> str:
    # `{key}` is a section on an application and a setting under /admin/settings.
    values = {**world.ids, "key": "max_drafts_per_user" if path.startswith("/admin/settings") else "business"}
    out = path
    for name in set(part[1:-1] for part in path.split("/") if part.startswith("{")):
        assert name in values, f"{path} has a placeholder {{{name}}} the world does not provide: add it"
        out = out.replace("{" + name + "}", values[name])
    return API + out


def _kwargs(method: str, path: str) -> dict[str, Any]:
    """A well-formed request, so a refusal can only come from the access rules and not from validation."""
    if method == "GET":
        return {"params": QUERY.get((method, path), {})}
    if path.endswith("/documents"):
        return {"data": {"document_type": "floor_plan"}, "files": {"file": ("a.pdf", PDF, "application/pdf")}}
    if path.endswith("/attachments"):
        return {"files": {"file": ("a.pdf", PDF, "application/pdf")}}
    if path.endswith("/sections/{key}"):
        return {"json": VALID_BUSINESS}
    if path.endswith(("/site-visit/counter", "/site-visit/reschedule")):
        return {"json": {"date": next_working_day(), "slot": "morning", "reason": "Need another day"}}
    if path.endswith("/responses"):
        return {"json": {"message": "Done."}}
    if path.endswith("/admin/users"):
        return {
            "json": {"email": "x@example.sg", "full_name": "X", "role": "officer", "password": "Aa1!aaaaaaaa"}
        }
    return {"json": {}}


def _principals(world: World) -> list[tuple[str, str | None, dict[str, str]]]:
    return [
        ("anonymous", None, world.anon),
        ("operator A", "operator", world.a),
        ("operator B", "operator", world.b),
        ("officer", "officer", world.officer),
        ("admin", "admin", world.admin),
    ]


def _verdict(principal: str, role: str | None, key: Key, row: Row) -> set[int] | str | None:
    """The statuses the principal may get; 'allowed' for a listed role (not asserted for unsafe methods);
    None when the route is public."""
    roles, scope = row
    if scope == "public":
        return None
    if role is None:
        return {401}
    if role not in roles:
        return {403}
    if scope == "own" and principal == "operator B":
        return {403, 404}
    if scope == "owner_user" and principal != "operator A":
        return {404}
    return "allowed"


def test_every_route_as_every_role_and_as_another_tenant(
    client: TestClient, db: Session, world: World
) -> None:
    failures: list[str] = []
    allowed_calls: list[tuple[str, Key, str]] = []
    before = fingerprint(db)

    for key, row in ACCESS.items():
        method, path = key
        for principal, role, headers in _principals(world):
            want = _verdict(principal, role, key, row)
            if want == "allowed":
                if method == "GET":
                    allowed_calls.append((principal, key, role or ""))
                continue
            r = client.request(method, _fill(world, path), headers=headers, **_kwargs(method, path))
            if want is None:  # public: whoever asks, never a server error and never a refusal by role
                ok = r.status_code < 500 and r.status_code not in (401, 403)
                want = {"not 401/403/5xx"}
            else:
                ok = r.status_code in want
            if not ok:
                failures.append(f"{principal:10} {method:6} {path}: got {r.status_code}, want {sorted(want)}")
                continue
            # A refusal says nothing about the case it refused.
            if r.status_code >= 400 and "Kopi" in r.text:
                failures.append(f"{principal:10} {method:6} {path}: the refusal leaks case data")

    changed = [t for t, rows in fingerprint(db).items() if rows != before[t]]
    assert not failures, "access rules broken:\n" + "\n".join(failures)
    assert not changed, f"a refused request changed the database: {changed}"

    # Routes the role may call: executed when safe; the owner must really reach the resource.
    for principal, key, _ in allowed_calls:
        method, path = key
        headers = dict((p, h) for p, _, h in _principals(world))[principal]
        r = client.request(method, _fill(world, path), headers=headers, **_kwargs(method, path))
        if r.status_code >= 500 or r.status_code in (401, 403):
            failures.append(f"{principal:10} {method:6} {path}: refused or failed with {r.status_code}")
        scope = ACCESS[key][1]
        if principal == "operator A" and scope == "own":
            expected = OWNER_NOT_200.get(key, (200, ""))[0]
            if r.status_code != expected:
                failures.append(
                    f"{principal:10} {method:6} {path}: the owner got {r.status_code}, want {expected} "
                    "(the matrix is not reaching A's resource)"
                )
    assert not failures, "access rules broken:\n" + "\n".join(failures)


def test_self_scoped_lists_never_hold_another_tenants_rows(client: TestClient, world: World) -> None:
    mine = {a["id"] for a in client.get(f"{API}/applications", headers=world.a).json()}
    theirs = client.get(f"{API}/applications", headers=world.b).json()
    assert world.app_id in mine and theirs == []

    a_notes = {n["id"] for n in client.get(f"{API}/notifications", headers=world.a).json()["items"]}
    b_notes = client.get(f"{API}/notifications", headers=world.b).json()["items"]
    assert a_notes and not ({n["id"] for n in b_notes} & a_notes)
    assert client.get(f"{API}/auth/me", headers=world.b).json()["email"] == "op-b@example.sg"


@pytest.mark.parametrize("who", ["officer", "admin", "b"])
def test_nobody_but_the_owner_can_mark_a_notification_read(
    client: TestClient, world: World, who: str
) -> None:
    nid = world.ids["notification_id"]
    r = client.post(f"{API}/notifications/{nid}/read", headers=getattr(world, who))
    assert r.status_code == 404
    unread = client.get(f"{API}/notifications", headers=world.a).json()["items"]
    assert next(n for n in unread if n["id"] == nid)["read_at"] is None
    assert client.post(f"{API}/notifications/{uuid.uuid4()}/read", headers=world.a).status_code == 404
