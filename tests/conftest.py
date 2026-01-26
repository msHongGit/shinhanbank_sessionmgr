"""
Session Manager - Test Configuration and Fixtures (v4.0)
Sprint 2: Redis Integration Tests
"""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

# 모든 환경에서 REDIS_URL 필수
# - 로컬: .env 파일에 Azure Redis 설정
# - CI: GitHub Actions workflow에서 설정

# v4.0: 테스트에서는 실제 Redis를 사용하고, Profile만 Mock으로 주입
from app.main import app
from app.repositories.mock import MockProfileRepository
from app.schemas import (
    ConversationTurn,
    CustomerProfile,
    ProfileAttribute,
)
from app.services.session_service import SessionService


@pytest.fixture
def client():
    """FastAPI TestClient using real Redis for sessions/contexts and Mock profile data."""

    from app.api.v1.sessions import get_session_service

    profile_repo = MockProfileRepository()

    # SessionService는 기본적으로 RedisSessionRepository를 사용하고,
    # 여기서 Profile Repository만 Mock 으로 주입한다.
    def override_session_service():
        return SessionService(profile_repo=profile_repo)

    app.dependency_overrides[get_session_service] = override_session_service

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_mock_repositories():
    """테스트 간 Mock Profile Repository 상태 보장.

    현재 구현에서는 MockProfileRepository 가 내부적으로 demo/user_vip 사용자에 대한
    고정 데이터를 가지고 있으므로, 여기서는 인스턴스 초기화만 보장한다.
    """

    MockProfileRepository()  # singleton 초기화 (mock 데이터 로드)
    yield


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
        cusnoS10="0616001905",
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
