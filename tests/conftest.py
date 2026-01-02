"""
Session Manager - Test Configuration and Fixtures (v4.0)
Sprint 1: Mock Repository 사용
"""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

# CI 환경에서 Redis URL 설정 (GitHub Actions service container용)
if "REDIS_URL" not in os.environ:
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.config import settings

# v4.0: Mock Repository 사용으로 DB patching 불필요
from app.main import app
from app.repositories.mock import MockContextRepository, MockProfileRepository, MockSessionRepository
from app.schemas import (
    ConversationTurn,
    CustomerProfile,
    ProfileAttribute,
)


@pytest.fixture
def client():
    """FastAPI TestClient"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_mock_repositories():
    """테스트 간 Mock Repository 상태 초기화"""
    # 싱글톤 인스턴스의 데이터 초기화
    session_repo = MockSessionRepository()
    context_repo = MockContextRepository()
    MockProfileRepository()  # Initialize singleton

    session_repo._sessions.clear()
    session_repo._local_mappings.clear()
    context_repo._contexts.clear()
    context_repo._turns.clear()
    # profile은 mock 데이터 유지

    yield


# ============ API Keys (호출자별) ============


@pytest.fixture
def agw_headers():
    """AGW API headers"""
    return {"X-API-Key": settings.AGW_API_KEY, "Content-Type": "application/json"}


@pytest.fixture
def ma_headers():
    """MA API headers"""
    return {"X-API-Key": settings.MA_API_KEY, "Content-Type": "application/json"}


@pytest.fixture
def portal_headers():
    """Portal API headers"""
    return {"X-API-Key": settings.PORTAL_API_KEY, "Content-Type": "application/json"}


@pytest.fixture
def vdb_headers():
    """VDB API headers"""
    return {"X-API-Key": settings.VDB_API_KEY, "Content-Type": "application/json"}


# ============ Sample Data ============


@pytest.fixture
def sample_global_session_key():
    """샘플 Global 세션 키 (Client가 발급)"""
    return "gsess_20250316_user_001"


@pytest.fixture
def sample_local_session_key():
    """샘플 Local 세션 키 (업무 Agent가 발급)"""
    return "lsess_transfer_001"


@pytest.fixture
def sample_context_id():
    """샘플 Context ID"""
    return "ctx_20250316_001"


@pytest.fixture
def sample_customer_profile():
    """샘플 고객 프로파일"""
    return CustomerProfile(
        user_id="user_001",
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
    return {"global_session_key": sample_global_session_key, "user_id": "user_001", "channel": "mobile", "request_id": "req_001"}


# ============ MA Requests ============


@pytest.fixture
def sample_ma_local_register_request(sample_global_session_key, sample_local_session_key):
    """MA Local 세션 등록 요청"""
    return {
        "global_session_key": sample_global_session_key,
        "local_session_key": sample_local_session_key,
        "agent_id": "agent-transfer",
        "agent_type": "task",
    }


@pytest.fixture
def sample_ma_session_patch_request(sample_global_session_key):
    """MA 세션 상태 업데이트 요청"""
    return {
        "global_session_key": sample_global_session_key,
        "conversation_id": "conv_001",
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
        "conversation_id": "conv_001",
        "close_reason": "user_exit",
        "final_summary": "이체 완료",
    }


@pytest.fixture
def sample_ma_turn_save_request(sample_global_session_key, sample_context_id, sample_conversation_turn):
    """MA 대화 턴 저장 요청"""
    return {"global_session_key": sample_global_session_key, "context_id": sample_context_id, "turn": sample_conversation_turn.model_dump()}


# ============ Portal Request ============


@pytest.fixture
def sample_portal_context_delete_request(sample_context_id):
    """Portal Context 삭제 요청"""
    return {"context_id": sample_context_id, "reason": "사용자 요청"}


# ============ VDB Request ============


@pytest.fixture
def sample_vdb_batch_request():
    """VDB 배치 프로파일 요청"""
    return {
        "batch_id": "batch_001",
        "source_system": "crm",
        "computed_at": datetime.now(UTC).isoformat(),
        "records": [
            {"user_id": "user_001", "attributes": [{"key": "segment", "value": "VIP", "source_system": "crm"}], "segment": "VIP"},
            {"user_id": "user_002", "attributes": [{"key": "segment", "value": "일반", "source_system": "crm"}], "segment": "일반"},
        ],
    }
