"""Session Manager - Main Application (v5.0, Sprint 5)."""

import logging
from contextlib import asynccontextmanager
from textwrap import dedent

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.sessions import router as sessions_router
from app.config import ALLOWED_ORIGINS, API_PREFIX, DEBUG
from app.core.exceptions import SessionManagerError

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - Redis 및 MariaDB 연결 초기화"""
    # Startup
    print("🚀 Session Manager starting...")

    # Redis 비동기 초기화
    from app.db.redis import init_redis

    await init_redis()

    # MariaDB 비동기 초기화 (선택적, MARIADB_HOST가 설정되어 있을 때만)
    from app.db.mariadb import init_mariadb

    init_mariadb()

    print("✅ Session Manager started")

    yield

    # Shutdown
    from app.db.redis import close_redis

    await close_redis()
    print("👋 Session Manager shutting down...")


app = FastAPI(
    title="Session Manager API",
    description=dedent(
        """
        ## Session Manager v5.0 (Sprint 5)

        ### 주요 기능

        **세션 관리**
        - 세션 생성/조회/상태 업데이트/종료/Ping
        - 세션 상태 관리: start / talk / end
        - JWT 토큰 기반 인증 (Access Token, Refresh Token)

        **멀티턴 컨텍스트**
        - `reference_information` 을 통한 대화 이력 관리
        - PATCH로 업데이트, GET으로 조회 시 자동 파싱
        - 주요 필드: conversation_history, current_intent, turn_count, task_queue_status 등

        **개인화 프로파일**
        - 실시간 프로파일: 실시간 프로파일 업데이트 API로 Redis 저장
          - cusnoN10이 있으면: 세션에 cusno 저장, Redis에 profile:realtime:{cusno} 저장, 배치 프로파일 조회 및 저장
          - cusnoN10이 없으면: 세션에 cusno 저장하지 않음, Redis에 profile:realtime:{global_session_key} 저장, 배치 프로파일 조회 안 함
        - 배치 프로파일: MariaDB에서 조회하여 Redis에 저장 (MariaDB 연결 정보가 있고 cusnoN10이 있을 때만)
        - 세션 조회 시 batch_profile과 realtime_profile을 분리하여 반환
        - 세션 조회 시 세션의 cusno 필드로 프로파일 조회 (cusno가 없으면 global_session_key로 실시간 프로파일만 조회)

        **SOL API 연동 로그**
        - 실시간 API 호출 결과를 `turn_id` 기반 메타데이터로 저장
        - 세션 전체 정보 조회 API로 세션 + 턴 목록 한 번에 확인 가능

        ### 주요 API 엔드포인트

        **Sessions API** (`/api/v1/sessions`)
        - `POST /sessions` - 세션 생성 (JWT 토큰 발급, userId 선택적)
        - `GET /sessions/{key}` - 세션 조회 (user_id 응답 제외)
        - `GET /sessions/ping` - 세션 생존 확인 (토큰 기반, TTL 연장 없음)
        - `GET /sessions/verify` - 토큰 검증 및 세션 정보 조회 (user_id 응답 제외)
        - `POST /sessions/refresh` - 토큰 갱신 (Refresh Token Rotation, 세션 TTL 연장)
        - `PATCH /sessions/{key}/state` - 세션 상태 업데이트
        - `DELETE /sessions/{key}` - 세션 종료 (내부 서비스용)
        - `DELETE /sessions` - 세션 종료 (토큰 기반)
        - `POST /sessions/{key}/api-results` - 실시간 API 연동 결과 저장
        - `POST /sessions/{key}/realtime-personal-context` - 실시간 프로파일 업데이트 (cusnoN10 선택적)
        - `GET /sessions/{key}/full` - 세션 전체 정보 조회 (세션 + 턴 목록)

        ### 저장소

        - **Redis**: 세션/턴 메타데이터 및 프로파일 저장
          - 세션: 기본 TTL 300초 (5분)
          - 턴(Turns): 세션과 동일한 TTL
          - 프로파일: 세션과 동일한 TTL (세션 만료 시 함께 삭제)
          - 키 구조: `session:{global_session_key}`, `profile:realtime:{cusno|global_session_key}`, `profile:batch:{cusno}`
        - **MariaDB** (선택적): 배치 프로파일 조회용 (IFC_CUS_DD_SMRY_TOT, IFC_CUS_MMBY_SMRY_TOT)
          - MariaDB 연결 정보가 없어도 서비스 정상 동작 (배치 프로파일만 None 반환)

        ### 환경

        - 로컬/Dev/운영: Redis 기반 (필수), MariaDB (선택적)
        - 환경변수 기반 설정, JWT 토큰 기반 인증
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


app.include_router(sessions_router, prefix=API_PREFIX)


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
