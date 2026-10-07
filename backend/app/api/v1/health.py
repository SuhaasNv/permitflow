import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.settings import get_settings
from app.core.version import APP_VERSION, BUILD_COMMIT
from app.infra.db import database_is_reachable

router = APIRouter()


# The probe result is held for a moment: the route is exempt from the limiter, so an unlimited caller
# must not turn every hit into a pooled connection and a query (review finding, 21 Sep).
PROBE_TTL_SECONDS = 2.0
_probe: tuple[float, bool] | None = None


def probe_database() -> bool:
    global _probe  # noqa: PLW0603 - one small cache for one route
    now = time.monotonic()
    if _probe is not None and now - _probe[0] < PROBE_TTL_SECONDS:
        return _probe[1]
    ok = database_is_reachable()
    _probe = (now, ok)
    return ok


@router.get("/health")
def health() -> JSONResponse:
    """Liveness + database readiness (REL-006), and which build answers: the version, the commit CI baked
    into the image and the environment, the same three the metrics and Telegram name (US-094; the What's
    new page heads with them). Never exposes provider configuration."""
    db_ok = probe_database()
    body: dict[str, object] = {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "version": APP_VERSION,
        "commit": BUILD_COMMIT,
        "environment": get_settings().app_env,
    }
    if not db_ok:
        # Same error body as every other failure (REL-001); the status fields stay for the deploy gate.
        body["error"] = {"code": "unavailable", "message": "The database is unreachable."}
    return JSONResponse(status_code=200 if db_ok else 503, content=body)
