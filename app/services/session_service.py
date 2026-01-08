"""Session Manager - Session Service (v4.0 - Sync).

세션 관리 핵심 로직 (Sync 방식)
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import BackgroundTasks

from app.config import (
    CONTEXT_ID_PREFIX,
    CONVERSATION_ID_PREFIX,
    GLOBAL_SESSION_PREFIX,
    LOCAL_SESSION_PREFIX,
    SESSION_CACHE_TTL,
    SESSION_MAP_TTL,
)
from app.core.exceptions import SessionNotFoundError
from app.repositories import (
    ContextRepositoryInterface,
    MockContextRepository,
    MockSessionRepository,
    RedisContextRepository,
    RedisSessionRepository,
    SessionRepositoryInterface,
)
from app.schemas.common import (
    AgentType,
    CustomerProfile,
    LastEvent,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionResolveRequest,
    SessionResolveResponse,
    SessionState,
    SubAgentStatus,
    TaskQueueStatus,
)


class SessionService:
    """세션 관리 서비스 (Sync)"""

    def __init__(
        self,
        session_repo: SessionRepositoryInterface | None = None,
        context_repo: ContextRepositoryInterface | None = None,
        profile_repo=None,
    ):
        if session_repo is not None and context_repo is not None:
            self.session_repo = session_repo
            self.context_repo = context_repo
            self.profile_repo = profile_repo
            return

        # Sprint 2: 세션/컨텍스트/세션 매핑은 항상 Redis를 사용
        self.session_repo = RedisSessionRepository()
        self.context_repo = RedisContextRepository()
        self.profile_repo = None  # Production에서는 HybridProfileRepository 사용

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

    def create_session(self, request: SessionCreateRequest, background_tasks: BackgroundTasks | None = None) -> SessionCreateResponse:
        """초기 세션 생성 (AGW → SM) - Global Session Key 자동 생성

        세션 생성 흐름:
        1. 세션 객체 생성
        2. 고객 프로파일 조회 (MariaDB context_db에서)
        3. Redis 즉시 저장 (세션 스냅샷)
        4. Context 생성
        5. MariaDB 비동기 저장
        """
        # Session Manager가 Global Session Key 생성
        global_session_key = self._generate_id(GLOBAL_SESSION_PREFIX)
        conversation_id = self._generate_id(CONVERSATION_ID_PREFIX)
        context_id = self._generate_id(CONTEXT_ID_PREFIX)
        expires_at = datetime.now(UTC) + timedelta(seconds=SESSION_CACHE_TTL)

        # 고객 프로파일 조회 (MariaDB context_db 또는 Mock Repository)
        customer_profile_response = None
        profile_data = None
        if self.profile_repo:
            customer_profile = self.profile_repo.get_profile(
                user_id=request.user_id,
                context_id=context_id,
                background_tasks=background_tasks,
            )
            if customer_profile:
                # Redis 스냅샷 저장용 raw dict
                profile_data = customer_profile.model_dump()
                # 응답에는 schemas.common.CustomerProfile 그대로 사용
                customer_profile_response = customer_profile

        # Redis 즉시 저장 (세션 스냅샷)
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

        # Context 생성
        self.context_repo.create(
            context_id=context_id,
            global_session_key=global_session_key,
            user_id=request.user_id,
        )

        # TODO: MariaDB 비동기 저장
        # if background_tasks:
        #     background_tasks.add_task(self._save_session_to_mariadb, global_session_key)

        return SessionCreateResponse(
            global_session_key=global_session_key,
            context_id=context_id,
            session_state=SessionState.START,
            expires_at=expires_at,
            is_new=True,
            customer_profile=customer_profile_response,
        )

    # ============ MA API ============

    def resolve_session(self, request: SessionResolveRequest) -> SessionResolveResponse:
        """세션 조회 (MA → SM)"""
        session = self.session_repo.get(request.global_session_key)

        if not session:
            raise SessionNotFoundError(request.global_session_key)

        agent_session_key = None
        if request.agent_type == AgentType.TASK and request.agent_id:
            mapping = self.session_repo.get_local_mapping(
                request.global_session_key,
                request.agent_id,
            )
            if mapping:
                # RedisSessionRepository는 "local_session_key"를, MockSessionRepository는
                # "agent_session_key"를 사용하므로 모두 지원하도록 처리
                agent_session_key = mapping.get("local_session_key") or mapping.get("agent_session_key")

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
            agent_session_key=agent_session_key,
            conversation_id=session.get("conversation_id", ""),
            context_id=session.get("context_id", ""),
            session_state=SessionState(session.get("session_state", "start")),
            is_first_call=session.get("session_state") == "start",
            task_queue_status=task_queue_status,
            subagent_status=SubAgentStatus(session.get("subagent_status", "undefined")),
            last_event=last_event,
            customer_profile=self._load_customer_profile(session),
        )

    def patch_session_state(self, request: SessionPatchRequest, background_tasks: BackgroundTasks | None = None) -> SessionPatchResponse:
        """세션 상태 업데이트 (MA → SM)

        세션 업데이트 흐름:
        1. 세션 상태 업데이트
        2. Redis 즉시 저장 (세션 스냅샷)
        3. MariaDB 비동기 저장
        """
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

        # Agent 세션 매핑 등록 (세션 상태 업데이트 시 함께 처리)
        if patch.agent_session_key and patch.last_agent_id:
            agent_type_value = patch.last_agent_type.value if patch.last_agent_type else AgentType.TASK.value
            self.session_repo.set_local_mapping(
                global_session_key=request.global_session_key,
                agent_id=patch.last_agent_id,
                local_session_key=patch.agent_session_key,
                agent_type=agent_type_value,
            )

        self.session_repo.update(request.global_session_key, **updates)

        # TODO: MariaDB 비동기 저장
        # if background_tasks:
        #     background_tasks.add_task(self._save_session_to_mariadb, request.global_session_key)

        return SessionPatchResponse(status="success", updated_at=now)

    def close_session(self, request: SessionCloseRequest) -> SessionCloseResponse:
        """세션 종료 (MA → SM)

        세션 종료 흐름:
        1. 세션 상태를 END로 변경
        2. Redis 업데이트
        3. MariaDB 최종 상태 저장 (동기)
        """
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

        # TODO: MariaDB 최종 상태 저장 (동기)
        # self._save_session_to_mariadb(request.global_session_key)

        # conversation_id가 요청에 없으면 세션에 저장된 값을 사용
        conversation_id = request.conversation_id or session.get("conversation_id", "")
        archived_id = f"arch_{conversation_id}" if conversation_id else "arch_"

        return SessionCloseResponse(
            status="success",
            closed_at=now,
            archived_conversation_id=archived_id,
            cleaned_local_sessions=0,
        )


def get_session_service() -> SessionService:
    """SessionService 인스턴스 반환 (DI)"""
    return SessionService()
