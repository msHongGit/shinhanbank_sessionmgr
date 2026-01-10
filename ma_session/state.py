"""Pydantic models for Master Agent state.

Phase B: Full implementation per PRD Section 15.

All models defined here serve as the single source of truth for state structures.
See docs/03-datamodel-registry.md for change tracking and dependency mapping.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

# ============================================================================
# INPUT MODELS
# ============================================================================


class InputEnvelope(BaseModel):
    """Unified entry point for all inputs (user/agent).

    Phase G1: Comprehensive event_type enumeration covering all Korean business event types.
    See: PRD Section 15.1 & docs/04-enhancement-plan-phase-g.md Section 1.1
    """

    event_source: Literal["User", "Agent"]
    event_channel: str  # utterance, button, component, page, agent
    event_type: Literal[
        "natural_language",  # 자연어/음성 발화
        "component",  # 컴포넌트입력 (button, selector, form)
        "icon_entry",  # 아이콘 진입
        "page_question",  # Sol 페이지 질문 진입
        "sol_error",  # Sol 에러 진입
        "campaign_message",  # 캠페인 문자 진입
        "group_bot_transfer",  # 그룹사 챗봇 전환 진입 / 컴포넌트 경유 전환
        "product_search",  # 상품 검색 페이지 진입
        "agent_response",  # Agent → SubAgent response (internal routing)
    ]
    payload: dict[str, Any]  # Raw input data
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("event_source")
    @classmethod
    def validate_event_source(cls, v: str) -> str:
        """Ensure event_source is valid."""
        if v not in ["User", "Agent"]:
            raise ValueError(f"event_source must be 'User' or 'Agent', got '{v}'")
        return v


# ============================================================================
# SESSION MODELS
# ============================================================================


class SessionSnapshot(BaseModel):
    """Session state provided by AgentGW.

    Master Agent does NOT call Session Manager directly.
    See: PRD Section 15.2
    """

    session_id: str
    user_id: str
    conversation_status: Literal["Start", "Talk", "End"]
    failure_count: int = Field(default=0, ge=0)

    @field_validator("session_id", "user_id")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure IDs are non-empty."""
        if not v or not v.strip():
            raise ValueError("session_id and user_id must be non-empty")
        return v.strip()


# ============================================================================
# TASK MODELS
# ============================================================================


class TaskItem(BaseModel):
    """Individual task representation.

    See: PRD Section 15.3
    Phase H-2: Enriched with skillset metadata for better routing
    """

    task_id: str
    intent: str
    skill_tag: str
    task_text: str | None = None  # Original unit task sentence (for skill search)
    priority: int
    status: Literal["Pending", "Running", "Completed", "Deleted"] = "Pending"

    # Skillset metadata (enriched from skillset agent response)
    skillset_metadata: dict[str, Any] | None = None  # Carries {agent, skill, sub_skill, score, reference_query}

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Ensure task_id is non-empty."""
        if not v or not v.strip():
            raise ValueError("task_id must be non-empty")
        return v.strip()


class TaskQueue(BaseModel):
    """Control plane for task prioritization and coordination.

    See: PRD Section 15.3
    """

    items: list[TaskItem] = Field(default_factory=list)

    @property
    def count(self) -> int:
        """Count non-deleted tasks."""
        return len([t for t in self.items if t.status != "Deleted"])

    def add(self, task: TaskItem) -> None:
        """Add task to queue (in-place modification for testing)."""
        self.items.append(task)

    def pop_top(self) -> TaskItem | None:
        """Remove and return first non-deleted task."""
        for i, task in enumerate(self.items):
            if task.status != "Deleted":
                return self.items.pop(i)
        return None

    def delete_bottom(self) -> None:
        """Mark last non-deleted task as Deleted."""
        for task in reversed(self.items):
            if task.status != "Deleted":
                task.status = "Deleted"
                break

    def sort_by_priority(self) -> None:
        """Sort queue: Running first, then Pending by priority (asc), then Completed/Deleted.

        Phase D-2: Implements priority re-ordering per PRD section 7.4.
        - Running tasks stay at front (active)
        - Pending tasks sorted by priority (1=High, 3=Low)
        - Completed/Deleted tasks moved to back (history)
        """
        running = [t for t in self.items if t.status == "Running"]
        pending = [t for t in self.items if t.status == "Pending"]
        other = [t for t in self.items if t.status in ["Completed", "Deleted"]]

        # Sort pending by priority (ascending: 1 is highest)
        pending.sort(key=lambda t: (t.priority, self.items.index(t)))

        # Recombine
        self.items = running + pending + other


# ============================================================================
# DECISION MODELS
# ============================================================================


class RouteDecision(BaseModel):
    """Output of ROUTE node.

    See: PRD Section 15.4
    """

    route_type: Literal["DirectRouting", "NeedInference", "HandleSubAgent", "Fallback"]
    reason: str


class NudgeAnalysis(BaseModel):
    """Output of ANALYZE_1 node (sentiment/validity).

    See: PRD Section 15.4
    """

    sentiment: Literal["Positive", "Neutral", "Negative"]
    entities: list[str] = Field(default_factory=list)
    valid: bool
    failure_type: Literal["Ambiguous", "OffTopic", "Abusive", "Empty"] | None = None
    chitchat_answer: str | None = None

    @field_validator("failure_type")
    @classmethod
    def validate_failure_type(cls, v: str | None, info: ValidationInfo) -> str | None:
        """Ensure failure_type is None when valid=True."""
        if info.data.get("valid") and v is not None:
            raise ValueError("failure_type must be None when valid=True")
        return v


class PlanAnalysis(BaseModel):
    """Output of ANALYZE_2 node (intent extraction + task planning).

    Phase D: Intent extraction + decomposition (no skill assignment).
    Phase D-2: Prepares tasks for SKILL_SEARCH node.

    See: PRD Section 15.4
    """

    intents: list[str]
    tasks: list[TaskItem]  # skill_tag may be placeholder; filled by SKILL_SEARCH
    task_count: int

    @field_validator("task_count")
    @classmethod
    def validate_task_count(cls, v: int, info: ValidationInfo) -> int:
        """Ensure task_count matches tasks length."""
        tasks = info.data.get("tasks", [])
        if v != len(tasks):
            raise ValueError(f"task_count ({v}) must equal len(tasks) ({len(tasks)})")
        return v


# ============================================================================
# SUB-AGENT MODELS
# ============================================================================


class SubAgentCall(BaseModel):
    """Metadata for sub-agent dispatch.

    See: PRD Section 15.5
    """

    task: TaskItem
    called_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SubAgentResponse(BaseModel):
    """Result from sub-agent execution.

    See: PRD Section 15.5
    """

    task_id: str
    subagent_status: Literal["Undefined", "Continue", "End", "Fallback"]
    result: dict[str, Any] | None = None
    message: str | None = None


# ============================================================================
# OUTPUT MODELS
# ============================================================================


class OutMessage(BaseModel):
    """Final message returned to AgentGW.

    See: PRD Section 15.6
    """

    message_type: Literal["Final", "Cushion", "AskBack", "Fallback"]
    text: str
    metadata: dict[str, Any] | None = None
    routing_info: dict[str, Any] | None = Field(
        default=None, description="Routing details: event_type, event_channel, route_type, target_agent, etc."
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure text is non-empty."""
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        return v


