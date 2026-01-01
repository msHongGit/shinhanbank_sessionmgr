"""
Session Manager - API Dependencies (v3.0)
호출자별 API Key 분리
"""

from fastapi import Header, HTTPException

from app.config import settings
from app.services.context_service import ContextService
from app.services.profile_service import ProfileService
from app.services.session_service import SessionService

# ============ API Key 검증 (호출자별) ============


def verify_agw_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """AGW API Key 검증"""
    if not x_api_key or x_api_key != settings.AGW_API_KEY:
        raise HTTPException(status_code=401, detail={"code": "AUTH001", "message": "Invalid AGW API key"})
    return x_api_key


def verify_ma_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """MA API Key 검증"""
    if not x_api_key or x_api_key != settings.MA_API_KEY:
        raise HTTPException(status_code=401, detail={"code": "AUTH002", "message": "Invalid MA API key"})
    return x_api_key


def verify_portal_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """Portal API Key 검증"""
    if not x_api_key or x_api_key != settings.PORTAL_API_KEY:
        raise HTTPException(status_code=401, detail={"code": "AUTH003", "message": "Invalid Portal API key"})
    return x_api_key


def verify_vdb_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """VDB API Key 검증"""
    if not x_api_key or x_api_key != settings.VDB_API_KEY:
        raise HTTPException(status_code=401, detail={"code": "AUTH004", "message": "Invalid VDB API key"})
    return x_api_key


# ============ Service 의존성 ============


def get_session_service() -> SessionService:
    """SessionService 의존성"""
    return SessionService()


def get_context_service() -> ContextService:
    """ContextService 의존성"""
    return ContextService()


def get_profile_service() -> ProfileService:
    """ProfileService 의존성"""
    return ProfileService()
