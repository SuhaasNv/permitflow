from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.infra.db import database_is_reachable

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    """Liveness + database readiness (REL-006). Never exposes provider configuration."""
    db_ok = database_is_reachable()
    body = {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unreachable"}
    return JSONResponse(status_code=200 if db_ok else 503, content=body)
