"""
Session Manager - Session Service
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

from app.config import settings
from app.schemas.session import (
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResolveRequest,
    SessionResolveResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionCloseRequest,
    SessionCloseResponse,
    LastEvent,
)
from app.core.exceptions import SessionNotFoundError


class SessionService:
    """세션 관리 서비스"""
    
    def __init__(self, redis_client: redis.Redis, db_session: AsyncSession):
        self.redis = redis_client
        self.db = db_session
    
    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid4())[:8]
        return f"{settings.SESSION_ID_PREFIX}_{timestamp}_{unique_id}"
    
    def _generate_conversation_id(self, session_id: str) -> str:
        """대화 ID 생성"""
        return f"{settings.CONVERSATION_ID_PREFIX}_{session_id.replace(settings.SESSION_ID_PREFIX, '')}_{str(uuid4())[:4]}"
    
    async def _get_cached_session(self, session_id: str) -> Optional[dict]:
        """Redis에서 세션 조회"""
        data = await self.redis.hgetall(f"session:{session_id}")
        return data if data else None
    
    async def _cache_session(self, session_id: str, data: dict) -> None:
        """Redis에 세션 저장"""
        await self.redis.hset(f"session:{session_id}", mapping=data)
        await self.redis.expire(f"session:{session_id}", settings.SESSION_CACHE_TTL)
    
    async def _delete_cached_session(self, session_id: str) -> None:
        """Redis에서 세션 삭제"""
        await self.redis.delete(f"session:{session_id}")
    
    async def create_session(self, request: SessionCreateRequest) -> SessionCreateResponse:
        """초기 세션 생성"""
        # 1. 기존 세션 확인 (session_key로)
        cache_key = f"session_key:{request.session_key.scope}:{request.session_key.key}"
        existing_session_id = await self.redis.get(cache_key)
        
        if existing_session_id:
            # 기존 세션 반환
            cached = await self._get_cached_session(existing_session_id)
            if cached and datetime.fromisoformat(cached.get("expires_at", "")) > datetime.utcnow():
                return SessionCreateResponse(
                    session_id=existing_session_id,
                    conversation_id=cached.get("conversation_id"),
                    session_state=cached.get("session_state", "start"),
                    expires_at=datetime.fromisoformat(cached.get("expires_at")),
                    policy_profile_ref=cached.get("policy_profile_ref"),
                )
        
        # 2. 새 세션 생성
        session_id = self._generate_session_id()
        conversation_id = self._generate_conversation_id(session_id)
        expires_at = datetime.utcnow() + timedelta(seconds=settings.SESSION_TTL)
        
        session_data = {
            "session_id": session_id,
            "user_id": request.user_id,
            "channel": request.channel,
            "session_key_scope": request.session_key.scope,
            "session_key_value": request.session_key.key,
            "conversation_id": conversation_id,
            "session_state": "start",
            "conversation_status": "start",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "expires_at": expires_at.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # 3. Redis 캐시 저장
        await self._cache_session(session_id, session_data)
        await self.redis.set(cache_key, session_id, ex=settings.SESSION_CACHE_TTL)
        
        # TODO: PostgreSQL에 영속 저장
        
        return SessionCreateResponse(
            session_id=session_id,
            conversation_id=conversation_id,
            session_state="start",
            expires_at=expires_at,
            policy_profile_ref=None,
        )
    
    async def resolve_session(self, request: SessionResolveRequest) -> SessionResolveResponse:
        """세션 조회/생성"""
        # 1. session_key로 session_id 조회
        cache_key = f"session_key:{request.session_key.scope}:{request.session_key.key}"
        session_id = await self.redis.get(cache_key)
        
        is_first_call = False
        
        if not session_id:
            # 새 세션 생성
            is_first_call = True
            create_request = SessionCreateRequest(
                user_id=request.user_id_ref or "unknown",
                channel=request.channel,
                session_key=request.session_key,
                request_id=str(uuid4()),
            )
            created = await self.create_session(create_request)
            session_id = created.session_id
        
        # 2. 세션 상세 정보 조회
        cached = await self._get_cached_session(session_id)
        
        if not cached:
            raise SessionNotFoundError(session_id)
        
        # 3. last_event 파싱
        last_event = None
        last_event_str = cached.get("last_event")
        if last_event_str:
            try:
                last_event_data = json.loads(last_event_str)
                last_event = LastEvent(**last_event_data)
            except (json.JSONDecodeError, ValueError):
                pass
        
        return SessionResolveResponse(
            session_id=session_id,
            conversation_id=cached.get("conversation_id", ""),
            session_state=cached.get("session_state", "start"),
            is_first_call=is_first_call,
            task_queue_status=cached.get("task_queue_status", "null"),
            subagent_status=cached.get("subagent_status", "undefined"),
            last_event=last_event,
            customer_profile_ref=cached.get("customer_profile_ref"),
        )
    
    async def patch_session_state(
        self,
        session_id: str,
        request: SessionPatchRequest,
        background_tasks: BackgroundTasks,
    ) -> SessionPatchResponse:
        """세션 상태 업데이트"""
        # 1. 기존 세션 확인
        cached = await self._get_cached_session(session_id)
        if not cached:
            raise SessionNotFoundError(session_id)
        
        # 2. 상태 업데이트
        update_data = {
            "conversation_id": request.conversation_id,
            "turn_id": request.turn_id,
            "session_state": request.session_state,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # state_patch 적용
        patch = request.state_patch
        if patch.subagent_status:
            update_data["subagent_status"] = patch.subagent_status
        if patch.action_owner:
            update_data["action_owner"] = patch.action_owner
        if patch.reference_information:
            update_data["reference_information"] = json.dumps(patch.reference_information)
        if patch.cushion_message:
            update_data["cushion_message"] = patch.cushion_message
        
        # 3. Redis 업데이트
        await self.redis.hset(f"session:{session_id}", mapping=update_data)
        
        # 4. PostgreSQL 스냅샷 저장 (비동기)
        background_tasks.add_task(self._save_snapshot, session_id, update_data)
        
        return SessionPatchResponse(
            status="success",
            updated_at=datetime.utcnow(),
        )
    
    async def _save_snapshot(self, session_id: str, data: dict) -> None:
        """PostgreSQL에 스냅샷 저장 (비동기)"""
        # TODO: 실제 DB 저장 로직 구현
        print(f"📸 Saving snapshot for session {session_id}")
    
    async def close_session(
        self,
        session_id: str,
        request: SessionCloseRequest,
    ) -> SessionCloseResponse:
        """세션 종료"""
        # 1. 기존 세션 확인
        cached = await self._get_cached_session(session_id)
        if not cached:
            raise SessionNotFoundError(session_id)
        
        # 2. 세션 상태 업데이트
        update_data = {
            "session_state": "end",
            "close_reason": request.close_reason,
            "closed_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if request.final_summary:
            update_data["final_summary"] = request.final_summary
        
        await self.redis.hset(f"session:{session_id}", mapping=update_data)
        
        # 3. Task Queue 정리
        await self.redis.delete(f"task_queue:{session_id}")
        
        # 4. 아카이브 ID 생성
        archived_id = f"arch_{request.conversation_id}"
        
        # TODO: PostgreSQL에 최종 상태 저장
        
        return SessionCloseResponse(
            status="success",
            closed_at=datetime.utcnow(),
            archived_conversation_id=archived_id,
        )
