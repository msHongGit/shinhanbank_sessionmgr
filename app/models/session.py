"""
Session Manager - Session Model
세션 메타정보 테이블
"""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.models import Base


class SessionStatusEnum(str, enum.Enum):
    """세션 상태"""

    START = "start"
    TALK = "talk"
    END = "end"


class Session(Base):
    """
    Session 테이블

    세션의 기본 메타정보만 저장.
    상태 정보는 SessionStatus 테이블에 분리.
    """

    __tablename__ = "sessions"

    # Primary Key
    session_id = Column(Integer, primary_key=True, autoincrement=True, comment="내부 세션 ID")

    # Business Key (Client 발급)
    global_session_key = Column(String(255), unique=True, nullable=False, index=True, comment="Client가 발급한 Global Session Key")

    # 사용자 정보
    user_id = Column(String(100), nullable=False, index=True, comment="사용자 ID")
    channel = Column(String(50), comment="접속 채널 (mobile/web/etc)")

    # 대화 식별자
    conversation_id = Column(String(255), unique=True, comment="대화 인스턴스 ID")
    context_id = Column(String(255), index=True, comment="대화 이력 식별자")

    # 타임스탬프
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="세션 시작 시각")
    ended_at = Column(DateTime, comment="세션 종료 시각")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 세션 상태 (기본값만, 상세는 SessionStatus 테이블)
    session_status = Column(
        SQLEnum(SessionStatusEnum), default=SessionStatusEnum.START, nullable=False, comment="세션 상태 (start/talk/end)"
    )

    # Relationships
    status_detail = relationship("SessionStatus", back_populates="session", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id={self.session_id}, key={self.global_session_key}, user={self.user_id})>"
