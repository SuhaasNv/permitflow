"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import TimeoutError as PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.api.v1.router import api_router
from app.core.errors import AppError
from app.core.logging import configure_logging, request_logging_middleware
from app.core.rate_limit import RequestLimiter
from app.core.settings import get_settings

logger = logging.getLogger("permitflow")

# FastAPI's own HTTP errors, mapped to the standard error body (REL-001).
_HTTP_CODES = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.validate_for_startup()
    configure_logging()
    if settings.app_env != "test":
        from app.services.verification import mark_stale_runs_failed

        try:
            n = mark_stale_runs_failed()
            if n:
                logger.warning("stale_runs_marked_failed", extra={"extra_fields": {"count": n}})
        except Exception:  # noqa: BLE001 - startup must not depend on this housekeeping
            logger.exception("stale_run_cleanup_failed")
    yield


_INTERNAL_MESSAGE = "Something went wrong. Quote the request id when reporting it."


def _error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": {"request_id": request_id}}},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    # Interactive docs stay available outside production (THREAT_MODEL: no public schema in production).
    expose_docs = settings.app_env != "production"
    app = FastAPI(
        title="PermitFlow API",
        version="0.3.0",
        lifespan=lifespan,
        docs_url="/api/docs" if expose_docs else None,
        openapi_url="/api/openapi.json" if expose_docs else None,
    )

    # Added first, so it sits inside CORS: an unhandled error or an exhausted pool is answered with the
    # standard error body and the CORS headers, instead of a bare 500 the browser cannot read (US-044).
    @app.middleware("http")
    async def catch_unhandled(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except PoolTimeout:
            logger.warning("db_pool_exhausted", extra={"extra_fields": {"path": request.url.path}})
            return _error_response(request, 503, "unavailable", "The server is busy. Try again in a moment.")
        except Exception:
            request_id = getattr(request.state, "request_id", None)
            logger.exception("unhandled", extra={"extra_fields": {"request_id": request_id}})
            return _error_response(request, 500, "internal_error", _INTERNAL_MESSAGE)

    # Per-client request limits (US-058), inside CORS so a 429 carries the headers the browser needs.
    # Off in the test environment; tests that exercise it install their own limiter on app.state.
    app.state.limiter = RequestLimiter(
        per_minute=0 if settings.app_env == "test" else settings.rate_limit_per_minute,
        login_per_minute=0 if settings.app_env == "test" else settings.login_attempts_per_minute,
        trusted_proxies=settings.trusted_proxies,
    )

    @app.middleware("http")
    async def rate_limit(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        retry_after = app.state.limiter.check(request)
        if retry_after is not None:
            response = _error_response(
                request, 429, "rate_limited", "Too many requests. Try again in a moment."
            )
            response.headers["Retry-After"] = str(retry_after)
            return response
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        # US-058: the API serves JSON and files, never a page, so nothing may run or be embedded. The
        # interactive docs (non-production only) load Swagger from a CDN and are exempted.
        if not request.url.path.startswith("/api/docs") and not request.url.path.startswith("/api/openapi"):
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        return response

    app.middleware("http")(request_logging_middleware)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_body())

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        # A malformed id in the path (a mistyped or truncated link) is a missing resource to the user.
        if errors and all(e.get("loc", [None])[0] == "path" for e in errors):
            return _error_response(request, 404, "not_found", "Not found.")
        fields = [
            {"loc": [str(p) for p in e.get("loc", [])], "msg": e.get("msg", ""), "type": e.get("type", "")}
            for e in errors
        ]
        body = {
            "error": {
                "code": "validation_failed",
                "message": "Request validation failed",
                "details": {"fields": fields},
            }
        }
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message}},
            headers=dict(exc.headers or {}),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # Fallback for errors raised in the outer middlewares themselves; the usual path is catch_unhandled.
        request_id = getattr(request.state, "request_id", None)
        logger.exception("unhandled", extra={"extra_fields": {"request_id": request_id}})
        return _error_response(request, 500, "internal_error", _INTERNAL_MESSAGE)

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
