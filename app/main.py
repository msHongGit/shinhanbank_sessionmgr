"""Session Manager - Main Application (v4.0, Sprint 3).

세션 상태 / 컨텍스트 메타데이터 / 에이전트 세션 매핑 관리 API 진입점.
현재 Sprint 3 구현은 Redis 기반 세션/컨텍스트 캐시 + Mock Profile Repository만 사용하며,
MariaDB(Context DB) 연동은 향후 스프린트에서 추가된다.
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

                - 세션 상태 (start / talk / end), SubAgent 상태, Task Queue 상태 관리
                                - Global 세션 ↔ 업무 Agent 세션 키 매핑 관리
                                - 멀티턴 컨텍스트(reference_information)를 세션 조회 응답에서 옵션 A 구조로 노출
                                    (active_task, conversation_history, current_intent 등)
                - SOL 실시간 API 연동 결과 메타데이터 저장 (Context/Turn 메타데이터, 대화 텍스트는 저장하지 않음)
                - 외부 Profile Repository에서 조회한 고객 개인화 프로파일 스냅샷 캐시

                - 주요 API:
                    - `/api/v1/sessions` : 세션 생성 / 조회 / 상태 업데이트 / 종료
                    - `/api/v1/contexts` : SOL 실시간 API 결과 저장 (turn-results 전용)

                - 저장소:
                    - Redis : 세션/컨텍스트/턴 메타데이터 캐시 및 저장 (기본 TTL 600초)
                    - MariaDB(Context DB) : 향후 영구 저장용으로 연동 예정 (현재 미사용)

                - 실행 모드:
                    - 로컬/Dev: Redis + Mock Profile Repository (API Key 인증 비활성화)
                    - 운영: Redis + MariaDB 하이브리드 모드 목표 (아직 미구현)
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


@app.get("/health", tags=["Health"])
def health_check():
    """외부 헬스체크용 /health 엔드포인트 (루트와 동일 응답)."""
    return root_health_check()


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
