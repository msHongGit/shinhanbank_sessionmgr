"""Session Manager - Redis Session Repository (Async).

Redis 기반 세션 저장소.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import SESSION_CACHE_TTL
from app.db.redis import RedisHelper, get_redis_client


class RedisSessionRepository:
    """Redis 기반 세션 Repository (Async)

    - session:{global_session_key} 형태의 Hash에 세션 정보를 저장
    - Global↔Local 세션 매핑은 세션 hash의 agent_mappings 필드에 저장 (JSON 문자열)
    """

    def __init__(self) -> None:
        client = get_redis_client()
        self.helper = RedisHelper(client)

    async def create(
        self,
        global_session_key: str,
        user_id: str,
        channel: str,
        conversation_id: str,
        session_state: str,
        task_queue_status: str,
        subagent_status: str,
        customer_profile: dict[str, Any] | None = None,
        profile: dict[str, Any] | None = None,
        start_type: str | None = None,
    ) -> dict[str, Any]:
        """세션 생성 (존재 시 기존 세션 반환)"""
        existing = await self.helper.get_session(global_session_key)
        if existing:
            return existing

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=SESSION_CACHE_TTL)

        session: dict[str, Any] = {
            "global_session_key": global_session_key,
            "user_id": user_id,
            "channel": channel,
            "conversation_id": conversation_id,
            "session_state": session_state,
            "task_queue_status": task_queue_status,
            "subagent_status": subagent_status,
            "profile": json.dumps(profile or {}),
            "expires_at": expires_at.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        if start_type is not None:
            # AGW startType 등 세션 진입 유형 메타데이터로 저장
            session["start_type"] = start_type

        if customer_profile is not None:
            # 세션에 개인화 프로파일 스냅샷 저장 (JSON 직렬화)
            session["customer_profile"] = json.dumps(customer_profile)

        await self.helper.set_session(global_session_key, session, ttl=SESSION_CACHE_TTL)

        return session

    async def get(self, global_session_key: str) -> dict[str, Any] | None:
        """세션 조회"""
        return await self.helper.get_session(global_session_key)

    async def update(self, global_session_key: str, **kwargs: Any) -> dict[str, Any]:
        """세션 업데이트 (부분 업데이트)"""
        now = datetime.now(UTC).isoformat()
        updates = {**kwargs, "updated_at": now}
        await self.helper.update_session(global_session_key, updates)
        updated = await self.helper.get_session(global_session_key) or {}
        return updated

    async def delete(self, global_session_key: str) -> bool:
        """세션 삭제"""
        before = await self.helper.get_session(global_session_key)
        await self.helper.delete_session(global_session_key)
        after = await self.helper.get_session(global_session_key)
        return before is not None and after is None

    async def refresh_ttl(self, global_session_key: str) -> dict[str, Any] | None:
        """세션 TTL 연장 및 만료 시각 갱신.

        세션이 존재하면 SESSION_CACHE_TTL 기준으로 expires_at을 다시 설정하고 Redis TTL도 연장한다.
        턴 데이터와 프로파일 데이터의 TTL도 함께 연장한다.
        존재하지 않으면 None을 반환한다.
        """

        session = await self.helper.get_session(global_session_key)
        if not session:
            return None

        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=SESSION_CACHE_TTL)
        session["expires_at"] = expires_at.isoformat()
        await self.helper.set_session(global_session_key, session, ttl=SESSION_CACHE_TTL)

        # 턴 데이터 TTL도 함께 연장
        redis_client = get_redis_client()
        turns_key = f"turns:{global_session_key}"
        if await redis_client.exists(turns_key):
            await redis_client.expire(turns_key, SESSION_CACHE_TTL)

        # 프로파일 데이터 TTL도 함께 연장
        cusno = session.get("cusno")
        if cusno:
            # cusno 기반 프로파일 TTL 연장
            realtime_key = f"profile:realtime:{cusno}"
            batch_key = f"profile:batch:{cusno}"
            if await redis_client.exists(realtime_key):
                await redis_client.expire(realtime_key, SESSION_CACHE_TTL)
            if await redis_client.exists(batch_key):
                await redis_client.expire(batch_key, SESSION_CACHE_TTL)
        else:
            # global_session_key 기반 프로파일 TTL 연장 (cusnoN10 없을 경우)
            realtime_key = f"profile:realtime:{global_session_key}"
            if await redis_client.exists(realtime_key):
                await redis_client.expire(realtime_key, SESSION_CACHE_TTL)

        return session

    # ============ Global↔Local Session Mapping ============

    async def set_local_mapping(self, global_session_key: str, agent_id: str, agent_session_key: str, agent_type: str) -> None:
        """Global↔Local 세션 매핑 등록 (세션 hash에 저장)"""
        # 기존 세션 조회
        session = await self.helper.get_session(global_session_key)
        if not session:
            return

        # 기존 agent_mappings 파싱
        agent_mappings: dict[str, dict[str, str]] = {}
        mappings_str = session.get("agent_mappings")
        if mappings_str:
            try:
                agent_mappings = json.loads(mappings_str)
            except (json.JSONDecodeError, TypeError):
                agent_mappings = {}

        # 새로운 매핑 추가/업데이트
        agent_mappings[agent_id] = {
            "agent_session_key": agent_session_key,
            "agent_type": agent_type,
        }

        # 세션 hash에 저장
        await self.helper.update_session(
            global_session_key,
            {"agent_mappings": json.dumps(agent_mappings)},
        )

    async def get_local_mapping(self, global_session_key: str, agent_id: str) -> dict[str, Any] | None:
        """Local 세션 매핑 조회 (세션 hash에서 조회)"""
        session = await self.helper.get_session(global_session_key)
        if not session:
            return None

        mappings_str = session.get("agent_mappings")
        if not mappings_str:
            return None

        try:
            agent_mappings = json.loads(mappings_str)
            agent_mapping = agent_mappings.get(agent_id)
            if agent_mapping:
                return {
                    "global_session_key": global_session_key,
                    "agent_id": agent_id,
                    "agent_session_key": agent_mapping.get("agent_session_key"),
                    "agent_type": agent_mapping.get("agent_type"),
                }
        except (json.JSONDecodeError, TypeError):
            return None

        return None

    # ============ Turns (대화 턴 이력) ============

    async def add_turn(self, global_session_key: str, turn_data: dict[str, Any]) -> None:
        """대화 턴 추가 (실시간 API 연동 결과 저장)"""
        await self.helper.add_context_turn(global_session_key, turn_data)

    async def get_turns(self, global_session_key: str) -> list[dict[str, Any]]:
        """대화 턴 목록 조회"""
        return await self.helper.get_context_turns(global_session_key)

    async def delete_turns(self, global_session_key: str) -> int:
        """턴 삭제 (삭제된 턴 수 반환)"""
        return await self.helper.delete_context_turns(global_session_key)

    # ============ 조회 유틸 ============

    async def list_all_sessions(self) -> list[dict[str, Any]]:
        """모든 세션 조회 (Portal 목록용)"""
        return await self.helper.get_all_sessions()
