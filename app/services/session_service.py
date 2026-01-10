"""Session Manager - Session Service (v4.0 - Sync).

세션 관리 핵심 로직 (Sync 방식)
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks

from app.config import (
    CONTEXT_ID_PREFIX,
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
    SessionPingResponse,
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
        else:
            # 기본값: 세션/컨텍스트/세션 매핑은 Redis 사용
            self.session_repo = RedisSessionRepository()
            self.context_repo = RedisContextRepository()

        # Profile Repository는 주입된 값을 그대로 사용 (없으면 None)
        self.profile_repo = profile_repo

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
        # Session Manager가 Global Session Key 및 Context ID 생성
        global_session_key = self._generate_id(GLOBAL_SESSION_PREFIX)
        context_id = self._generate_id(CONTEXT_ID_PREFIX)

        # 고객 프로파일 조회 (MariaDB context_db 또는 Mock Repository)
        profile_data = None
        if self.profile_repo:
            customer_profile = self.profile_repo.get_profile(
                user_id=request.user_id,
                context_id=context_id,
                background_tasks=background_tasks,
            )
            if customer_profile:
                # Redis 스냅샷 저장용 raw dict (조회 응답에서 사용)
                profile_data = customer_profile.model_dump()

        # Redis 즉시 저장 (세션 스냅샷)
        self.session_repo.create(
            global_session_key=global_session_key,
            user_id=request.user_id,
            channel="utterance",
            conversation_id="",  # Pass empty string instead of conversation_id
            context_id=context_id,
            session_state=SessionState.START.value,
            task_queue_status=TaskQueueStatus.NULL.value,
            subagent_status=SubAgentStatus.UNDEFINED.value,
            customer_profile=profile_data,
            start_type=request.start_type,
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

        # 외부 응답은 Global 세션 키만 반환 (상세 메타데이터는 조회 API에서 확인)
        return SessionCreateResponse(global_session_key=global_session_key)

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
        updates: dict[str, Any] = {}

        # 세션 상태는 전달된 경우에만 변경
        if request.session_state is not None:
            updates["session_state"] = request.session_state.value

        patch = request.state_patch
        if patch is not None:
            if patch.subagent_status:
                updates["subagent_status"] = patch.subagent_status.value
            if patch.action_owner:
                updates["action_owner"] = patch.action_owner
            if patch.reference_information:
                updates["reference_information"] = json.dumps(patch.reference_information)
            if patch.cushion_message:
                updates["cushion_message"] = patch.cushion_message
            if patch.session_attributes:
                updates["session_attributes"] = json.dumps(patch.session_attributes)

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

    def ping_session(self, global_session_key: str) -> SessionPingResponse:
        """세션 생존 여부 확인 및 TTL 연장.

        세션이 존재하면 TTL을 연장하고, 연장 후 만료 시각을 반환한다.
        세션이 없으면 is_alive=False 와 expires_at=None 을 반환한다.
        """

        # 세션 존재 여부 확인
        session = self.session_repo.get(global_session_key)
        if not session:
            return SessionPingResponse(global_session_key=global_session_key, is_alive=False, expires_at=None)

        # 저장소별 TTL 연장 처리 (Duck typing)
        refreshed = None
        if isinstance(self.session_repo, (RedisSessionRepository, MockSessionRepository)) and hasattr(
            self.session_repo,
            "refresh_ttl",
        ):
            refreshed = self.session_repo.refresh_ttl(global_session_key)

        # refresh_ttl 호출 결과가 없으면 기존 세션 정보 사용
        snapshot = refreshed or self.session_repo.get(global_session_key) or {}
        expires_raw = snapshot.get("expires_at")
        expires_at = None
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None

        return SessionPingResponse(
            global_session_key=global_session_key,
            is_alive=True,
            expires_at=expires_at,
        )

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

        # conversation_id 없이 세션 기준 아카이브 ID 생성
        archived_id = f"arch_{request.global_session_key}"

        return SessionCloseResponse(
            status="success",
            closed_at=now,
            archived_conversation_id=archived_id,
            cleaned_local_sessions=0,
        )


def get_session_service() -> SessionService:
    """SessionService 인스턴스 반환 (DI)"""
    return SessionService()
