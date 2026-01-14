"""Session Manager - MariaDB Models.

Sprint 3: SQLAlchemy ORM 모델 정의
"""

from datetime import datetime

from sqlalchemy import JSON, TIMESTAMP, Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from app.db.mariadb import Base

# ============================================================================
# 1. Session 모델
# ============================================================================


class SessionModel(Base):
    """세션 모델 (MariaDB)

    Redis에 저장되는 세션 정보를 MariaDB에 영구 저장하기 위한 모델.
    멀티턴 컨텍스트(reference_information, turn_ids) 및 종료 정보 포함.
    """

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    global_session_key = Column(String(255), unique=True, nullable=False, index=True)
    conversation_id = Column(String(255), nullable=False, index=True)
    context_id = Column(String(255), nullable=False)
    channel = Column(String(50))
    user_id = Column(String(255), index=True)
    session_state = Column(String(20), nullable=False, default="start")
    task_queue_status = Column(String(20), default="null")
    subagent_status = Column(String(20), default="undefined")
    action_owner = Column(String(255), comment="현재 액션 담당자")
    
    # 멀티턴 컨텍스트 (핵심 필드)
    reference_information = Column(JSON, comment="멀티턴 컨텍스트 (conversation_history, current_intent, turn_count 등)")
    turn_ids = Column(JSON, comment="누적 턴 ID 목록")
    
    # 이벤트/종료 정보
    start_type = Column(String(50), comment="세션 진입 유형 (event_type, 예: ICON_ENTRY)")
    ended_at = Column(TIMESTAMP(6), comment="세션 종료 시각")
    close_reason = Column(String(100), comment="종료 사유")
    final_summary = Column(String(1000), comment="최종 요약")
    
    # 기타 메타데이터 (JSON)
    session_metadata = Column("metadata", JSON, comment="기타 메타데이터 (customer_profile, cushion_message, last_event, session_attributes 등)")
    profile = Column(JSON, comment="User profile attributes at session creation")
    
    created_at = Column(TIMESTAMP(6), nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(6),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    expires_at = Column(TIMESTAMP(6))

    __table_args__ = (Index("idx_sessions_state_updated", "session_state", "updated_at"),)


# ============================================================================
# 2. Agent Session 모델
# ============================================================================


class AgentSessionModel(Base):
    """에이전트 세션 모델 (구 local_session)"""

    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    global_session_key = Column(
        String(255),
        ForeignKey("sessions.global_session_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_session_key = Column(String(255), nullable=False, index=True)
    agent_id = Column(String(255), nullable=False, index=True)
    agent_type = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(6), nullable=False, server_default=func.current_timestamp())
    last_used_at = Column(
        TIMESTAMP(6),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    expires_at = Column(TIMESTAMP(6))

    __table_args__ = (
        Index("unique_mapping", "global_session_key", "agent_id", unique=True),
        Index("idx_agent_sessions_active", "is_active", "last_used_at"),
    )


# ============================================================================
# 3. Context 모델
# ============================================================================


class ContextModel(Base):
    """컨텍스트 모델"""

    __tablename__ = "contexts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    context_id = Column(String(255), unique=True, nullable=False, index=True)
    global_session_key = Column(
        String(255),
        ForeignKey("sessions.global_session_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    current_intent = Column(String(255))
    current_slots = Column(JSON)
    entities = Column(JSON)
    turn_count = Column(Integer, nullable=False, default=0)
    context_metadata = Column("metadata", JSON)
    created_at = Column(TIMESTAMP(6), nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(6),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


# ============================================================================
# 4. Conversation Turn 모델
# ============================================================================


class ConversationTurnModel(Base):
    """대화 턴 모델 (메타데이터만, 텍스트 제외)"""

    __tablename__ = "conversation_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    turn_id = Column(String(255), unique=True, nullable=False, index=True)
    context_id = Column(
        String(255),
        ForeignKey("contexts.context_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    global_session_key = Column(
        String(255),
        ForeignKey("sessions.global_session_key", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    turn_number = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    agent_id = Column(String(255))
    agent_type = Column(String(50))
    turn_metadata = Column("metadata", JSON, comment="intent, confidence, slots, API 호출 결과 등")
    timestamp = Column(TIMESTAMP(6), nullable=False, server_default=func.current_timestamp(), index=True)

    __table_args__ = (Index("idx_turns_context_number", "context_id", "turn_number"),)


# ============================================================================
# 5. Profile Attribute 모델
# ============================================================================


class ProfileAttributeModel(Base):
    """프로파일 속성 모델 (Context-dependent user attributes)"""

    __tablename__ = "profile_attributes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attribute_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    context_id = Column(String(100), nullable=False, index=True)
    attribute_key = Column(String(100), nullable=False, index=True)
    attribute_value = Column(String(1000))
    source_system = Column(String(100))
    computed_at = Column(TIMESTAMP(6), nullable=False)
    valid_from = Column(TIMESTAMP(6), nullable=False)
    valid_to = Column(TIMESTAMP(6))
    batch_period = Column(String(1), nullable=False, comment="D=Daily, W=Weekly, M=Monthly, A=Ad-hoc")
    permission_scope = Column(JSON, comment="Agent access control")
    created_at = Column(TIMESTAMP(6), nullable=False, server_default=func.current_timestamp())
    updated_at = Column(
        TIMESTAMP(6),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        Index("idx_user_context", "user_id", "context_id"),
        Index("idx_user_key", "user_id", "attribute_key"),
        Index("idx_valid_dates", "valid_from", "valid_to"),
    )
