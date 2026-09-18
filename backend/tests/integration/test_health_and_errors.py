from fastapi.testclient import TestClient

from app.api.v1 import health as health_module


def test_health_ok(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Request-ID"]


def test_health_503_when_database_down(client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(health_module, "database_is_reachable", lambda: False)
    r = client.get("/api/v1/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "database": "unreachable"}


def test_unknown_route_uses_error_shape(client: TestClient) -> None:
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_method_not_allowed_uses_error_shape(client: TestClient) -> None:
    r = client.post("/api/v1/health")
    assert r.status_code == 405
    assert r.json()["error"]["code"] == "method_not_allowed"


def test_request_id_is_echoed(client: TestClient) -> None:
    r = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"


def test_unhandled_error_carries_cors_headers_and_request_id(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """US-044: a crash inside a route reaches the browser as the JSON envelope, with CORS headers."""
    from sqlalchemy.exc import TimeoutError as PoolTimeout

    from app.main import create_app

    app = create_app()

    @app.get("/api/v1/_boom")
    def boom() -> None:
        raise RuntimeError("boom")

    @app.get("/api/v1/_busy")
    def busy() -> None:
        raise PoolTimeout("QueuePool limit reached")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/v1/_boom", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 500
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
        body = r.json()["error"]
        assert body["code"] == "internal_error" and body["details"]["request_id"]
        assert r.headers["X-Request-ID"] == body["details"]["request_id"]

        r = c.get("/api/v1/_busy", headers={"Origin": "http://localhost:3000"})
        assert r.status_code == 503
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert r.json()["error"]["code"] == "unavailable"
