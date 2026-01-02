"""
Session Manager - Session Service (v4.0 - Sync)
세션 관리 핵심 로직 (Sync 방식)
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.config import settings
from app.core.exceptions import SessionNotFoundError
from app.repositories import (
    ContextRepositoryInterface,
    MockContextRepository,
    MockSessionRepository,
    RedisContextRepository,
    RedisSessionRepository,
    SessionRepositoryInterface,
)
from app.schemas import AgentType, CustomerProfile, SessionState, SubAgentStatus, TaskQueueStatus
from app.schemas.agw import SessionCreateRequest, SessionCreateResponse
from app.schemas.ma import (
    LastEvent,
    LocalSessionGetResponse,
    LocalSessionRegisterRequest,
    LocalSessionRegisterResponse,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionResolveRequest,
    SessionResolveResponse,
)
from app.schemas.portal import SessionListItem, SessionListResponse


class SessionService:
    """세션 관리 서비스 (Sync)"""

    def __init__(
        self,
        session_repo: SessionRepositoryInterface | None = None,
        context_repo: ContextRepositoryInterface | None = None,
    ):
        if session_repo is not None and context_repo is not None:
            self.session_repo = session_repo
            self.context_repo = context_repo
            return

        # Sprint 2: 세션/컨텍스트/세션 매핑은 항상 Redis를 사용
        self.session_repo = RedisSessionRepository()
        self.context_repo = RedisContextRepository()

    def _generate_id(self, prefix: str) -> str:
        """ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}_{uuid4().hex[:6]}"

    def _load_customer_profile(self, session: dict) -> CustomerProfile | None:
        """세션 딕셔너리에서 고객 프로파일 스냅샷 복원"""
        raw = session.get("customer_profile")
        if not raw:
            return None

        if isinstance(raw, dict):
            try:
                return CustomerProfile(**raw)
            except Exception:
                return None

        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return CustomerProfile(**data)
            except Exception:
                return None

        return None

    # ============ AGW API ============

    def create_session(self, request: SessionCreateRequest) -> SessionCreateResponse:
        """초기 세션 생성 (AGW → SM) - Global Session Key 자동 생성"""
        # Session Manager가 Global Session Key 생성
        global_session_key = self._generate_id(settings.GLOBAL_SESSION_PREFIX)
        conversation_id = self._generate_id(settings.CONVERSATION_ID_PREFIX)
        context_id = self._generate_id(settings.CONTEXT_ID_PREFIX)
        expires_at = datetime.now(UTC) + timedelta(seconds=settings.SESSION_CACHE_TTL)

        profile_data = request.customer_profile.model_dump() if request.customer_profile else None

        self.session_repo.create(
            global_session_key=global_session_key,
            user_id=request.user_id,
            channel=request.channel,
            conversation_id=conversation_id,
            context_id=context_id,
            session_state=SessionState.START.value,
            task_queue_status=TaskQueueStatus.NULL.value,
            subagent_status=SubAgentStatus.UNDEFINED.value,
            customer_profile=profile_data,
        )

        self.context_repo.create(
            context_id=context_id,
            global_session_key=global_session_key,
            user_id=request.user_id,
        )

        return SessionCreateResponse(
            global_session_key=global_session_key,
            conversation_id=conversation_id,
            context_id=context_id,
            session_state=SessionState.START,
            expires_at=expires_at,
            is_new=True,
            customer_profile=request.customer_profile,
        )

    # ============ MA API ============

    def resolve_session(self, request: SessionResolveRequest) -> SessionResolveResponse:
        """세션 조회 (MA → SM)"""
        session = self.session_repo.get(request.global_session_key)

        if not session:
            raise SessionNotFoundError(request.global_session_key)

        local_session_key = None
        if request.agent_type == AgentType.TASK and request.agent_id:
            mapping = self.session_repo.get_local_mapping(
                request.global_session_key,
                request.agent_id,
            )
            if mapping:
                local_session_key = mapping.get("local_session_key")

        task_queue_status = TaskQueueStatus(session.get("task_queue_status", "null"))

        last_event = None
        if session.get("last_event"):
            try:
                event_data = json.loads(session.get("last_event"))
                last_event = LastEvent(**event_data)
            except (json.JSONDecodeError, ValueError):
                pass

        return SessionResolveResponse(
            global_session_key=request.global_session_key,
            local_session_key=local_session_key,
            conversation_id=session.get("conversation_id", ""),
            context_id=session.get("context_id", ""),
            session_state=SessionState(session.get("session_state", "start")),
            is_first_call=session.get("session_state") == "start",
            task_queue_status=task_queue_status,
            subagent_status=SubAgentStatus(session.get("subagent_status", "undefined")),
            last_event=last_event,
            customer_profile=self._load_customer_profile(session),
        )

    def register_local_session(self, request: LocalSessionRegisterRequest) -> LocalSessionRegisterResponse:
        """Local 세션 등록 (MA → SM)"""
        session = self.session_repo.get(request.global_session_key)
        if not session:
            raise SessionNotFoundError(request.global_session_key)

        expires_at = datetime.now(UTC) + timedelta(seconds=settings.SESSION_MAP_TTL)
        mapping_id = self.session_repo.set_local_mapping(
            global_session_key=request.global_session_key,
            agent_id=request.agent_id,
            local_session_key=request.local_session_key,
            agent_type=request.agent_type.value,
        )

        return LocalSessionRegisterResponse(
            status="success",
            mapping_id=mapping_id,
            expires_at=expires_at,
        )

    def get_local_session(self, global_session_key: str, agent_id: str) -> LocalSessionGetResponse:
        """Local 세션 조회 (MA → SM)"""
        mapping = self.session_repo.get_local_mapping(global_session_key, agent_id)

        if mapping:
            return LocalSessionGetResponse(
                global_session_key=global_session_key,
                local_session_key=mapping.get("local_session_key"),
                agent_id=agent_id,
                agent_type=AgentType(mapping.get("agent_type")) if mapping.get("agent_type") else None,
                is_active=True,
            )

        return LocalSessionGetResponse(
            global_session_key=global_session_key,
            local_session_key=None,
            agent_id=agent_id,
            agent_type=None,
            is_active=False,
        )

    def patch_session_state(self, request: SessionPatchRequest) -> SessionPatchResponse:
        """세션 상태 업데이트 (MA → SM)"""
        session = self.session_repo.get(request.global_session_key)
        if not session:
            raise SessionNotFoundError(request.global_session_key)

        now = datetime.now(UTC)
        updates = {
            "conversation_id": request.conversation_id,
            "session_state": request.session_state.value,
        }

        patch = request.state_patch
        if patch.subagent_status:
            updates["subagent_status"] = patch.subagent_status.value
        if patch.action_owner:
            updates["action_owner"] = patch.action_owner
        if patch.reference_information:
            updates["reference_information"] = json.dumps(patch.reference_information)
        if patch.cushion_message:
            updates["cushion_message"] = patch.cushion_message

        if patch.last_agent_id or patch.last_response_type:
            last_event = {
                "event_type": "AGENT_RESPONSE",
                "agent_id": patch.last_agent_id,
                "agent_type": patch.last_agent_type.value if patch.last_agent_type else None,
                "response_type": patch.last_response_type.value if patch.last_response_type else None,
                "updated_at": now.isoformat(),
            }
            updates["last_event"] = json.dumps(last_event)

        self.session_repo.update(request.global_session_key, **updates)

        return SessionPatchResponse(status="success", updated_at=now)

    def close_session(self, request: SessionCloseRequest) -> SessionCloseResponse:
        """세션 종료 (MA → SM)"""
        session = self.session_repo.get(request.global_session_key)
        if not session:
            raise SessionNotFoundError(request.global_session_key)

        now = datetime.now(UTC)

        updates = {
            "session_state": SessionState.END.value,
            "close_reason": request.close_reason,
            "ended_at": now.isoformat(),
        }
        if request.final_summary:
            updates["final_summary"] = request.final_summary

        self.session_repo.update(request.global_session_key, **updates)

        archived_id = f"arch_{request.conversation_id}"

        return SessionCloseResponse(
            status="success",
            closed_at=now,
            archived_conversation_id=archived_id,
            cleaned_local_sessions=0,
        )

    # ============ Portal API ============

    def list_sessions(
        self,
        page: int = 1,
        page_size: int = 20,
        user_id: str | None = None,
        session_state: SessionState | None = None,
    ) -> SessionListResponse:
        """세션 목록 조회 (Portal → SM, 읽기 전용)"""
        repo = self.session_repo

        if hasattr(repo, "list_all_sessions"):
            all_sessions = repo.list_all_sessions()  # type: ignore[assignment]
        elif hasattr(repo, "_sessions"):
            all_sessions = list(repo._sessions.values())  # type: ignore[attr-defined,assignment]
        else:
            all_sessions = []

        filtered = all_sessions
        if user_id:
            filtered = [s for s in filtered if s.get("user_id") == user_id]
        if session_state:
            filtered = [s for s in filtered if s.get("session_state") == session_state.value]

        filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paged = filtered[start:end]

        items = []
        for s in paged:
            items.append(
                SessionListItem(
                    global_session_key=s.get("global_session_key", ""),
                    user_id=s.get("user_id", ""),
                    channel=s.get("channel", ""),
                    session_state=SessionState(s.get("session_state", "start")),
                    context_id=s.get("context_id", ""),
                    conversation_id=s.get("conversation_id", ""),
                    created_at=datetime.fromisoformat(s.get("created_at", datetime.now(UTC).isoformat())),
                    updated_at=datetime.fromisoformat(s.get("updated_at", datetime.now(UTC).isoformat())),
                    expires_at=datetime.fromisoformat(s["expires_at"]) if s.get("expires_at") else None,
                )
            )

        return SessionListResponse(total=total, page=page, page_size=page_size, items=items)


def get_session_service() -> SessionService:
    """SessionService 인스턴스 반환 (DI)"""
    return SessionService()
