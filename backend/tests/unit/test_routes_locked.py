"""Every API route is locked (SEC-003, SEC-004): a role guard, or a signed-in user with ownership in the
query, or one of the few public routes named here. A new router that forgets its guard fails this test
before it reaches a reviewer (the admin, checklist, clarification and site-visit routers of v0.4.0 included).
"""

from fastapi.routing import APIRoute

from app.main import app

# Public by design: sign-in, the health probe, and the metrics scrape (a bearer token checked in the handler).
PUBLIC = {("POST", "/auth/login"), ("GET", "/health"), ("GET", "/metrics")}
# Any signed-in user; the data is scoped to the caller inside the query (notifications) or is not sensitive.
SIGNED_IN = {
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
    ("GET", "/form-schema"),
    ("GET", "/notifications"),
    ("POST", "/notifications/read-all"),
    ("POST", "/notifications/{notification_id}/read"),
}


def _routes() -> list[APIRoute]:
    def flatten(routes: list[object]) -> list[APIRoute]:
        out: list[APIRoute] = []
        for r in routes:
            if isinstance(r, APIRoute):
                out.append(r)
            elif type(r).__name__ == "_IncludedRouter":
                out.extend(flatten(r.original_router.routes))  # type: ignore[attr-defined]
        return out

    return flatten(list(app.routes))


def _guards(route: APIRoute) -> set[str]:
    names: set[str] = set()

    def walk(dep: object) -> None:
        for d in dep.dependencies:  # type: ignore[attr-defined]
            name = getattr(d.call, "__name__", "")
            if name == "_check" and d.call.__closure__:
                roles = d.call.__closure__[0].cell_contents
                name = "require_role(" + ",".join(sorted(x.value for x in roles)) + ")"
            names.add(name)
            walk(d)

    walk(route.dependant)
    return names


def test_every_route_is_locked() -> None:
    seen: set[tuple[str, str]] = set()
    for route in _routes():
        for method in route.methods:
            key = (method, route.path)
            seen.add(key)
            guards = _guards(route)
            if key in PUBLIC:
                assert "get_current_user" not in guards, f"{key} is public by design"
                continue
            if key in SIGNED_IN:
                assert "get_current_user" in guards, f"{key} must require a signed-in user"
                continue
            assert any(g.startswith("require_role(") for g in guards), f"{key} has no role guard"
    assert PUBLIC <= seen and SIGNED_IN <= seen, "the allowlists name routes that do not exist"


# The only writes an administrator may make: user management (US-073). Every case route stays read-only.
ADMIN_WRITES = {("POST", "/admin/users"), ("PATCH", "/admin/users/{user_id}")}


def test_admin_writes_are_user_management_only() -> None:
    """The read-only rule on cases (ADR-014): no route outside user management admits the admin to a write."""
    seen: set[tuple[str, str]] = set()
    for route in _routes():
        guards = _guards(route)
        if any("admin" in g for g in guards if g.startswith("require_role(")):
            for method in route.methods:
                if method != "GET":
                    seen.add((method, route.path))
                    assert (method, route.path) in ADMIN_WRITES, f"{route.path} lets an admin write"
    assert seen == ADMIN_WRITES
