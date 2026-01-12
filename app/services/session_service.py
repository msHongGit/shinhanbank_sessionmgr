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
    USE_MOCK_REDIS,
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
    ChannelInfo,
    CustomerProfile,
    DialogContext,
    DialogTurn,
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
            # 명시적으로 Repository가 주입된 경우 그대로 사용
            self.session_repo = session_repo
            self.context_repo = context_repo
        else:
            # 기본 Repository 선택:
            # - USE_MOCK_REDIS=true 이면 In-Memory Mock Repository 사용 (Redis 불필요)
            # - 그렇지 않으면 Redis 기반 Repository 사용
            if USE_MOCK_REDIS:
                self.session_repo = MockSessionRepository()
                self.context_repo = MockContextRepository()
            else:
                self.session_repo = RedisSessionRepository()
                self.context_repo = RedisContextRepository()

        # Profile Repository는 주입된 값을 그대로 사용 (없으면 None)
        self.profile_repo = profile_repo

    # -------------------------------------------------------------------------
    # 내부 유틸리티
    # -------------------------------------------------------------------------

    @staticmethod
    def _serialize_reference_information(ref_info: dict[str, Any]) -> str:
        """reference_information 직렬화 헬퍼.

        - JSON 객체 키를 정렬(sort_keys=True)하여 일관된 저장 형태를 유지한다.
        - 리스트(conversation_history 등)의 순서는 그대로 유지된다.
        """
        return json.dumps(ref_info, sort_keys=True, ensure_ascii=False)

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

        # 채널 및 세션 진입 유형은 channel 정보에서 파생 (없으면 기본값 사용)
        start_type_value: str | None = None
        if request.channel is not None:
            channel_value = request.channel.event_channel
            start_type_value = request.channel.event_type
        else:
            channel_value = "utterance"

        # Redis 즉시 저장 (세션 스냅샷)
        self.session_repo.create(
            global_session_key=global_session_key,
            user_id=request.user_id,
            channel=channel_value,
            conversation_id="",  # Pass empty string instead of conversation_id
            context_id=context_id,
            session_state=SessionState.START.value,
            task_queue_status=TaskQueueStatus.NULL.value,
            subagent_status=SubAgentStatus.UNDEFINED.value,
            customer_profile=profile_data,
            start_type=start_type_value,
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

        # 멀티턴 reference_information 파싱 (mulititurn.md 옵션 A)
        ref_info_raw = session.get("reference_information")
        ref_info: dict[str, Any] | None = None
        if isinstance(ref_info_raw, str):
            try:
                parsed = json.loads(ref_info_raw)
                if isinstance(parsed, dict):
                    ref_info = parsed
            except json.JSONDecodeError:
                ref_info = None
        elif isinstance(ref_info_raw, dict):
            ref_info = ref_info_raw

        active_task = None
        conversation_history = None
        current_intent = None
        current_task_id = None
        task_queue_status_detail = None
        turn_count = None

        if isinstance(ref_info, dict):
            active_task = ref_info.get("active_task")
            conversation_history = ref_info.get("conversation_history")
            current_intent = ref_info.get("current_intent")
            current_task_id = ref_info.get("current_task_id")
            task_queue_status_detail = ref_info.get("task_queue_status")
            turn_count = ref_info.get("turn_count")

        channel_info: ChannelInfo | None = None
        stored_channel = session.get("channel")
        stored_start_type = session.get("start_type")
        if stored_channel or stored_start_type:
            # 최소한 하나라도 있으면 ChannelInfo 구성 (없으면 빈 문자열 대체)
            channel_info = ChannelInfo(
                event_type=stored_start_type or "",
                event_channel=stored_channel or "",
            )

        # 누적 turn_id 목록 파싱
        turn_ids: list[str] | None = None
        raw_turn_ids = session.get("turn_ids")
        if isinstance(raw_turn_ids, list):
            turn_ids = [str(t) for t in raw_turn_ids]
        elif isinstance(raw_turn_ids, str):
            try:
                parsed_turn_ids = json.loads(raw_turn_ids)
                if isinstance(parsed_turn_ids, list):
                    turn_ids = [str(t) for t in parsed_turn_ids]
            except json.JSONDecodeError:
                turn_ids = None

        # Sub-Agent 표준 스펙과 호환되는 DialogContext 구성
        dialog_context: DialogContext | None = None
        if conversation_history or current_intent or turn_count or turn_ids:
            history_items: list[DialogTurn] = []
            if isinstance(conversation_history, list):
                for item in conversation_history:
                    if not isinstance(item, dict):
                        continue

                    role = (item.get("role") or "user") if isinstance(item.get("role"), str) else "user"
                    content = (item.get("content") or "") if isinstance(item.get("content"), str) else ""

                    # timestamp는 문자열일 경우 ISO8601 파싱 시도, 없거나 실패하면 None
                    ts_value = item.get("timestamp")
                    ts: datetime | None = None
                    if isinstance(ts_value, str):
                        try:
                            ts = datetime.fromisoformat(ts_value)
                        except ValueError:
                            ts = None

                    history_items.append(
                        DialogTurn(
                            role=role,
                            content=content,
                            timestamp=ts,
                            agent_id=item.get("agentId") or item.get("agent_id"),
                        ),
                    )

            effective_turn_count: int | None = turn_count
            if effective_turn_count is None:
                if history_items:
                    effective_turn_count = len(history_items)
                elif turn_ids:
                    effective_turn_count = len(turn_ids)

            current_turn_id = turn_ids[-1] if turn_ids else None

            dialog_context = DialogContext(
                turn_id=current_turn_id,
                turn_count=effective_turn_count,
                history=history_items,
                current_intent=current_intent,
                entities=None,
            )

        return SessionResolveResponse(
            global_session_key=request.global_session_key,
            user_id=session.get("user_id", ""),
            channel=channel_info,
            agent_session_key=agent_session_key,
            session_state=SessionState(session.get("session_state", "start")),
            is_first_call=session.get("session_state") == "start",
            task_queue_status=task_queue_status,
            subagent_status=SubAgentStatus(session.get("subagent_status", "undefined")),
            last_event=last_event,
            customer_profile=self._load_customer_profile(session),
            active_task=active_task,
            conversation_history=conversation_history,
            current_intent=current_intent,
            current_task_id=current_task_id,
            task_queue_status_detail=task_queue_status_detail,
            turn_count=turn_count,
            reference_information=ref_info,
            turn_ids=turn_ids,
            dialog_context=dialog_context,
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
                # reference_information은 JSON으로 직렬화할 때 키를 정렬하여
                # Redis/MariaDB에 일관된 형태로 저장한다.
                updates["reference_information"] = self._serialize_reference_information(patch.reference_information)
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

        # turn_id는 선택적이지만, 전달된 경우 세션 단위로 누적 관리한다.
        # - 한 세션에 여러 턴이 존재할 수 있으므로 리스트로 저장
        # - 저장 형식: JSON 직렬화된 리스트(str) 또는 리스트 자체를 모두 허용
        if request.turn_id is not None:
            turn_ids: list[str] = []

            existing = session.get("turn_ids")
            if isinstance(existing, list):
                turn_ids = [str(t) for t in existing]
            elif isinstance(existing, str):
                try:
                    parsed = json.loads(existing)
                    if isinstance(parsed, list):
                        turn_ids = [str(t) for t in parsed]
                except json.JSONDecodeError:
                    # 형식이 이상하면 새로 시작
                    turn_ids = []

            if request.turn_id not in turn_ids:
                turn_ids.append(request.turn_id)

            updates["turn_ids"] = json.dumps(turn_ids)

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
