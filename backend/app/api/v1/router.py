from fastapi import APIRouter

from app.api.v1 import applications, auth, form_schema, health, notifications, officer

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(form_schema.router, tags=["form"])
api_router.include_router(applications.router, tags=["applications"])
api_router.include_router(officer.router, tags=["officer"])
api_router.include_router(notifications.router, tags=["notifications"])
