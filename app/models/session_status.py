"""
Session Manager - SessionStatus Model
세션 상태 상세 정보 테이블 (Session과 1:1 관계)
"""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.models import Base


class ConversationStatusEnum(str, enum.Enum):
    """대화 상태"""
    START = "start"
    TALK = "talk"
    END = "end"


class TaskQueueStatusEnum(str, enum.Enum):
    """Task Queue 상태"""
    NULL = "null"           # 큐 비어있음
    PENDING = "pending"     # 대기 중
    PROCESSING = "processing"  # 처리 중


class SubAgentStatusEnum(str, enum.Enum):
    """SubAgent 상태"""
    UNDEFINED = "undefined"  # 정의되지 않음
    CONTINUE = "continue"    # 계속 진행
    END = "end"             # 종료
    ERROR = "error"         # 에러


class SessionStatus(Base):
    """
    SessionStatus 테이블 (정규화)
    
    Session 테이블과 1:1 관계로 분리.
    세션 상태의 상세 정보와 이벤트 정보를 저장.
    """
    __tablename__ = "session_status"

    # Primary Key (Session FK)
    session_id = Column(
        Integer,
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        primary_key=True,
        comment="세션 ID (FK)"
    )

    # 중복 user_id (빠른 조회용)
    user_id = Column(String(100), nullable=False, index=True, comment="사용자 ID")

    # 이벤트 정보
    event_source = Column(String(50), comment="이벤트 발생 소스 (AGW/MA/SA)")
    event_type = Column(String(50), comment="이벤트 타입 (start/talk/end)")

    # 대화 상태
    conversation_status = Column(
        SQLEnum(ConversationStatusEnum),
        default=ConversationStatusEnum.START,
        nullable=False,
        comment="대화 상태"
    )

    # Task Queue 상태
    task_queue_status = Column(
        SQLEnum(TaskQueueStatusEnum),
        default=TaskQueueStatusEnum.NULL,
        nullable=False,
        comment="Task Queue 상태"
    )

    # SubAgent 상태
    subagent_status = Column(
        SQLEnum(SubAgentStatusEnum),
        default=SubAgentStatusEnum.UNDEFINED,
        nullable=False,
        comment="SubAgent 상태"
    )

    # 액션 정보
    action_owner = Column(String(100), comment="현재 액션 담당자 (agent_id)")

    # 참조 정보 (JSON 문자열)
    reference_information = Column(Text, comment="참조 정보 (JSON)")

    # 쿠션 메시지
    cushion_message = Column(Text, comment="쿠션 메시지")

    # 타임스탬프
    last_event_at = Column(DateTime, default=datetime.utcnow, comment="마지막 이벤트 시각")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="status_detail")

    def __repr__(self):
        return (
            f"<SessionStatus(session_id={self.session_id}, "
            f"conversation={self.conversation_status}, "
            f"subagent={self.subagent_status})>"
        )
