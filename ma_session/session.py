"""Session data models for session lifecycle management.

Models:
- SessionStatus: Current state of a session (Active, Inactive, Expired)
- ConversationStatus: Conversation phase (Start, Active, Ended)
- CustomerProfile: Customer profile with attributes for personalization
- SessionRequest: Request to create a new session
- Session: Internal session state (full data)
- SessionSnapshot: Response model (public data for API)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionState(str, Enum):
    """External session state as defined by Session Manager."""

    START = "start"
    TALK = "talk"
    END = "end"


class SubAgentStatus(str, Enum):
    """Sub-agent lifecycle status from Session Manager."""

    UNDEFINED = "undefined"
    CONTINUE = "continue"
    END = "end"


class LastEvent(BaseModel):
    """Last event metadata returned by Session Manager."""

    event_type: str | None = None
    agent_id: str | None = None
    agent_type: str | None = None
    response_type: str | None = None
    updated_at: datetime | None = None


class SessionStatus(str, Enum):
    """Session lifecycle states."""

    ACTIVE = "Active"
    INACTIVE = "Inactive"
    EXPIRED = "Expired"


class ConversationStatus(str, Enum):
    """Conversation status within a session."""

    START = "Start"
    ACTIVE = "Active"
    ENDED = "Ended"


class CustomerProfile(BaseModel):
    """Customer profile for personalization.

    Simple key-value store for customer attributes.
    """

    customer_id: str
    attributes: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "customer_id": "CUST-12345",
                "attributes": {
                    "name": "홍길동",
                    "tier": "VIP",
                    "preferred_language": "ko",
                    "account_type": "premium",
                },
            }
        }


class SessionRequest(BaseModel):
    """Request to create a new session."""

    user_id: str | None = None
    channel: str = "utterance"
    metadata: dict[str, Any] | None = None


class Session(BaseModel):
    """Complete internal session state.

    Attributes:
        session_id: Unique session identifier
        global_session_key: External global session key from Session Manager
        conversation_id: External conversation identifier
        context_id: External context identifier
        local_session_keys: Map of (agent_type, agent_id) to local_session_key
        user_id: Associated user (if provided)
        conversation_status: Current conversation phase (internal)
        session_state: External session lifecycle state (start/talk/end)
        channel: Communication channel (e.g., "utterance")
        created_at: Session creation timestamp
        updated_at: Last update timestamp
        last_activity_at: Last activity timestamp
        failure_count: Number of failures in this session
        ttl: Time-to-live in seconds
        metadata: Custom metadata key-value pairs
        customer_profile: Embedded customer profile (optional)
        customer_profile_ref: External profile reference (optional)
        context: Conversation context (slots, last_intent, etc.)
        task_queue_status: Task queue status from Session Manager (optional)
        subagent_status: Sub-agent lifecycle status (optional)
        last_event: Last event metadata (optional)
        action_owner: Owner of the last action (optional)
        reference_information: Supplemental reference info (optional)
        cushion_message: Cushion message guidance (optional)
        last_response_type: Last response type reported (optional)
        turn_id: Last turn identifier (optional)
        is_first_call: Whether this is the first call in the session
        close_reason: Reason for closing the session (optional)
        final_summary: Final summary from close (optional)
        ended_at: Session end timestamp (optional)
        archived_conversation_id: Archived conversation ID from close (optional)
        expires_at: Expiration timestamp (optional)
    """

    session_id: str
    global_session_key: str | None = None
    conversation_id: str | None = None
    context_id: str | None = None
    local_session_keys: dict[str, str] = Field(default_factory=dict)
    user_id: str | None = None
    conversation_status: ConversationStatus = ConversationStatus.START
    session_state: SessionState | None = SessionState.START
    channel: str = "utterance"
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    failure_count: int = 0
    ttl: int = 3600  # 1 hour default
    metadata: dict[str, Any] = Field(default_factory=dict)
    customer_profile: CustomerProfile | None = None
    customer_profile_ref: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    task_queue_status: str | None = None
    subagent_status: SubAgentStatus | None = None
    last_event: LastEvent | None = None
    action_owner: str | None = None
    reference_information: dict[str, Any] = Field(default_factory=dict)
    cushion_message: str | None = None
    last_response_type: str | None = None
    turn_id: str | None = None
    is_first_call: bool | None = None
    close_reason: str | None = None
    final_summary: str | None = None
    ended_at: datetime | None = None
    archived_conversation_id: str | None = None
    expires_at: datetime | None = None


class SessionSnapshot(BaseModel):
    """Session snapshot for API responses.

    Contains public session information without internal details.

    Attributes:
        session_id: Unique session identifier
        status: Current session status
        created_at: Creation timestamp
        updated_at: Last update timestamp
        last_activity_at: Last activity timestamp
        failure_count: Number of failures
    """

    session_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime
    failure_count: int = 0


class SessionUpdateRequest(BaseModel):
    """Request to update session fields."""

    conversation_status: ConversationStatus | None = None
    failure_count: int | None = None
    metadata: dict[str, Any] | None = None
