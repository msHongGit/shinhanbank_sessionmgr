"""Session Manager - Session Service (v5.0 - Sync).

세션 관리 핵심 로직 (Sync 방식, Redis만 사용)
"""

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException

from app.config import (
    GLOBAL_SESSION_PREFIX,
    SESSION_CACHE_TTL,
    JWT_SECRET_KEY,
)
from app.core.exceptions import SessionNotFoundError
from app.core.utils import datetime_to_iso, safe_json_dumps, safe_json_parse
from app.repositories import (
    RedisSessionRepository,
)

logger = logging.getLogger(__name__)
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
    SessionVerifyResponse,
    SubAgentStatus,
    TaskQueueStatus,
    TokenRefreshRequest,
    TokenRefreshResponse,
)


class SessionService:
    """세션 관리 서비스 (Sync)"""

    def __init__(
        self,
        session_repo=None,
        profile_repo=None,
    ):
        if session_repo is not None:
            # 명시적으로 Repository가 주입된 경우 그대로 사용
            self.session_repo = session_repo
        else:
            # Redis 기반 Repository 사용
            self.session_repo = RedisSessionRepository()

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
            data = safe_json_parse(raw)
            if isinstance(data, dict):
                try:
                    return CustomerProfile(**data)
                except (ValueError, TypeError):
                    return None

        return None

    # ============ AGW API ============

    def create_session(self, request: SessionCreateRequest, background_tasks: BackgroundTasks | None = None) -> SessionCreateResponse:
        """초기 세션 생성 (AGW → SM) - Global Session Key 자동 생성

        세션 생성 흐름:
        1. 세션 객체 생성
        2. 고객 프로파일 조회 (Profile Repository에서)
        3. Redis 즉시 저장 (세션 스냅샷)
        """
        # Session Manager가 Global Session Key 생성
        global_session_key = self._generate_id(GLOBAL_SESSION_PREFIX)

        # 고객 프로파일 조회 (Profile Repository)
        profile_data = None
        if self.profile_repo:
            customer_profile = self.profile_repo.get_profile(
                user_id=request.user_id,
                context_id=None,  # context_id 제거됨
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
            session_state=SessionState.START.value,
            task_queue_status=TaskQueueStatus.NULL.value,
            subagent_status=SubAgentStatus.UNDEFINED.value,
            customer_profile=profile_data,
            start_type=start_type_value,
        )

        # JWT 토큰 발급
        from app.core.jwt import create_access_token, create_refresh_token
        from app.db.redis import get_redis_client
        
        # jti 생성
        jti = str(uuid4())
        
        # Redis에 jti -> global_session_key 매핑 저장
        redis_client = get_redis_client()
        redis_client.setex(f"jti:{jti}", SESSION_CACHE_TTL, global_session_key)
        
        # Access Token 및 Refresh Token 발급
        access_token = create_access_token(jti, request.user_id, JWT_SECRET_KEY)
        refresh_token = create_refresh_token(jti, request.user_id, JWT_SECRET_KEY)

        # 응답 반환 (토큰 포함)
        return SessionCreateResponse(
            global_session_key=global_session_key,
            access_token=access_token,
            refresh_token=refresh_token,
            jti=jti,
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
                # Redis와 Mock 모두 "agent_session_key" 사용
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
                self.session_repo.set_local_mapping(
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

        self.session_repo.update(request.global_session_key, **updates)

        return SessionPatchResponse(status="success", updated_at=now)

    def ping_session(self, global_session_key: str) -> SessionPingResponse:
        """세션 생존 여부 확인 및 TTL 연장.

        세션이 존재하면 TTL을 연장하고, 연장 후 만료 시각을 반환한다.
        세션이 없으면 is_alive=False 와 expires_at=None 을 반환한다.
        
        주의: 이 메서드는 기존 API 호환성을 위해 유지되며, 
        새로운 토큰 기반 API에서는 ping_session_by_token을 사용한다.
        """

        # 세션 존재 여부 확인
        session = self.session_repo.get(global_session_key)
        if not session:
            return SessionPingResponse(is_alive=False, expires_at=None)

        # TTL 연장 처리
        refreshed = None
        if hasattr(self.session_repo, "refresh_ttl"):
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
            is_alive=True,
            expires_at=expires_at,
        )

    def ping_session_by_token(self, token: str) -> SessionPingResponse:
        """토큰 기반 세션 Ping (TTL 연장 없음)
        
        Args:
            token: Access Token 문자열
            
        Returns:
            SessionPingResponse: 세션 생존 여부 및 현재 만료 시각
            
        Raises:
            HTTPException: 토큰이 유효하지 않은 경우 401 반환
        """
        from app.core.jwt_auth import get_global_session_key_from_token
        
        # 1. 토큰에서 global_session_key 조회
        try:
            global_session_key = get_global_session_key_from_token(token)
        except HTTPException as e:
            # 잘못된 토큰에 대해서는 401 반환
            raise e
        
        # 2. 세션 조회
        session = self.session_repo.get(global_session_key)
        if not session:
            return SessionPingResponse(is_alive=False, expires_at=None)
        
        # 3. 만료 시각 반환 (TTL 연장 안 함)
        expires_at = None
        expires_raw = session.get("expires_at")
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None
        
        return SessionPingResponse(is_alive=True, expires_at=expires_at)

    def verify_token_and_get_session(self, token: str) -> SessionVerifyResponse:
        """토큰 검증 및 세션 정보 조회
        
        Args:
            token: Access Token 문자열
            
        Returns:
            SessionVerifyResponse: 세션 정보
        """
        from app.core.jwt import verify_token
        from app.db.redis import get_redis_client
        
        # 1. 토큰 검증
        try:
            payload = verify_token(token, JWT_SECRET_KEY)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        
        # 2. 토큰 타입 확인
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # 3. jti 추출 및 global_session_key 조회
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token: jti not found")
        
        redis_client = get_redis_client()
        global_session_key = redis_client.get(f"jti:{jti}")
        
        if not global_session_key:
            raise HTTPException(status_code=401, detail="Token expired or invalid")
        
        global_session_key = global_session_key if isinstance(global_session_key, str) else global_session_key.decode()
        
        # 4. 세션 조회
        session = self.session_repo.get(global_session_key)
        if not session:
            return SessionVerifyResponse(
                global_session_key=global_session_key,
                user_id=payload.get("sub", ""),
                session_state="",
                is_alive=False,
                expires_at=None,
            )
        
        # 5. 만료 시각 파싱
        expires_at = None
        expires_raw = session.get("expires_at")
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None
        
        return SessionVerifyResponse(
            global_session_key=global_session_key,
            user_id=session.get("user_id", ""),
            session_state=session.get("session_state", ""),
            is_alive=True,
            expires_at=expires_at,
        )

    def refresh_token(self, refresh_token: str) -> TokenRefreshResponse:
        """토큰 갱신
        
        Args:
            refresh_token: Refresh Token 문자열
            
        Returns:
            TokenRefreshResponse: 새 토큰 및 세션 정보
        """
        from app.core.jwt import verify_token, create_access_token, create_refresh_token
        from app.db.redis import get_redis_client
        
        # 1. Refresh Token 검증
        try:
            payload = verify_token(refresh_token, JWT_SECRET_KEY)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
        
        # 2. 토큰 타입 확인
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # 3. jti 추출 및 global_session_key 조회
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token: jti not found")
        
        redis_client = get_redis_client()
        global_session_key = redis_client.get(f"jti:{jti}")
        
        if not global_session_key:
            raise HTTPException(status_code=401, detail="Token expired or invalid")
        
        global_session_key = global_session_key if isinstance(global_session_key, str) else global_session_key.decode()
        
        # 4. 세션 TTL 연장
        self.session_repo.refresh_ttl(global_session_key)
        
        # 5. 새 jti 생성 (Refresh Token Rotation)
        from uuid import uuid4
        new_jti = str(uuid4())
        
        # 6. 새 토큰 발급 (새 jti 사용)
        user_id = payload.get("sub", "")
        new_access_token = create_access_token(new_jti, user_id, JWT_SECRET_KEY)
        new_refresh_token = create_refresh_token(new_jti, user_id, JWT_SECRET_KEY)
        
        # 7. 기존 jti 매핑 삭제 및 새 jti 매핑 저장
        redis_client.delete(f"jti:{jti}")
        redis_client.setex(f"jti:{new_jti}", SESSION_CACHE_TTL, global_session_key)
        
        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            global_session_key=global_session_key,
            jti=new_jti,
        )

    def close_session_by_token(self, token: str, close_reason: str | None = None) -> SessionCloseResponse:
        """토큰 기반 세션 종료
        
        Args:
            token: Access Token 문자열
            close_reason: 종료 사유
            
        Returns:
            SessionCloseResponse: 세션 종료 응답
        """
        from app.core.jwt_auth import get_global_session_key_from_token
        
        # 1. 토큰에서 global_session_key 조회
        global_session_key = get_global_session_key_from_token(token)
        
        # 2. 기존 close_session 로직 사용
        request = SessionCloseRequest(
            global_session_key=global_session_key,
            close_reason=close_reason,
        )
        return self.close_session(request)

    def close_session(self, request: SessionCloseRequest, background_tasks: BackgroundTasks | None = None) -> SessionCloseResponse:
        """세션 종료 (MA → SM)

        세션 종료 흐름:
        1. 세션 상태를 END로 변경
        2. Redis 업데이트
        """
        session = self.session_repo.get(request.global_session_key)
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

        self.session_repo.update(request.global_session_key, **updates)

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
