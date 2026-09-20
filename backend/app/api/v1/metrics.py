"""`GET /metrics` for Prometheus (US-077). Off unless `METRICS_TOKEN` is configured; then a bearer token
is required, so the counts never sit on the public internet unauthenticated."""

import secrets

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.api.deps import DbSession
from app.core import metrics
from app.core.errors import NotFound, Unauthorized
from app.core.settings import get_settings
from app.services.metrics import refresh_gauges

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def scrape(request: Request, db: DbSession) -> Response:
    token = get_settings().metrics_token
    if not token:
        raise NotFound("Not found.")
    header = request.headers.get("authorization", "")
    scheme, _, presented = header.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(presented, token):
        raise Unauthorized("A metrics token is required.")
    refresh_gauges(db)
    body, content_type = metrics.render()
    return Response(content=body, media_type=content_type)
