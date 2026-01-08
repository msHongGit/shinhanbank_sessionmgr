"""
Session Manager - Schemas Package (v3.0)
"""

from app.schemas.agent_sessions import (
    AgentSessionGetResponse,
    AgentSessionRegisterRequest,
    AgentSessionRegisterResponse,
)
from app.schemas.common import (
    AgentType,
    ConversationHistory,
    ConversationHistoryResponse,
    ConversationTurn,
    ConversationTurnSaveRequest,
    ConversationTurnSaveResponse,
    CustomerProfile,
    ErrorResponse,
    FallbackReason,
    LastEvent,
    ProfileAttribute,
    ProfileGetResponse,
    ResponseType,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionResolveRequest,
    SessionResolveResponse,
    SessionState,
    StatePatch,
    SubAgentStatus,
    TaskQueueStatus,
)
from app.schemas.contexts import (
    ContextCreate,
    ContextResponse,
    ContextUpdate,
    TurnCreate,
    TurnCreateWithAPI,
    TurnListResponse,
    TurnResponse,
)

__all__ = [
    # Agent Sessions
    "AgentSessionGetResponse",
    "AgentSessionRegisterRequest",
    "AgentSessionRegisterResponse",
    # Common - Enums
    "AgentType",
    "FallbackReason",
    "ResponseType",
    "SessionState",
    "SubAgentStatus",
    "TaskQueueStatus",
    # Common - Models
    "ConversationHistory",
    "ConversationHistoryResponse",
    "ConversationTurn",
    "ConversationTurnSaveRequest",
    "ConversationTurnSaveResponse",
    "CustomerProfile",
    "ErrorResponse",
    "LastEvent",
    "ProfileAttribute",
    "ProfileGetResponse",
    "SessionCloseRequest",
    "SessionCloseResponse",
    "SessionCreateRequest",
    "SessionCreateResponse",
    "SessionPatchRequest",
    "SessionPatchResponse",
    "SessionResolveRequest",
    "SessionResolveResponse",
    "StatePatch",
    # Contexts (Sprint 3)
    "ContextCreate",
    "ContextResponse",
    "ContextUpdate",
    "TurnCreate",
    "TurnCreateWithAPI",
    "TurnListResponse",
    "TurnResponse",
]