# ============================================================================
# MASTER STATE
# ============================================================================


class AgentState(BaseModel):
    """Single state object passed through all LangGraph nodes.

    Phase G: Added route_count to track recursive agent calls per request.
    Max 3 agent calls per request (when ROUTE node is touched again after initial API request).
    See: PRD Section 15.7 & docs/04-enhancement-plan-phase-g.md Section 3.1
    """

    # Required context
    input: InputEnvelope
    session: SessionSnapshot
    task_queue: TaskQueue

    # Recursion tracking (Phase G)
    route_count: int = Field(default=0, ge=0, le=3)  # Incremented each time ROUTE is visited

    # LLM configuration override
    use_mock_llm: bool = False  # Optional: force use of mock LLM for this request

    # Conversation history for contextual LLM calls
    conversation_history: list[dict[str, Any]] = Field(
        default_factory=list, description="Recent conversation turns for maintaining context in LLM calls"
    )

    # Intent taxonomy for LLM guidance (Phase G2: Token-optimized intent taxonomy)
    reference_taxonomy: list[dict[str, Any]] | None = Field(
        default=None,
        description=(
            "Compact intent taxonomy for LLM prompting; format: [{'agent': 'RAI', 'skill': '금융정보', 'sub_skill': '매크로'}, ...]"
        ),
    )

    # Langfuse tracing (Phase G3: Nested trace support)
    parent_trace_id: str | None = Field(default=None, description="Parent Langfuse trace ID for nesting eval traces under request trace")

    # Decision outputs (populated by nodes)
    route_decision: RouteDecision | None = None
    nudge_analysis: NudgeAnalysis | None = None
    plan_analysis: PlanAnalysis | None = None

    # Execution outputs (populated by nodes)
    subagent_response: SubAgentResponse | None = None

    # Log collection for frontend visibility
    logs: list[dict[str, Any]] = Field(default_factory=list, description="Execution logs for frontend")
    out_message: OutMessage | None = None

    model_config = {"frozen": False}  # Allow in-place updates for task_queue


# ============================================================================
# MOCK MODELS (Phase 1 only)
# ============================================================================


class MockLLMResponse(BaseModel):
    """Phase 1 mock LLM output structure.

    See: PRD Section 15.8
    Deprecated in Phase 2 (replaced by real LLM response parsing).
    """

    raw_text: str
    parsed: dict[str, Any]
