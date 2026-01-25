"""Session Manager - API Router Integration (v5.0).

통합 API 구조: 세션 API로 통일
"""

from fastapi import APIRouter

from app.api.v1.sessions import router as sessions_router

api_router = APIRouter()

# === 통합 API ===
api_router.include_router(sessions_router)  # /sessions - 세션 관리 (인증키로 호출자 구분)
