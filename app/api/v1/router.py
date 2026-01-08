"""Session Manager - API Router Integration (v5.0).

통합 API 구조: 기능별 분리 + 인증으로 호출자 구분
"""

from fastapi import APIRouter

from app.api.v1.contexts import router as contexts_router
from app.api.v1.sessions import router as sessions_router

api_router = APIRouter()

# === 통합 API ===
api_router.include_router(sessions_router)  # /sessions - 세션 관리 (인증키로 호출자 구분)
api_router.include_router(contexts_router)  # /contexts - Context & Turn 메타데이터 (Sprint 3)
