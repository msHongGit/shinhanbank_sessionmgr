"""
Session Manager - API Router Integration (v3.0)
호출자별 API 분리
"""
from fastapi import APIRouter

# AGW
from app.api.v1.agw.sessions import router as agw_sessions_router

# Batch (VDB)
from app.api.v1.batch.profiles import router as batch_profiles_router
from app.api.v1.ma.context import router as ma_context_router
from app.api.v1.ma.profiles import router as ma_profiles_router

# MA
from app.api.v1.ma.sessions import router as ma_sessions_router

# Portal
from app.api.v1.portal.admin import router as portal_admin_router

api_router = APIRouter()

# AGW API - 초기 세션 생성
api_router.include_router(agw_sessions_router)

# MA API - 세션 관리, 대화 이력, 프로파일
api_router.include_router(ma_sessions_router)
api_router.include_router(ma_context_router)
api_router.include_router(ma_profiles_router)

# Portal API - 세션 조회(읽기전용), Context 삭제
api_router.include_router(portal_admin_router)

# Batch API - VDB 프로파일 업로드
api_router.include_router(batch_profiles_router)
