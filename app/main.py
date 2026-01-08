"""Session Manager - Main Application (v4.0, Sprint 3).

세션 상태 / 컨텍스트 메타데이터 / 에이전트 세션 매핑 관리 API 진입점.
로컬에선 Mock/Redis, 운영에선 Redis + MariaDB 하이브리드 구성을 기준으로 한다.
"""

from contextlib import asynccontextmanager
from textwrap import dedent

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import ALLOWED_ORIGINS, API_PREFIX, APP_ENV, DEBUG
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
    description=dedent(
        """
        ## Session Manager v4.0 (Sprint 3)

        은행 AI Agent 시스템의 **세션 상태 / 컨텍스트 메타데이터 / 에이전트 세션 매핑**을 관리하는 서비스입니다.

        ### Session Manager가 관리하는 것
        - 세션 상태 정보 (Session State, SubAgent Status, Task Queue Status)
        - 에이전트 세션 매핑 (Global Session ↔ Agent Session Key)
        - 컨텍스트 메타데이터 (현재 Intent, Slot, Entity, Turn Count 등)
        - 대화 턴 메타데이터 (턴 번호, 역할, Agent 정보, 메타데이터) - **대화이력 제외**

        ### Session Manager가 관리하지 않는 것
        - 실제 대화 텍스트/콘텐츠
        - 대화 요약, Long-term 메모리

        ### 주요 API 그룹
        - `/api/v1/sessions` : 세션 생성 / 조회 / 상태 업데이트 / 종료 (AGW, MA, Client)
        - `/api/v1/contexts` : 컨텍스트 및 턴 메타데이터 관리 (MA, Portal)

        ### 저장소 구조 (Sprint 3 설계)
        - Redis : 세션/컨텍스트 캐시 (저지연 조회)
        - MariaDB : 세션, 에이전트 세션, 컨텍스트, 턴 메타데이터 영구 저장
        - Hybrid Repository : 읽기는 Redis 우선, 쓰기는 Redis + MariaDB 동기화

        ### 현재 실행 모드
        - 로컬 개발: Mock Repository / Redis 기반 In-Memory 모드
        - 운영: Redis + MariaDB 기반 하이브리드 모드 (설계 기준)
        """
    ),
    version="4.0.0",
    openapi_url=f"{API_PREFIX}/openapi.json",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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


@app.get("/", tags=["Health"])
def root_health_check():
    return {
        "status": "healthy",
        "service": "session-manager",
        "version": "4.0.0",
        "mode": "mock",  # Sprint 1
    }


app.include_router(api_router, prefix=API_PREFIX)


def custom_openapi():
    """커스텀 OpenAPI 스키마 - Swagger UI에서 servers 드롭다운 노출용."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Swagger UI에서 선택할 서버 목록 정의
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:5000",
            "description": "Local Dev (port 5000)",
        },
        {
            "url": "http://localhost:8000",
            "description": "Local Dev (port 8000)",
        },
        # 필요 시 ngrok / 테스트 서버 URL을 여기에 추가
        # {"url": "https://<your-ngrok>.ngrok-free.app", "description": "Ngrok tunnel"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# FastAPI에 커스텀 OpenAPI 적용
app.openapi = custom_openapi  # type: ignore[assignment]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=5000, reload=DEBUG)
