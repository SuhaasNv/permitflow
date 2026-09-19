from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.infra.db import database_is_reachable

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    """Liveness + database readiness (REL-006). Never exposes provider configuration."""
    db_ok = database_is_reachable()
    body: dict[str, object] = {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unreachable",
    }
    if not db_ok:
        # Same error body as every other failure (REL-001); the status fields stay for the deploy gate.
        body["error"] = {"code": "unavailable", "message": "The database is unreachable."}
    return JSONResponse(status_code=200 if db_ok else 503, content=body)
