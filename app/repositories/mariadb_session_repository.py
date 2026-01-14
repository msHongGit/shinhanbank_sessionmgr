"""
Session Manager - MariaDB Session Repository
Sprint 3+: Session 영구 저장소 (비동기 저장용)
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.utils import safe_datetime_parse, safe_json_parse
from app.models.mariadb_models import AgentSessionModel, SessionModel


class MariaDBSessionRepository:
    """MariaDB Session Repository (비동기 저장용)

    Redis에 저장된 세션 스냅샷을 MariaDB에 영구 저장한다.
    BackgroundTasks에서 호출되어 비동기로 실행된다.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_or_update(self, global_session_key: str, session_data: dict[str, Any]) -> SessionModel:
        """세션 생성 또는 업데이트 (Redis 스냅샷 기반)

        Args:
            global_session_key: 세션 키
            session_data: Redis에서 읽은 세션 딕셔너리

        Returns:
            생성/업데이트된 SessionModel
        """
        # 기존 세션 조회
        session_model = (
            self.db.query(SessionModel).filter(SessionModel.global_session_key == global_session_key).first()
        )

        # JSON 필드 파싱 (유틸리티 함수 사용)
        reference_information = safe_json_parse(session_data.get("reference_information"))
        turn_ids = safe_json_parse(session_data.get("turn_ids"))
        customer_profile = safe_json_parse(session_data.get("customer_profile"))

        # session_metadata 구성 (기타 필드들)
        session_metadata: dict[str, Any] = {}
        if customer_profile:
            session_metadata["customer_profile"] = customer_profile
        if session_data.get("cushion_message"):
            session_metadata["cushion_message"] = session_data.get("cushion_message")
        session_attributes = safe_json_parse(session_data.get("session_attributes"))
        if session_attributes:
            session_metadata["session_attributes"] = session_attributes
        last_event = safe_json_parse(session_data.get("last_event"))
        if last_event:
            session_metadata["last_event"] = last_event

        # datetime 필드 파싱 (유틸리티 함수 사용)
        ended_at = safe_datetime_parse(session_data.get("ended_at"))
        expires_at = safe_datetime_parse(session_data.get("expires_at"))

        if session_model:
            # 업데이트
            session_model.conversation_id = session_data.get("conversation_id", "")
            session_model.context_id = session_data.get("context_id", "")
            session_model.channel = session_data.get("channel")
            session_model.user_id = session_data.get("user_id", "")
            session_model.session_state = session_data.get("session_state", "start")
            session_model.task_queue_status = session_data.get("task_queue_status", "null")
            session_model.subagent_status = session_data.get("subagent_status", "undefined")
            session_model.action_owner = session_data.get("action_owner")
            session_model.reference_information = reference_information
            session_model.turn_ids = turn_ids
            session_model.start_type = session_data.get("start_type")
            session_model.ended_at = ended_at
            session_model.close_reason = session_data.get("close_reason")
            session_model.final_summary = session_data.get("final_summary")
            session_model.session_metadata = session_metadata if session_metadata else None
            profile_data = safe_json_parse(session_data.get("profile"))
            if profile_data:
                session_model.profile = profile_data
            session_model.expires_at = expires_at
        else:
            # 생성
            profile_data = safe_json_parse(session_data.get("profile"), default={})

            session_model = SessionModel(
                global_session_key=global_session_key,
                conversation_id=session_data.get("conversation_id", ""),
                context_id=session_data.get("context_id", ""),
                channel=session_data.get("channel"),
                user_id=session_data.get("user_id", ""),
                session_state=session_data.get("session_state", "start"),
                task_queue_status=session_data.get("task_queue_status", "null"),
                subagent_status=session_data.get("subagent_status", "undefined"),
                action_owner=session_data.get("action_owner"),
                reference_information=reference_information,
                turn_ids=turn_ids,
                start_type=session_data.get("start_type"),
                ended_at=ended_at,
                close_reason=session_data.get("close_reason"),
                final_summary=session_data.get("final_summary"),
                session_metadata=session_metadata if session_metadata else None,
                profile=profile_data,
                expires_at=expires_at,
            )
            self.db.add(session_model)

        self.db.commit()
        self.db.refresh(session_model)
        return session_model

    def create_or_update_agent_mapping(
        self,
        global_session_key: str,
        agent_id: str,
        agent_session_key: str,
        agent_type: str,
    ) -> AgentSessionModel:
        """Agent 세션 매핑 생성 또는 업데이트

        Args:
            global_session_key: Global 세션 키
            agent_id: Agent ID
            agent_session_key: Agent 로컬 세션 키
            agent_type: Agent 타입 (task/knowledge)

        Returns:
            생성/업데이트된 AgentSessionModel
        """
        # 기존 매핑 조회
        mapping = (
            self.db.query(AgentSessionModel)
            .filter(
                AgentSessionModel.global_session_key == global_session_key,
                AgentSessionModel.agent_id == agent_id,
            )
            .first()
        )

        if mapping:
            # 업데이트
            mapping.agent_session_key = agent_session_key
            mapping.agent_type = agent_type
            mapping.is_active = True
        else:
            # 생성
            mapping = AgentSessionModel(
                global_session_key=global_session_key,
                agent_id=agent_id,
                agent_session_key=agent_session_key,
                agent_type=agent_type,
                is_active=True,
            )
            self.db.add(mapping)

        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def get_session(self, global_session_key: str) -> SessionModel | None:
        """세션 조회"""
        return self.db.query(SessionModel).filter(SessionModel.global_session_key == global_session_key).first()

    def get_agent_mapping(self, global_session_key: str, agent_id: str) -> AgentSessionModel | None:
        """Agent 세션 매핑 조회"""
        return (
            self.db.query(AgentSessionModel)
            .filter(
                AgentSessionModel.global_session_key == global_session_key,
                AgentSessionModel.agent_id == agent_id,
                AgentSessionModel.is_active == True,  # noqa: E712
            )
            .first()
        )
