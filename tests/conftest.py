"""
Session Manager - Test Configuration and Fixtures (v5.0)
Sprint 5: Redis + MariaDB Integration Tests
"""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

# 모든 환경에서 REDIS_URL 필수
# - 로컬: .env 파일에 Azure Redis 설정
# - CI: GitHub Actions workflow에서 설정
# v5.0: 테스트에서는 실제 Redis와 실제 MariaDB를 사용
from app.main import app
from app.schemas import ConversationTurn, CustomerProfile, ProfileAttribute
from app.services.session_service import SessionService


@pytest.fixture(autouse=True)
def _reset_redis_client():
    """각 테스트마다 Redis 클라이언트 초기화 (이벤트 루프 충돌 방지)

    TestClient가 각 테스트마다 새로운 이벤트 루프를 생성하고 닫기 때문에,
    전역 Redis 클라이언트를 재사용하면 "Event loop is closed" 에러가 발생합니다.
    따라서 테스트 환경에서는 매번 새로 생성하되, Redis 연결 풀은 내부적으로 재사용됩니다.
    """
    import app.db.redis as redis_module

    # Redis 클라이언트를 None으로 초기화 (매 테스트마다 새로 생성되도록)
    redis_module._redis_client = None

    yield

    # Cleanup은 생략 (테스트 환경에서는 Redis 클라이언트를 명시적으로 닫지 않음)
    # TestClient가 사용하는 이벤트 루프와 충돌을 피하기 위함


@pytest.fixture
def client():
    """FastAPI TestClient using real Redis and real MariaDB."""
    from app.api.v1.sessions import get_session_service

    # 실제 MariaDB Batch Profile Repository 사용 (설정되어 있으면)
    profile_repo = None
    try:
        from app.repositories.mariadb_batch_profile_repository import MariaDBBatchProfileRepository

        profile_repo = MariaDBBatchProfileRepository()
    except Exception as e:
        # MariaDB 연결 정보가 없으면 None으로 두고 테스트 진행
        # (일부 테스트는 MariaDB 없이도 실행 가능)
        import logging

        logging.getLogger(__name__).debug(f"MariaDB connection not available: {e}")
        profile_repo = None

    # SessionService는 실제 Redis와 실제 MariaDB를 사용
    def override_session_service():
        return SessionService(profile_repo=profile_repo)

    app.dependency_overrides[get_session_service] = override_session_service

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


# ============ Test Headers (JWT 기반 인증으로 전환, API Key 제거) ============


@pytest.fixture
def agw_headers():
    """AGW API headers (API Key 제거됨, Content-Type만 유지)"""
    return {"Content-Type": "application/json"}


@pytest.fixture
def ma_headers():
    """MA API headers (API Key 제거됨, Content-Type만 유지)"""
    return {"Content-Type": "application/json"}


@pytest.fixture
def portal_headers():
    """Portal API headers (API Key 제거됨, Content-Type만 유지)"""
    return {"Content-Type": "application/json"}


@pytest.fixture
def vdb_headers():
    """VDB API headers (API Key 제거됨, Content-Type만 유지)"""
    return {"Content-Type": "application/json"}


@pytest.fixture
def jwt_headers(access_token):
    """JWT 토큰 기반 헤더"""
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


@pytest.fixture
def access_token(client, agw_headers):
    """Access Token 생성 (세션 생성 후 토큰 추출)"""
    request_data = {
        "userId": "0616001905",
    }
    response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)
    assert response.status_code == 201
    data = response.json()
    return data["access_token"]


@pytest.fixture
def refresh_token(client, agw_headers):
    """Refresh Token 생성 (세션 생성 후 토큰 추출)"""
    request_data = {
        "userId": "0616001905",
    }
    response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)
    assert response.status_code == 201
    data = response.json()
    return data["refresh_token"]


@pytest.fixture
def session_with_tokens(client, agw_headers):
    """세션 생성 및 토큰 정보 반환"""
    request_data = {
        "userId": "0616001905",
    }
    response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)
    assert response.status_code == 201
    data = response.json()
    return {
        "global_session_key": data["global_session_key"],
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "jti": data["jti"],
    }


# ============ Sample Data ============


@pytest.fixture
def sample_global_session_key():
    """샘플 Global 세션 키 (Client가 발급)"""
    return "gsess_20250316_user_001"


@pytest.fixture
def sample_agent_session_key():
    """샘플 Agent 세션 키 (업무 Agent가 발급)"""
    return "lsess_transfer_001"


@pytest.fixture
def sample_customer_profile():
    """샘플 고객 프로파일"""
    return CustomerProfile(
        cusnoN10="0616001905",
        attributes=[ProfileAttribute(key="segment", value="VIP", source_system="crm")],
        segment="VIP",
        preferences={"language": "ko"},
    )


@pytest.fixture
def sample_conversation_turn():
    """샘플 대화 턴"""
    return ConversationTurn(turn_id="turn_001", role="user", content="계좌 이체를 하고 싶어요", timestamp=datetime.now(UTC))


# ============ AGW Request ============


@pytest.fixture
def sample_agw_session_create_request(sample_global_session_key):
    """AGW 세션 생성 요청"""
    return {"global_session_key": sample_global_session_key, "user_id": "0616001905", "channel": "mobile", "request_id": "req_001"}


# ============ MA Requests ============


@pytest.fixture
def sample_ma_local_register_request(sample_global_session_key, sample_agent_session_key):
    """MA Local 세션 등록 요청"""
    return {
        "global_session_key": sample_global_session_key,
        "agent_session_key": sample_agent_session_key,
        "agent_id": "agent-transfer",
        "agent_type": "task",
    }


@pytest.fixture
def sample_ma_session_patch_request(sample_global_session_key):
    """MA 세션 상태 업데이트 요청"""
    return {
        "global_session_key": sample_global_session_key,
        "turn_id": "turn_001",
        "session_state": "talk",
        "state_patch": {
            "subagent_status": "continue",
            "last_agent_id": "agent-transfer",
            "last_agent_type": "task",
            "last_response_type": "continue",
        },
    }


@pytest.fixture
def sample_ma_session_close_request(sample_global_session_key):
    """MA 세션 종료 요청"""
    return {
        "global_session_key": sample_global_session_key,
        "close_reason": "user_exit",
        "final_summary": "이체 완료",
    }


# ============ Portal Request ============


# ============ VDB Request ============


@pytest.fixture
def sample_vdb_batch_request():
    """VDB 배치 프로파일 요청"""
    return {
        "batch_id": "batch_001",
        "source_system": "crm",
        "computed_at": datetime.now(UTC).isoformat(),
        "records": [
            {"user_id": "0616001905", "attributes": [{"key": "segment", "value": "VIP", "source_system": "crm"}], "segment": "VIP"},
            {"user_id": "0616001906", "attributes": [{"key": "segment", "value": "일반", "source_system": "crm"}], "segment": "일반"},
        ],
    }
