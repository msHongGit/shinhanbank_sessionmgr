"""
Session Manager - Common Schemas (v3.0)
SM에서 사용하는 공통 타입 정의
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============ Enums ============

class SessionState(str, Enum):
    """세션 상태"""
    START = "start"
    TALK = "talk"
    END = "end"


class AgentType(str, Enum):
    """Agent 유형"""
    KNOWLEDGE = "knowledge"  # 지식 Agent
    TASK = "task"            # 업무 Agent


class ResponseType(str, Enum):
    """SA 응답 타입 (SM이 기록용으로 사용)"""
    CONTINUE = "continue"
    END = "end"
    FALLBACK = "fallback"


class FallbackReason(str, Enum):
    """Fallback 사유 코드"""
    INTENT_ERROR = "INTENT_ERROR"
    SLOT_FILLING_FAIL = "SLOT_FILLING_FAIL"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class TaskQueueStatus(str, Enum):
    """Task Queue 상태"""
    NULL = "null"
    NOTNULL = "notnull"


class SubAgentStatus(str, Enum):
    """SubAgent 상태"""
    UNDEFINED = "undefined"
    CONTINUE = "continue"
    END = "end"


# ============ Common Models ============

class ProfileAttribute(BaseModel):
    """고객 프로파일 속성"""
    key: str = Field(..., description="속성 키")
    value: str = Field(..., description="속성 값")
    source_system: str = Field(..., description="소스 시스템")
    valid_from: str | None = Field(None, description="유효 시작일")
    valid_to: str | None = Field(None, description="유효 종료일")


class CustomerProfile(BaseModel):
    """고객 프로파일"""
    user_id: str = Field(..., description="사용자 ID")
    attributes: list[ProfileAttribute] = Field(default=[], description="속성 목록")
    segment: str | None = Field(None, description="고객 세그먼트")
    preferences: dict[str, Any] | None = Field(None, description="고객 선호 설정")


class ConversationTurn(BaseModel):
    """대화 턴"""
    turn_id: str = Field(..., description="턴 ID")
    role: str = Field(..., description="user | assistant")
    content: str = Field(..., description="메시지 내용")
    timestamp: datetime = Field(..., description="메시지 시각")


class ConversationHistory(BaseModel):
    """대화 이력"""
    context_id: str = Field(..., description="Context ID")
    global_session_key: str = Field(..., description="Global 세션 키")
    turns: list[ConversationTurn] = Field(default=[], description="대화 턴 목록")


class ErrorResponse(BaseModel):
    """에러 응답"""
    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    detail: str | None = Field(None, description="상세 정보")
