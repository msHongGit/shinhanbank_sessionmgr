"""
Session Manager - MariaDB Session Repository Integration Tests

MariaDB 세션 저장 로직에 대한 통합 테스트
- Redis 세션 스냅샷을 MariaDB에 저장하는 로직 검증
- Agent 세션 매핑 저장 검증
"""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.db.mariadb import SessionLocal
from app.models.mariadb_models import AgentSessionModel, SessionModel
from app.repositories.mariadb_session_repository import MariaDBSessionRepository


@pytest.fixture
def db_session():
    """MariaDB 세션 제공 (테스트용)"""
    if SessionLocal is None:
        pytest.skip("MariaDB not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def mariadb_repo(db_session: Session):
    """MariaDBSessionRepository 인스턴스"""
    return MariaDBSessionRepository(db_session)


@pytest.fixture
def sample_session_data():
    """샘플 Redis 세션 데이터"""
    return {
        "global_session_key": "gsess_test_001",
        "user_id": "user_test_001",
        "channel": "web",
        "conversation_id": "",
        "context_id": "ctx_test_001",
        "session_state": "talk",
        "task_queue_status": "notnull",
        "subagent_status": "continue",
        "action_owner": "agent-transfer",
        "start_type": "ICON_ENTRY",
        "reference_information": json.dumps(
            {
                "conversation_history": [
                    {"role": "user", "content": "계좌 이체를 하고 싶어요"},
                    {"role": "assistant", "content": "계좌번호를 알려주세요"},
                ],
                "current_intent": "계좌이체",
                "turn_count": 2,
            }
        ),
        "turn_ids": json.dumps(["turn_001", "turn_002"]),
        "customer_profile": json.dumps(
            {
                "user_id": "user_test_001",
                "attributes": [{"key": "segment", "value": "VIP", "source_system": "crm"}],
                "segment": "VIP",
            }
        ),
        "cushion_message": "잠시만 기다려주세요",
        "session_attributes": json.dumps({"custom_key": "custom_value"}),
        "last_event": json.dumps(
            {
                "event_type": "AGENT_RESPONSE",
                "agent_id": "agent-transfer",
                "agent_type": "task",
                "response_type": "continue",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC).replace(hour=23, minute=59, second=59)).isoformat(),
    }


@pytest.fixture
def sample_agent_mapping():
    """샘플 Agent 매핑 데이터"""
    return {
        "global_session_key": "gsess_test_001",
        "agent_id": "agent-transfer",
        "agent_session_key": "lsess_transfer_001",
        "agent_type": "task",
    }


class TestMariaDBSessionRepository:
    """MariaDB Session Repository 테스트"""

    def test_create_session(self, mariadb_repo: MariaDBSessionRepository, sample_session_data: dict, db_session: Session):
        """세션 생성 테스트"""
        # 세션 생성
        session_model = mariadb_repo.create_or_update(
            global_session_key=sample_session_data["global_session_key"],
            session_data=sample_session_data,
        )

        # 검증
        assert session_model is not None
        assert session_model.global_session_key == sample_session_data["global_session_key"]
        assert session_model.user_id == sample_session_data["user_id"]
        assert session_model.channel == sample_session_data["channel"]
        assert session_model.session_state == sample_session_data["session_state"]
        assert session_model.task_queue_status == sample_session_data["task_queue_status"]
        assert session_model.subagent_status == sample_session_data["subagent_status"]
        assert session_model.action_owner == sample_session_data["action_owner"]
        assert session_model.start_type == sample_session_data["start_type"]

        # JSON 필드 검증
        assert session_model.reference_information is not None
        assert isinstance(session_model.reference_information, dict)
        assert "conversation_history" in session_model.reference_information
        assert len(session_model.reference_information["conversation_history"]) == 2

        assert session_model.turn_ids is not None
        assert isinstance(session_model.turn_ids, list)
        assert len(session_model.turn_ids) == 2

        assert session_model.session_metadata is not None
        assert "customer_profile" in session_model.session_metadata
        assert "cushion_message" in session_model.session_metadata
        assert session_model.session_metadata["cushion_message"] == "잠시만 기다려주세요"

        # DB에서 직접 조회하여 검증
        db_session.refresh(session_model)
        assert session_model.created_at is not None
        assert session_model.updated_at is not None

    def test_update_session(self, mariadb_repo: MariaDBSessionRepository, sample_session_data: dict, db_session: Session):
        """세션 업데이트 테스트"""
        # 초기 세션 생성
        session_model = mariadb_repo.create_or_update(
            global_session_key=sample_session_data["global_session_key"],
            session_data=sample_session_data,
        )
        original_updated_at = session_model.updated_at

        # 업데이트 데이터 준비
        updated_data = sample_session_data.copy()
        updated_data["session_state"] = "end"
        updated_data["close_reason"] = "user_exit"
        updated_data["ended_at"] = datetime.now(UTC).isoformat()
        updated_data["final_summary"] = "이체 완료"

        # 세션 업데이트
        updated_model = mariadb_repo.create_or_update(
            global_session_key=sample_session_data["global_session_key"],
            session_data=updated_data,
        )

        # 검증
        assert updated_model.id == session_model.id  # 같은 레코드
        assert updated_model.session_state == "end"
        assert updated_model.close_reason == "user_exit"
        assert updated_model.final_summary == "이체 완료"
        assert updated_model.ended_at is not None

    def test_create_agent_mapping(self, mariadb_repo: MariaDBSessionRepository, sample_agent_mapping: dict, db_session: Session):
        """Agent 매핑 생성 테스트"""
        # Agent 매핑 생성
        mapping_model = mariadb_repo.create_or_update_agent_mapping(
            global_session_key=sample_agent_mapping["global_session_key"],
            agent_id=sample_agent_mapping["agent_id"],
            agent_session_key=sample_agent_mapping["agent_session_key"],
            agent_type=sample_agent_mapping["agent_type"],
        )

        # 검증
        assert mapping_model is not None
        assert mapping_model.global_session_key == sample_agent_mapping["global_session_key"]
        assert mapping_model.agent_id == sample_agent_mapping["agent_id"]
        assert mapping_model.agent_session_key == sample_agent_mapping["agent_session_key"]
        assert mapping_model.agent_type == sample_agent_mapping["agent_type"]
        assert mapping_model.is_active is True

        # DB에서 직접 조회하여 검증
        db_session.refresh(mapping_model)
        assert mapping_model.created_at is not None
        assert mapping_model.last_used_at is not None

    def test_update_agent_mapping(self, mariadb_repo: MariaDBSessionRepository, sample_agent_mapping: dict, db_session: Session):
        """Agent 매핑 업데이트 테스트"""
        # 초기 매핑 생성
        mapping_model = mariadb_repo.create_or_update_agent_mapping(
            global_session_key=sample_agent_mapping["global_session_key"],
            agent_id=sample_agent_mapping["agent_id"],
            agent_session_key=sample_agent_mapping["agent_session_key"],
            agent_type=sample_agent_mapping["agent_type"],
        )

        # 업데이트 (새로운 agent_session_key)
        updated_mapping = mariadb_repo.create_or_update_agent_mapping(
            global_session_key=sample_agent_mapping["global_session_key"],
            agent_id=sample_agent_mapping["agent_id"],
            agent_session_key="lsess_transfer_002",  # 새로운 키
            agent_type=sample_agent_mapping["agent_type"],
        )

        # 검증
        assert updated_mapping.id == mapping_model.id  # 같은 레코드
        assert updated_mapping.agent_session_key == "lsess_transfer_002"
        assert updated_mapping.is_active is True

    def test_get_session(self, mariadb_repo: MariaDBSessionRepository, sample_session_data: dict):
        """세션 조회 테스트"""
        # 세션 생성
        mariadb_repo.create_or_update(
            global_session_key=sample_session_data["global_session_key"],
            session_data=sample_session_data,
        )

        # 조회
        session_model = mariadb_repo.get_session(sample_session_data["global_session_key"])

        # 검증
        assert session_model is not None
        assert session_model.global_session_key == sample_session_data["global_session_key"]

    def test_get_agent_mapping(self, mariadb_repo: MariaDBSessionRepository, sample_agent_mapping: dict):
        """Agent 매핑 조회 테스트"""
        # 매핑 생성
        mariadb_repo.create_or_update_agent_mapping(
            global_session_key=sample_agent_mapping["global_session_key"],
            agent_id=sample_agent_mapping["agent_id"],
            agent_session_key=sample_agent_mapping["agent_session_key"],
            agent_type=sample_agent_mapping["agent_type"],
        )

        # 조회
        mapping_model = mariadb_repo.get_agent_mapping(
            global_session_key=sample_agent_mapping["global_session_key"],
            agent_id=sample_agent_mapping["agent_id"],
        )

        # 검증
        assert mapping_model is not None
        assert mapping_model.agent_id == sample_agent_mapping["agent_id"]
        assert mapping_model.agent_session_key == sample_agent_mapping["agent_session_key"]

    def test_json_field_parsing(self, mariadb_repo: MariaDBSessionRepository, db_session: Session):
        """JSON 필드 파싱 테스트 (다양한 형식 지원)"""
        # 문자열 형식의 JSON
        session_data_str = {
            "global_session_key": "gsess_json_test",
            "user_id": "user_json_test",
            "channel": "web",
            "conversation_id": "",
            "context_id": "ctx_json_test",
            "session_state": "start",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "reference_information": json.dumps({"test": "value"}),
            "turn_ids": json.dumps(["turn_1", "turn_2"]),
        }

        session_model = mariadb_repo.create_or_update("gsess_json_test", session_data_str)
        assert isinstance(session_model.reference_information, dict)
        assert session_model.reference_information["test"] == "value"
        assert isinstance(session_model.turn_ids, list)
        assert len(session_model.turn_ids) == 2

        # dict 형식의 JSON (이미 파싱된 상태)
        session_data_dict = {
            "global_session_key": "gsess_json_test",
            "user_id": "user_json_test",
            "channel": "web",
            "conversation_id": "",
            "context_id": "ctx_json_test",
            "session_state": "start",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "reference_information": {"test": "value2"},
            "turn_ids": ["turn_3", "turn_4"],
        }

        session_model2 = mariadb_repo.create_or_update("gsess_json_test", session_data_dict)
        assert isinstance(session_model2.reference_information, dict)
        assert session_model2.reference_information["test"] == "value2"
        assert isinstance(session_model2.turn_ids, list)
        assert len(session_model2.turn_ids) == 2
