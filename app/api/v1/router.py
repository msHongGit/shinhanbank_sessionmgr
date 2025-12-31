"""
Session Manager - API Router Integration
"""
from fastapi import APIRouter

from app.api.v1.sessions import router as sessions_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.portal import router as portal_router

api_router = APIRouter()

api_router.include_router(sessions_router)
api_router.include_router(tasks_router)
api_router.include_router(profiles_router)
api_router.include_router(portal_router)
