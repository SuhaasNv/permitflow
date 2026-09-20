"""Prometheus metrics (US-077). Counters and histograms are process-local and free to update; the
`/metrics` route renders them. Names carry the `permitflow_` prefix so a shared Prometheus can tell them
apart. Labels stay low-cardinality on purpose: route templates, not paths; enum values, not ids."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "permitflow_http_requests_total",
    "HTTP requests by method, route template and status code.",
    ["method", "route", "status"],
)
HTTP_SECONDS = Histogram(
    "permitflow_http_request_seconds",
    "HTTP request latency by method and route template.",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
RATE_LIMITED = Counter(
    "permitflow_rate_limited_total", "Requests refused with 429 by the per-client limiter."
)
VERIFICATION_RUNS = Counter(
    "permitflow_verification_runs_total",
    "Finished verification runs by outcome and provider.",
    ["outcome", "provider"],
)
VERIFICATION_SECONDS = Histogram(
    "permitflow_verification_run_seconds",
    "Verification run latency (extraction, model, rules) by provider.",
    ["provider"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 60),
)
QUOTA_REFUSALS = Counter(
    "permitflow_quota_refusals_total", "Refusals by a database quota (US-058).", ["quota"]
)
TRANSITIONS = Counter(
    "permitflow_transitions_total",
    "Committed status transitions by target status and actor.",
    ["target", "actor"],
)
OPENAI_TOKENS = Counter(
    "permitflow_openai_tokens_total",
    "Tokens billed by OpenAI for document checks, by model and kind (prompt, cached, completion).",
    ["model", "kind"],
)
APPLICATIONS = Gauge(
    "permitflow_applications", "Applications by status, refreshed on every scrape.", ["status"]
)
SESSIONS_ACTIVE = Gauge(
    "permitflow_sessions_active", "Accounts signed in right now (US-093), refreshed on every scrape."
)
# Use case 3 on the dashboard (US-089): the checklist and the rounds moving, and the volume filling.
CHECKLISTS_SUBMITTED = Counter(
    "permitflow_checklists_submitted_total", "Site visit checklists submitted (US-063)."
)
CLARIFICATION_ROUNDS = Counter(
    "permitflow_clarification_rounds_total",
    "Clarification rounds by event: released to the operator, answered by the operator.",
    ["event"],
)
ATTACHMENT_BYTES = Counter(
    "permitflow_attachment_bytes_total", "Bytes stored as clarification evidence (US-065)."
)
STORAGE_BYTES = Gauge(
    "permitflow_storage_bytes",
    "Bytes on the upload volume by kind (documents, attachments, volume_used, volume_total), per scrape.",
    ["kind"],
)


def route_template(request: Request) -> str:
    """The matched route's template (`/api/v1/applications/{application_id}`), never the raw path, so the
    label set stays as small as the API. The scope's route carries the path relative to the included
    router; the prefix is recovered by rendering the template with the path params and matching the
    raw path's tail."""
    route = request.scope.get("route")
    template = getattr(route, "path_format", None)
    if not template:
        return "unmatched"
    path = request.url.path
    try:
        concrete = str(template).format(**request.scope.get("path_params", {}))
    except (KeyError, IndexError):
        return str(template)
    if path.endswith(concrete):
        return path[: len(path) - len(concrete)] + str(template)
    return str(template)


async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = time.perf_counter()
    response = await call_next(request)
    route = route_template(request)
    if route.endswith("/metrics"):
        return response  # the scraper does not count itself
    HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    HTTP_SECONDS.labels(request.method, route).observe(time.perf_counter() - started)
    return response


def render() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
