"""Session Manager - Session Service (v5.0 - Async).

세션 관리 핵심 로직 (Async 방식, Redis + MariaDB 사용)
"""

import contextlib
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from app.services.auth_service import AuthService
    from app.services.profile_service import ProfileService

from fastapi import BackgroundTasks, HTTPException

from app.config import GLOBAL_SESSION_PREFIX
from app.core.exceptions import SessionNotFoundError
from app.core.utils import datetime_to_iso, safe_json_dumps, safe_json_parse
from app.db.redis import RedisHelper, get_redis_client
from app.repositories import (
    RedisSessionRepository,
)
from app.schemas.common import (
    AgentType,
    ChannelInfo,
    DialogContext,
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

logger = logging.getLogger(__name__)


class SessionService:
    """세션 관리 서비스 (Async)"""

    def __init__(
        self,
        session_repo=None,
        profile_repo=None,
        auth_service=None,
        profile_service=None,
    ):
        if session_repo is not None:
            # 명시적으로 Repository가 주입된 경우 그대로 사용
            self.session_repo = session_repo
        else:
            # Redis 기반 Repository 사용
            self.session_repo = RedisSessionRepository()

        # Profile Repository는 주입된 값을 그대로 사용 (없으면 None)
        self.profile_repo = profile_repo

        # AuthService와 ProfileService는 주입받거나 생성
        if auth_service is not None:
            self.auth_service = auth_service
        else:
            from app.services.auth_service import AuthService

            self.auth_service = AuthService(self.session_repo)

        if profile_service is not None:
            self.profile_service = profile_service
        else:
            from app.services.profile_service import ProfileService

            self.profile_service = ProfileService(self.session_repo, self.profile_repo)

    # -------------------------------------------------------------------------
    # 내부 유틸리티
    # -------------------------------------------------------------------------

    @staticmethod
    def _serialize_reference_information(ref_info: dict[str, Any]) -> str:
        """reference_information 직렬화 헬퍼.

        - JSON 객체 키를 정렬(sort_keys=True)하여 일관된 저장 형태를 유지한다.
        - 리스트(conversation_history 등)의 순서는 그대로 유지된다.
        """
        result = safe_json_dumps(ref_info, sort_keys=True, ensure_ascii=False)
        return result or "{}"

    @staticmethod
    def _validate_reference_information(ref_info: dict[str, Any]) -> None:
        """reference_information 구조 검증.

        - conversation_history 가 존재하면 반드시 리스트여야 한다.
        - turn_count 가 존재하면 반드시 정수여야 한다.

        MA에서 보낸 값이 조회 단계에서 ValidationError를 일으키지 않도록
        업데이트(PATCH) 시점에 먼저 방어적으로 검증한다.
        """
        conv = ref_info.get("conversation_history")
        if conv is not None and not isinstance(conv, list):
            raise HTTPException(
                status_code=400,
                detail="reference_information.conversation_history must be a list",
            )

        if (
            "turn_count" in ref_info
            and ref_info["turn_count"] is not None
            and not isinstance(
                ref_info["turn_count"],
                int,
            )
        ):
            raise HTTPException(
                status_code=400,
                detail="reference_information.turn_count must be an integer",
            )

    def _generate_id(self, prefix: str) -> str:
        """ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}_{uuid4().hex[:6]}"

    # ============ AGW API ============

    async def create_session(self, request: SessionCreateRequest, background_tasks: BackgroundTasks | None = None) -> SessionCreateResponse:
        """초기 세션 생성 (AGW → SM) - Global Session Key 자동 생성

        세션 생성 흐름:
        1. 세션 객체 생성
        2. Redis 즉시 저장 (세션 스냅샷)
        3. JWT 토큰 발급

        참고: 프로파일은 세션 생성 시점에는 조회하지 않음 (CUSNO 없음)
        - 실시간 프로파일: 실시간 프로파일 저장 API 호출 시 cusnoN10으로 저장
        - 배치 프로파일: 실시간 프로파일 저장 API 호출 시 cusnoN10 값을 CUSNO로 사용하여 MariaDB 조회
        """
        # Session Manager가 Global Session Key 생성
        global_session_key = self._generate_id(GLOBAL_SESSION_PREFIX)

        # 채널 및 세션 진입 유형은 channel 정보에서 파생 (없으면 기본값 사용)
        start_type_value: str | None = None
        if request.channel is not None:
            channel_value = request.channel.event_channel
            start_type_value = request.channel.event_type
        else:
            channel_value = "utterance"

        # user_id가 없으면 빈 문자열로 저장 (선택적 필드)
        user_id = request.user_id or ""

        # JWT 토큰 발급 (AuthService 위임)
        tokens = await self.auth_service.create_tokens(user_id, global_session_key)

        # Redis 즉시 저장 (세션 스냅샷)
        # 프로파일은 세션에 저장하지 않음 (Redis에 별도 저장)
        # 생성한 jti 세션 hash에 함께 저장

        await self.session_repo.create(
            global_session_key=global_session_key,
            user_id=user_id,
            channel=channel_value,
            conversation_id="",
            session_state=SessionState.START.value,
            task_queue_status=TaskQueueStatus.NULL.value,
            subagent_status=SubAgentStatus.UNDEFINED.value,
            # customer_profile=None,
            start_type=start_type_value,
        )

        # 응답 반환 (토큰 포함)
        return SessionCreateResponse(
            global_session_key=global_session_key,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            jti=tokens["jti"],
        )

    # ============ MA API ============

    async def resolve_session(self, request: SessionResolveRequest) -> SessionResolveResponse:
        """세션 조회 (MA → SM)"""
        session = await self.session_repo.get(request.global_session_key)

        if not session:
            raise SessionNotFoundError(request.global_session_key)

        agent_session_key = None
        if request.agent_type == AgentType.TASK and request.agent_id:
            mapping = await self.session_repo.get_local_mapping(
                request.global_session_key,
                request.agent_id,
            )
            if mapping:
                # agent_session_key 사용
                agent_session_key = mapping.get("agent_session_key")

        task_queue_status = TaskQueueStatus(session.get("task_queue_status", "null"))

        last_event = None
        event_data = safe_json_parse(session.get("last_event"))
        if event_data and isinstance(event_data, dict):
            with contextlib.suppress(ValueError, TypeError):
                last_event = LastEvent(**event_data)

        # 멀티턴 reference_information 파싱 (mulititurn.md 옵션 A)
        ref_info = safe_json_parse(session.get("reference_information"))

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

        # 타입이 예상과 다를 경우 조회 단계에서 전체 에러를 내지 않도록 방어적으로 정리
        if conversation_history is not None and not isinstance(conversation_history, list):
            conversation_history = None
        if task_queue_status_detail is not None and not isinstance(task_queue_status_detail, list):
            task_queue_status_detail = None
        if turn_count is not None and not isinstance(turn_count, int):
            turn_count = None

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
        parsed_turn_ids = safe_json_parse(session.get("turn_ids"))
        if isinstance(parsed_turn_ids, list):
            turn_ids = [str(t) for t in parsed_turn_ids]

        # Sub-Agent 표준 스펙과 호환되는 DialogContext 구성은
        # 향후 MA/AGW에서 직접 사용이 확정될 때 활성화한다.
        # 현재는 최소 필드(round-trip 보장용)만 제공하고 dialog_context 는 None 으로 둔다.
        dialog_context: DialogContext | None = None

        # 배치 프로파일과 실시간 프로파일 조회 (ProfileService 위임)
        # 세션에 저장된 cusno로 프로파일 조회
        cusno = session.get("cusno")  # 실시간 프로파일 저장 시 저장된 값

        if cusno:
            # 세션에 cusno가 있으면 해당 cusno로 프로파일 조회
            batch_profile_data, realtime_profile_data = await self.profile_service.get_batch_and_realtime_profiles(cusno)
        else:
            # cusno가 없으면: cusnoN10 없이 저장된 경우일 수 있음
            # global_session_key로 실시간 프로파일 조회 시도 (배치는 조회 불가)
            redis_client = get_redis_client()
            helper = RedisHelper(redis_client)
            realtime_profile_data = await helper.get_realtime_profile(request.global_session_key)
            batch_profile_data = None  # 배치 프로파일은 CUSNO 없이 조회 불가

        return SessionResolveResponse(
            global_session_key=request.global_session_key,
            channel=channel_info,
            agent_session_key=agent_session_key,
            session_state=SessionState(session.get("session_state", "start")),
            is_first_call=session.get("session_state") == "start",
            task_queue_status=task_queue_status,
            subagent_status=SubAgentStatus(session.get("subagent_status", "undefined")),
            last_event=last_event,
            cusno=cusno,
            # customer_profile=None,  # 통합 프로파일 제거
            batch_profile=batch_profile_data,  # 배치 프로파일 (일별+월별)
            realtime_profile=realtime_profile_data,  # 실시간 프로파일
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

    async def patch_session_state(
        self, request: SessionPatchRequest, background_tasks: BackgroundTasks | None = None
    ) -> SessionPatchResponse:
        """세션 상태 업데이트 (MA → SM)

        세션 업데이트 흐름:
        1. 세션 상태 업데이트
        2. Redis 즉시 저장 (세션 스냅샷)
        """
        session = await self.session_repo.get(request.global_session_key)
        if not session:
            raise SessionNotFoundError(request.global_session_key)

        now = datetime.now(UTC)
        updates: dict[str, Any] = {}

        # 세션 상태는 전달된 경우에만 변경
        if request.session_state is not None:
            updates["session_state"] = request.session_state.value

            # Invoke 시(사용자 메시지 전송 시) TTL 연장 (jwd.md 설계: Sliding Expiration on Invoke)
            if request.session_state == SessionState.TALK:
                await self.session_repo.refresh_ttl(request.global_session_key)

        patch = request.state_patch
        if patch is not None:
            if patch.subagent_status:
                updates["subagent_status"] = patch.subagent_status.value
            if patch.action_owner:
                updates["action_owner"] = patch.action_owner

            # reference_information 은 MA가 내려주는 구조를 가급적 그대로 저장하되,
            # current_intent / turn_count 가 state_patch 최상위에 온 경우 함께 병합하여 보관한다.
            if patch.reference_information is not None:
                ref_info: dict[str, Any] = dict(patch.reference_information)
            else:
                ref_info = {}

            if patch.current_intent is not None:
                ref_info["current_intent"] = patch.current_intent
            if patch.turn_count is not None:
                ref_info["turn_count"] = patch.turn_count

            if ref_info:
                # 업데이트 단계에서 구조를 검증하여, 조회 단계에서의 ValidationError를 방지한다.
                self._validate_reference_information(ref_info)
                updates["reference_information"] = self._serialize_reference_information(ref_info)

            if patch.cushion_message:
                updates["cushion_message"] = patch.cushion_message
            if patch.session_attributes:
                session_attrs_str = safe_json_dumps(patch.session_attributes)
                if session_attrs_str:
                    updates["session_attributes"] = session_attrs_str

            if patch.last_agent_id or patch.last_response_type:
                last_event = {
                    "event_type": "AGENT_RESPONSE",
                    "agent_id": patch.last_agent_id,
                    "agent_type": patch.last_agent_type.value if patch.last_agent_type else None,
                    "response_type": patch.last_response_type.value if patch.last_response_type else None,
                    "updated_at": datetime_to_iso(now),
                }
                last_event_str = safe_json_dumps(last_event)
                if last_event_str:
                    updates["last_event"] = last_event_str

            # Agent 세션 매핑 등록 (세션 hash에 저장)
            if patch.agent_session_key and patch.last_agent_id:
                agent_type_value = patch.last_agent_type.value if patch.last_agent_type else AgentType.TASK.value
                await self.session_repo.set_local_mapping(
                    global_session_key=request.global_session_key,
                    agent_id=patch.last_agent_id,
                    agent_session_key=patch.agent_session_key,
                    agent_type=agent_type_value,
                )

        # turn_id는 선택적이지만, 전달된 경우 세션 단위로 누적 관리한다.
        # - 한 세션에 여러 턴이 존재할 수 있으므로 리스트로 저장
        # - 저장 형식: JSON 직렬화된 리스트(str) 또는 리스트 자체를 모두 허용
        if request.turn_id is not None:
            parsed_existing = safe_json_parse(session.get("turn_ids"))
            turn_ids: list[str] = [str(t) for t in parsed_existing] if isinstance(parsed_existing, list) else []

            if request.turn_id not in turn_ids:
                turn_ids.append(request.turn_id)

            turn_ids_str = safe_json_dumps(turn_ids)
            if turn_ids_str:
                updates["turn_ids"] = turn_ids_str

        await self.session_repo.update(request.global_session_key, **updates)

        return SessionPatchResponse(status="success", updated_at=now)

    async def close_session(self, request: SessionCloseRequest, background_tasks: BackgroundTasks | None = None) -> SessionCloseResponse:
        """세션 종료 (MA → SM)

        세션 종료 흐름:
        1. 세션 상태를 END로 변경
        2. Redis 업데이트
        """
        session = await self.session_repo.get(request.global_session_key)
        if not session:
            raise SessionNotFoundError(request.global_session_key)

        now = datetime.now(UTC)

        updates = {
            "session_state": SessionState.END.value,
            "close_reason": request.close_reason,
            "ended_at": datetime_to_iso(now),
        }
        if request.final_summary:
            updates["final_summary"] = request.final_summary

        await self.session_repo.update(request.global_session_key, **updates)

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
    profile_repo = None
    try:
        from app.repositories.mariadb_batch_profile_repository import MariaDBBatchProfileRepository

        profile_repo = MariaDBBatchProfileRepository()
    except Exception as e:
        logger.warning(f"Failed to initialize MariaDBBatchProfileRepository: {e}")
        # MariaDB 연결 실패 시 profile_repo는 None으로 유지
    return SessionService(profile_repo=profile_repo)
