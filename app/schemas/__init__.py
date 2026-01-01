"""
Session Manager - Schemas Package (v3.0)
"""

from app.schemas.agw import (
    SessionCreateRequest,
    SessionCreateResponse,
)
from app.schemas.batch import (
    BatchProfileError,
    BatchProfileRecord,
    BatchProfileRequest,
    BatchProfileResponse,
)
from app.schemas.common import (
    AgentType,
    ConversationHistory,
    ConversationTurn,
    CustomerProfile,
    ErrorResponse,
    FallbackReason,
    ProfileAttribute,
    ResponseType,
    SessionState,
    SubAgentStatus,
    TaskQueueStatus,
)
from app.schemas.ma import (
    ConversationHistoryResponse,
    ConversationTurnSaveRequest,
    ConversationTurnSaveResponse,
    LastEvent,
    LocalSessionGetResponse,
    LocalSessionRegisterRequest,
    LocalSessionRegisterResponse,
    ProfileGetResponse,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionResolveRequest,
    SessionResolveResponse,
    StatePatch,
)
from app.schemas.portal import (
    ContextDeleteRequest,
    ContextDeleteResponse,
    ContextInfoResponse,
    SessionListItem,
    SessionListResponse,
)
