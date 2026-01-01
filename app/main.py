"""
Session Manager - Main Application (v4.0)
호출자별 API 분리: AGW, MA, Portal, Batch(VDB)
Sprint 1: Mock Repository 사용 (DB/Redis 연결 옵션)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import SessionManagerError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - DB/Redis 연결 (Sprint 1: Optional)"""
    # Startup
    print("🚀 Session Manager starting...")

    # Sprint 1: Mock Repository 사용, DB/Redis 연결 Skip
    # Sprint 2+: 아래 주석 해제
    # try:
    #     from app.db.redis import init_redis
    #     from app.db.postgres import init_db
    #     init_redis()
    #     init_db()
    # except Exception as e:
    #     print(f"⚠️ DB/Redis 연결 실패 (Mock 사용): {e}")

    print("✅ Session Manager started (Mock Repository Mode)")

    yield

    # Shutdown
    print("👋 Session Manager shutting down...")


app = FastAPI(
    title="Session Manager API",
    description="""
    ## Session Manager v4.0
    
    은행 AI Agent 시스템의 세션 관리 API
    
    ### 호출자별 API
    
    | 호출자 | Prefix | 기능 |
    |--------|--------|------|
    | **Agent GW** | `/agw` | 초기 세션 생성 |
    | **MA** | `/ma` | 세션 조회/업데이트, Local 매핑, 대화 이력, 프로파일 |
    | **Portal** | `/portal` | 세션 목록 조회(읽기전용), Context 삭제 |
    | **VDB** | `/batch` | 프로파일 배치 업로드 |
    
    ### 세션 구조
    - **Global Session**: Client가 발급, AGW가 SM에 전달
    - **Local Session**: 업무 Agent가 발급, MA가 매핑 등록
    
    ### 연동 방식
    - 모든 연동은 **Sync(동기)** 방식
    
    ### Sprint 1
    - Mock Repository 사용 (In-Memory)
    - DB/Redis 연결 없음
    """,
    version="4.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SessionManagerError)
def session_manager_exception_handler(request, exc: SessionManagerError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            }
        },
    )


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "session-manager",
        "version": "4.0.0",
        "mode": "mock",  # Sprint 1
    }


@app.get("/ready", tags=["Health"])
def readiness_check():
    return {"status": "ready"}


app.include_router(api_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
