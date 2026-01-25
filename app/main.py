"""Session Manager - Main Application (v5.0, Sprint 5).

세션 상태 / 컨텍스트 메타데이터 / 에이전트 세션 매핑 관리 API 진입점.
Sprint 5 구현: Redis 기반 세션/컨텍스트 관리 (Redis만 사용)
"""

from contextlib import asynccontextmanager
from textwrap import dedent

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import ALLOWED_ORIGINS, API_PREFIX, DEBUG
from app.core.exceptions import SessionManagerError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - Redis 연결"""
    # Startup
    print("🚀 Session Manager starting...")

    # Sprint 5: Redis만 사용
    # Redis 연결은 각 Repository에서 필요 시 초기화됨
    print("✅ Session Manager started (Redis only)")

    yield

    # Shutdown
    print("👋 Session Manager shutting down...")


app = FastAPI(
    title="Session Manager API",
    description=dedent(
        """
        ## Session Manager v5.0 (Sprint 5)

        은행 AI Agent 시스템의 세션/컨텍스트 관리 서비스

        ### 주요 기능

        **세션 관리**
        - 세션 생성/조회/상태 업데이트/종료/Ping (TTL 연장)
        - 세션 상태 관리: start / talk / end
        - SubAgent 상태 관리: undefined / continue / end
        - Global 세션 ↔ 업무 Agent 세션 키 매핑

        **멀티턴 컨텍스트**
        - `reference_information` 을 통한 대화 이력 관리
        - PATCH로 업데이트, GET으로 조회 시 자동 파싱
        - 주요 필드: conversation_history, current_intent, turn_count, task_queue_status 등

        **개인화 프로파일**
        - 세션 생성 시 user_id 기반 자동 조회 및 스냅샷 저장
        - 세션 조회 시 customer_profile 필드로 반환

        **SOL API 연동 로그**
        - 실시간 API 호출 결과를 `turn_id` 기반 메타데이터로 저장
        - 세션 전체 정보 조회 API로 세션 + 턴 목록 한 번에 확인 가능

        ### 주요 API 엔드포인트

        **Sessions API** (`/api/v1/sessions`)
        - `POST /sessions` - 세션 생성
        - `GET /sessions/{key}` - 세션 조회
        - `GET /sessions/{key}/ping` - 세션 생존 확인 및 TTL 연장
        - `PATCH /sessions/{key}/state` - 세션 상태 업데이트
        - `DELETE /sessions/{key}` - 세션 종료
        - `POST /sessions/{key}/api-results` - 실시간 API 연동 결과 저장
        - `GET /sessions/{key}/full` - 세션 전체 정보 조회 (세션 + 턴 목록)

        ### 저장소

        - **Redis**: 세션/턴 메타데이터 저장 (기본 TTL 300초)

        ### 환경

        - 로컬/Dev/운영: Redis 기반 (환경변수 기반 설정, API Key 인증 활성화 가능)
        """
    ),
    version="5.0.0",
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
    """루트 헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "session-manager",
        "version": "5.0.0",
        "storage": "redis",
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
