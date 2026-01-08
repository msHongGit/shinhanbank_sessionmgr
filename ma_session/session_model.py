"""Session data model for conversation lifecycle management.

Models:
- SessionState: External session state (start/talk/end)
- SessionStatus: Internal session status (Active/Inactive/Expired)
- ConversationStatus: Conversation phase (Start/Active/Ended)
- SubAgentStatus: Sub-agent lifecycle status
- LastEvent: Last event metadata
- Session: Complete session state with lifecycle tracking
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionState(str, Enum):
    """External session state as defined by Session Manager.

    - START: Session initiated
    - TALK: Active conversation
    - END: Session closed
    """

    START = "start"
    TALK = "talk"
    END = "end"


class SessionStatus(str, Enum):
    """Internal session lifecycle status.

    - ACTIVE: Session is active and accepting requests
    - INACTIVE: Session temporarily paused
    - EXPIRED: Session TTL exceeded
    """

    ACTIVE = "Active"
    INACTIVE = "Inactive"
    EXPIRED = "Expired"


class ConversationStatus(str, Enum):
    """Conversation phase within a session.

    - START: Conversation just started
    - ACTIVE: Ongoing conversation
    - ENDED: Conversation completed
    """

    START = "Start"
    ACTIVE = "Active"
    ENDED = "Ended"


class SubAgentStatus(str, Enum):
    """Sub-agent lifecycle status from Session Manager.

    - UNDEFINED: No sub-agent engaged
    - CONTINUE: Sub-agent needs more turns
    - END: Sub-agent completed task
    """

    UNDEFINED = "undefined"
    CONTINUE = "continue"
    END = "end"


class LastEvent(BaseModel):
    """Metadata about the last event in the session.

    Tracks the most recent action for debugging and state management.
    """

    event_type: str | None = Field(None, description="이벤트 타입 (Event type)")
    agent_id: str | None = Field(None, description="에이전트 ID (Agent ID)")
    agent_type: str | None = Field(None, description="에이전트 타입 (Agent type)")
    response_type: str | None = Field(None, description="응답 타입 (Response type)")
    updated_at: datetime | None = Field(None, description="업데이트 시각 (Update timestamp)")

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "agent_response",
                "agent_id": "skillset-001",
                "agent_type": "skillset",
                "response_type": "Final",
                "updated_at": "2026-01-02T15:30:00Z",
            }
        }


class Session(BaseModel):
    """Complete session state for conversation lifecycle management.

    Represents a user's conversation session with comprehensive state tracking,
    including Session Manager integration, customer profile, task queue status,
    and lifecycle metadata.

    Attributes:
        session_id: Internal unique session identifier
        global_session_key: External session key from Session Manager
        conversation_id: External conversation identifier
        context_id: External context identifier
        local_session_keys: Map of agent to local session keys
        user_id: Associated user identifier
        conversation_status: Current conversation phase
        session_state: External session state (start/talk/end)
        channel: Communication channel (utterance, web, app, etc.)
        created_at: Session creation timestamp
        updated_at: Last update timestamp
        last_activity_at: Last user/agent activity timestamp
        failure_count: Number of failures in this session
        ttl: Time-to-live in seconds
        metadata: Custom metadata key-value pairs
        customer_profile_ref: Reference to customer profile (external ID)
        context: Conversation context (slots, entities, history)
        task_queue_status: Current task queue status
        subagent_status: Sub-agent lifecycle status
        last_event: Last event metadata
        action_owner: Owner of the last action
        reference_information: Supplemental reference data
        cushion_message: Cushion message for user
        last_response_type: Last response type (Final/AskBack/Cushion/Fallback)
        turn_id: Current turn identifier
        is_first_call: Whether this is the first call in session
        close_reason: Reason for session closure
        final_summary: Final conversation summary
        ended_at: Session end timestamp
        archived_conversation_id: Archived conversation ID
        expires_at: Session expiration timestamp
    """

    # Core identifiers
    session_id: str = Field(..., description="세션 ID (Session ID)")
    global_session_key: str | None = Field(None, description="전역 세션 키 (Global session key from Session Manager)")
    conversation_id: str | None = Field(None, description="대화 ID (Conversation ID)")
    context_id: str | None = Field(None, description="컨텍스트 ID (Context ID)")
    local_session_keys: dict[str, str] = Field(default_factory=dict, description="로컬 세션 키 맵 (Map of agent_type to local_session_key)")

    # User information
    user_id: str | None = Field(None, description="사용자 ID (User ID)")
    customer_profile_ref: str | None = Field(None, description="고객 프로파일 참조 (Customer profile reference ID)")

    # Session state
    conversation_status: ConversationStatus = Field(ConversationStatus.START, description="대화 상태 (Conversation status)")
    session_state: SessionState | None = Field(SessionState.START, description="세션 상태 (Session state: start/talk/end)")
    channel: str = Field("utterance", description="채널 (Communication channel)")

    # Lifecycle timestamps
    created_at: datetime = Field(..., description="생성 시각 (Created timestamp)")
    updated_at: datetime = Field(..., description="수정 시각 (Updated timestamp)")
    last_activity_at: datetime = Field(..., description="마지막 활동 시각 (Last activity timestamp)")
    ended_at: datetime | None = Field(None, description="종료 시각 (Session end timestamp)")
    expires_at: datetime | None = Field(None, description="만료 시각 (Session expiration timestamp)")

    # Session management
    failure_count: int = Field(0, description="실패 횟수 (Failure count)")
    ttl: int = Field(3600, description="TTL (초) (Time-to-live in seconds)")

    # Metadata and context
    metadata: dict[str, Any] = Field(default_factory=dict, description="메타데이터 (Custom metadata)")
    context: dict[str, Any] = Field(default_factory=dict, description="대화 컨텍스트 (Conversation context: slots, entities, etc.)")
    reference_information: dict[str, Any] = Field(default_factory=dict, description="참조 정보 (Reference information)")

    # Agent and task tracking
    task_queue_status: str | None = Field(None, description="태스크 큐 상태 (Task queue status)")
    subagent_status: SubAgentStatus | None = Field(None, description="서브에이전트 상태 (Sub-agent status)")
    last_event: LastEvent | None = Field(None, description="마지막 이벤트 (Last event metadata)")
    action_owner: str | None = Field(None, description="액션 소유자 (Action owner: MA/SA/etc.)")

    # Response tracking
    cushion_message: str | None = Field(None, description="쿠션 메시지 (Cushion message)")
    last_response_type: str | None = Field(None, description="마지막 응답 타입 (Last response type: Final/AskBack/etc.)")
    turn_id: str | None = Field(None, description="턴 ID (Turn ID)")
    is_first_call: bool | None = Field(None, description="첫 호출 여부 (Whether this is the first call)")

    # Session closure
    close_reason: str | None = Field(None, description="종료 사유 (Close reason)")
    final_summary: str | None = Field(None, description="최종 요약 (Final summary)")
    archived_conversation_id: str | None = Field(None, description="아카이빙된 대화 ID (Archived conversation ID)")

    def is_expired(self, current_time: datetime) -> bool:
        """Check if session has expired.

        Args:
            current_time: Current timestamp

        Returns:
            True if session expired, False otherwise
        """
        if self.expires_at:
            return current_time >= self.expires_at
        return False

    def is_active(self) -> bool:
        """Check if session is active.

        Returns:
            True if session is in active conversation state
        """
        return self.session_state in [SessionState.START, SessionState.TALK] and self.conversation_status != ConversationStatus.ENDED

    def increment_failure(self) -> None:
        """Increment failure count."""
        self.failure_count += 1

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess-abc12345",
                "global_session_key": "gsk-xyz789",
                "conversation_id": "conv-456def",
                "context_id": "ctx-2025-000457",
                "local_session_keys": {"skillset": "lsk-skill-001", "knowledge": "lsk-know-002"},
                "user_id": "user_1084756",
                "customer_profile_ref": "profile-user-1084756-ctx-000457",
                "conversation_status": "Active",
                "session_state": "talk",
                "channel": "utterance",
                "created_at": "2026-01-02T14:00:00Z",
                "updated_at": "2026-01-02T14:30:00Z",
                "last_activity_at": "2026-01-02T14:30:00Z",
                "ended_at": None,
                "expires_at": "2026-01-02T15:00:00Z",
                "failure_count": 0,
                "ttl": 3600,
                "metadata": {"source": "mobile_app", "version": "1.0.0"},
                "context": {"last_intent": "account_inquiry", "slots": {"account_type": "체크카드"}},
                "reference_information": {},
                "task_queue_status": "pending",
                "subagent_status": "undefined",
                "last_event": {
                    "event_type": "agent_response",
                    "agent_id": "skillset-001",
                    "agent_type": "skillset",
                    "response_type": "Final",
                    "updated_at": "2026-01-02T14:30:00Z",
                },
                "action_owner": "MA",
                "cushion_message": None,
                "last_response_type": "Final",
                "turn_id": "turn-5",
                "is_first_call": False,
                "close_reason": None,
                "final_summary": None,
                "archived_conversation_id": None,
            }
        }


class SessionSnapshot(BaseModel):
    """Lightweight session snapshot for API responses.

    Contains only public session information without sensitive internal state.
    """

    session_id: str = Field(..., description="세션 ID (Session ID)")
    status: SessionStatus = Field(..., description="상태 (Session status)")
    created_at: datetime = Field(..., description="생성 시각 (Created timestamp)")
    updated_at: datetime = Field(..., description="수정 시각 (Updated timestamp)")
    last_activity_at: datetime = Field(..., description="마지막 활동 시각 (Last activity timestamp)")
    failure_count: int = Field(0, description="실패 횟수 (Failure count)")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess-abc12345",
                "status": "Active",
                "created_at": "2026-01-02T14:00:00Z",
                "updated_at": "2026-01-02T14:30:00Z",
                "last_activity_at": "2026-01-02T14:30:00Z",
                "failure_count": 0,
            }
        }
