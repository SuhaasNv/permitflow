from fastapi import APIRouter

from app.api.v1 import (
    admin,
    applications,
    auth,
    checklist,
    form_schema,
    health,
    metrics,
    notifications,
    officer,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(form_schema.router, tags=["form"])
api_router.include_router(applications.router, tags=["applications"])
api_router.include_router(officer.router, tags=["officer"])
api_router.include_router(checklist.router, tags=["checklist"])
api_router.include_router(notifications.router, tags=["notifications"])
api_router.include_router(admin.router, tags=["admin"])
