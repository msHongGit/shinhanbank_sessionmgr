"""
tests/integration/conftest.py

Pod 환경(개발 서버) 기반 통합 테스트 공통 설정.

필수 환경변수 (K8s ConfigMap/Secret 또는 .env):
    REDIS_SENTINEL_NODES  = '[["172.x.x.x",5001],["172.x.x.x",5002]]'
    REDIS_SENTINEL_MASTER_NAME = "mymaster"
    REDIS_USERNAME        = (비어 있으면 생략 가능)
    REDIS_PASSWORD        = "..."
    REDIS_DB              = "6"
    JWT_SECRET_KEY        = "..."
    MINIO_ENDPOINT        = "http://172.x.x.x:9000"   ← Profile 테스트 시 필요
    MINIO_ACCESS_KEY      = "..."
    MINIO_SECRET_KEY      = "..."
    MINIO_BUCKET          = "shinhanobj"

실행:
    # Pod 내부 또는 k8s port-forward 후
    pytest tests/integration/ -v

    # 특정 마커만
    pytest tests/integration/ -v -m session
    pytest tests/integration/ -v -m auth
    pytest tests/integration/ -v -m profile
"""

import os
import uuid

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# 사전 조건 확인: Redis 설정이 없으면 전체 모듈 스킵
# ---------------------------------------------------------------------------
_REDIS_URL = os.getenv("REDIS_URL")
_SENTINEL_NODES = os.getenv("REDIS_SENTINEL_NODES")

if not _REDIS_URL and not _SENTINEL_NODES:
    pytest.skip(
        "통합 테스트를 위한 Redis 설정이 없습니다. "
        "REDIS_URL 또는 REDIS_SENTINEL_NODES 환경변수를 설정하세요.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Redis 초기화 / 종료
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _init_redis_connection():
    """세션 전체에서 Redis 연결을 한 번 초기화하고 종료 시 닫는다."""
    from app.db.redis import close_redis, init_redis

    await init_redis()
    yield
    await close_redis()


# ---------------------------------------------------------------------------
# 테스트별 Redis 클라이언트
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def redis_client():
    """테스트에서 직접 Redis 명령을 실행할 수 있는 클라이언트."""
    from app.db.redis import get_redis_client

    return get_redis_client()


# ---------------------------------------------------------------------------
# 실제 Repository / Service 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def session_repo():
    """실제 RedisSessionRepository (개발 Redis 연결)."""
    from app.repositories.redis_session_repository import RedisSessionRepository

    return RedisSessionRepository()


@pytest.fixture
def auth_service(session_repo):
    """실제 AuthService (실제 JWT 서명 + 실제 Redis jti 매핑)."""
    from app.services.auth_service import AuthService

    return AuthService(session_repo=session_repo)


@pytest.fixture
def profile_repo():
    """MinIO BatchProfile Repository. 설정 없으면 None."""
    try:
        from app.repositories.minio_batch_profile_repository import MinioBatchProfileRepository

        repo = MinioBatchProfileRepository()
        return repo
    except Exception:
        return None


@pytest.fixture
def session_service(session_repo, auth_service, profile_repo):
    """실제 SessionService (모든 의존성 실제 연결)."""
    from app.services.profile_service import ProfileService
    from app.services.session_service import SessionService

    ps = ProfileService(session_repo=session_repo, profile_repo=profile_repo)
    return SessionService(
        session_repo=session_repo,
        auth_service=auth_service,
        profile_service=ps,
        profile_repo=profile_repo,
    )


@pytest.fixture
def profile_service(session_repo, profile_repo):
    """실제 ProfileService."""
    from app.services.profile_service import ProfileService

    return ProfileService(session_repo=session_repo, profile_repo=profile_repo)


# ---------------------------------------------------------------------------
# 테스트 키 네임스페이스: 테스트 전용 접두사로 격리
# ---------------------------------------------------------------------------

TEST_KEY_PREFIX = "inttest"


@pytest.fixture
def test_session_key():
    """테스트마다 고유한 세션 키 생성 (inttest_ 접두사로 실서비스 키와 격리)."""
    return f"{TEST_KEY_PREFIX}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# 자동 정리: 테스트에서 생성한 Redis 키를 테스트 후 삭제
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_test_keys(redis_client):
    """테스트 종료 후 inttest_* 패턴의 Redis 키를 모두 삭제한다."""
    yield
    keys = await redis_client.keys(f"{TEST_KEY_PREFIX}_*")
    if keys:
        await redis_client.delete(*keys)

    # jti 매핑도 정리 (set_jti_mapping은 "jti:{uuid}" 형태)
    jti_keys = await redis_client.keys("jti:*")
    # 테스트용 jti만 삭제 (실서비스 jti와 구분 불가이므로 주의: 개발 전용 DB 사용 권장)
    if jti_keys:
        await redis_client.delete(*jti_keys)
