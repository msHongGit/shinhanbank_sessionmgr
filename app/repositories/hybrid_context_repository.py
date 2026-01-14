"""
Session Manager - Hybrid Context Repository
Sprint 3: Redis Cache + MariaDB Persistent Storage
"""

import json
from datetime import datetime
from typing import Any

from fastapi import BackgroundTasks
from redis import Redis
from sqlalchemy.orm import Session

from app.core.utils import datetime_to_iso, iso_to_datetime, safe_json_dumps
from app.db.redis import get_redis_client
from app.repositories.mariadb_context_repository import MariaDBContextRepository
from app.schemas.contexts import (
    ContextCreate,
    ContextResponse,
    ContextUpdate,
    TurnCreate,
    TurnCreateWithAPI,
    TurnResponse,
)


class HybridContextRepository:
    """Hybrid Context Repository (Redis + MariaDB)"""

    def __init__(self, db: Session):
        self.db = db
        self.redis: Redis = get_redis_client()
        self.mariadb_repo = MariaDBContextRepository(db)
        # TTL 상수 (초 단위)
        self.context_ttl: int = 3600  # 1시간
        self.turn_ttl: int = 3600  # 1시간

    # ========================================================================
    # Context 메서드
    # ========================================================================

    def create_context(self, request: ContextCreate, background_tasks: BackgroundTasks) -> ContextResponse:
        """컨텍스트 생성 (Redis 즉시 + MariaDB 백그라운드)"""
        # Redis에 즉시 저장 (응답 속도 보장)
        cache_key = f"context:{request.context_id}"
        now = datetime.now()
        context_data = {
            "context_id": request.context_id,
            "global_session_key": request.global_session_key,
            "current_intent": None,
            "current_slots": {},
            "entities": [],
            "turn_count": 0,
            "metadata": {},
            "created_at": datetime_to_iso(now),
            "updated_at": datetime_to_iso(now),
        }
        json_str = safe_json_dumps(context_data)
        if json_str:
            self.redis.setex(cache_key, self.context_ttl, json_str)

        # MariaDB에 백그라운드 저장
        background_tasks.add_task(
            self.mariadb_repo.create_context,
            context_id=request.context_id,
            global_session_key=request.global_session_key,
        )

        context_data["created_at"] = now
        context_data["updated_at"] = now
        return ContextResponse(**context_data)

    def get_context(self, context_id: str) -> ContextResponse | None:
        """컨텍스트 조회 (Redis 우선, Miss 시 MariaDB)"""
        # Redis 조회
        cache_key = f"context:{context_id}"
        cached = self.redis.get(cache_key)

        if cached:
            data = json.loads(cached)
            # 필드명 통일: last_updated_at → updated_at (하위 호환성 지원)
            if "last_updated_at" in data:
                data["updated_at"] = data.pop("last_updated_at")
            data["created_at"] = iso_to_datetime(data["created_at"]) or datetime.now()
            data["updated_at"] = iso_to_datetime(data["updated_at"]) or datetime.now()
            return ContextResponse(**data)

        # MariaDB 조회
        context_model = self.mariadb_repo.get_context(context_id)
        if not context_model:
            return None

        # Redis에 캐싱
        context_data = {
            "context_id": context_model.context_id,
            "global_session_key": context_model.global_session_key,
            "current_intent": context_model.current_intent,
            "current_slots": context_model.current_slots or {},
            "entities": context_model.entities or [],
            "turn_count": context_model.turn_count,
            "metadata": context_model.metadata or {},
            "created_at": datetime_to_iso(context_model.created_at),
            "updated_at": datetime_to_iso(context_model.updated_at),
        }
        json_str = safe_json_dumps(context_data)
        if json_str:
            self.redis.setex(cache_key, self.context_ttl, json_str)

        context_data["created_at"] = context_model.created_at
        context_data["updated_at"] = context_model.updated_at
        return ContextResponse(**context_data)

    def update_context(self, context_id: str, request: ContextUpdate, background_tasks: BackgroundTasks) -> ContextResponse | None:
        """컨텍스트 업데이트 (Redis 즉시 + MariaDB 백그라운드)"""
        # 기존 컨텍스트 조회 (캐시 또는 DB)
        existing = self.get_context(context_id)
        if not existing:
            return None

        # Redis 즉시 업데이트
        cache_key = f"context:{context_id}"
        now = datetime.now()
        updated_data = {
            "context_id": existing.context_id,
            "global_session_key": existing.global_session_key,
            "current_intent": request.current_intent if request.current_intent is not None else existing.current_intent,
            "current_slots": request.current_slots if request.current_slots is not None else existing.current_slots,
            "entities": request.entities if request.entities is not None else existing.entities,
            "turn_count": existing.turn_count,
            "metadata": request.metadata if request.metadata is not None else existing.metadata,
            "created_at": datetime_to_iso(existing.created_at),
            "updated_at": datetime_to_iso(now),
        }
        json_str = safe_json_dumps(updated_data)
        if json_str:
            self.redis.setex(cache_key, self.context_ttl, json_str)

        # MariaDB 백그라운드 업데이트
        background_tasks.add_task(
            self.mariadb_repo.update_context,
            context_id=context_id,
            current_intent=request.current_intent,
            current_slots=request.current_slots,
            entities=request.entities,
            metadata=request.metadata,
        )

        updated_data["created_at"] = existing.created_at
        updated_data["updated_at"] = now
        return ContextResponse(**updated_data)

    # ========================================================================
    # Turn 메서드
    # ========================================================================

    def create_turn(self, request: TurnCreate | TurnCreateWithAPI, background_tasks: BackgroundTasks) -> TurnResponse:
        """턴 생성 (Redis 즉시 + MariaDB 백그라운드)"""
        # 1. context_id 자동 조회 (없으면 session에서)
        context_id = request.context_id or self._get_context_id_by_session(
            request.global_session_key,
        )

        # 2. turn_number 자동 증가 (없으면 context의 turn_count + 1)
        if request.turn_number is None:
            context = self.get_context(context_id)
            turn_number = (context.turn_count + 1) if context else 1
        else:
            turn_number = request.turn_number

        # 3. turn_id 자동 생성 (없으면 timestamp 기반)
        if request.turn_id:
            turn_id = request.turn_id
        else:
            import uuid

            turn_id = f"turn_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # Redis에 턴 즉시 저장
        now = datetime.now()
        cache_key = f"turn:{turn_id}"
        turn_data = {
            "turn_id": turn_id,
            "context_id": context_id,
            "global_session_key": request.global_session_key,
            "turn_number": turn_number,
            "role": request.role,
            "agent_id": request.agent_id,
            "agent_type": request.agent_type,
            "metadata": request.metadata or {},
            "timestamp": datetime_to_iso(now),
        }
        json_str = safe_json_dumps(turn_data)
        if json_str:
            self.redis.setex(cache_key, self.turn_ttl, json_str)

        # Redis Context 캐시 무효화 (turn_count 변경 예정)
        self.redis.delete(f"context:{context_id}")

        # MariaDB 백그라운드 저장
        background_tasks.add_task(
            self._save_turn_to_mariadb,
            turn_id=turn_id,
            context_id=context_id,
            global_session_key=request.global_session_key,
            turn_number=turn_number,
            role=request.role,
            agent_id=request.agent_id,
            agent_type=request.agent_type,
            metadata=request.metadata,
        )

        turn_data["timestamp"] = now
        return TurnResponse(**turn_data)

    def get_turn(self, turn_id: str) -> TurnResponse | None:
        """턴 조회 (Redis 우선)"""
        # Redis 조회
        cache_key = f"turn:{turn_id}"
        cached = self.redis.get(cache_key)

        if cached:
            data = json.loads(cached)
            timestamp = iso_to_datetime(data.get("timestamp"))
            if timestamp:
                data["timestamp"] = timestamp
            return TurnResponse(**data)

        # MariaDB 조회
        turn_model = self.mariadb_repo.get_turn(turn_id)
        if not turn_model:
            return None

        # Redis에 캐싱
        turn_data = {
            "turn_id": turn_model.turn_id,
            "context_id": turn_model.context_id,
            "global_session_key": turn_model.global_session_key,
            "turn_number": turn_model.turn_number,
            "role": turn_model.role,
            "agent_id": turn_model.agent_id,
            "agent_type": turn_model.agent_type,
            "metadata": turn_model.metadata or {},
            "timestamp": datetime_to_iso(turn_model.timestamp),
        }
        json_str = safe_json_dumps(turn_data)
        if json_str:
            self.redis.setex(cache_key, self.turn_ttl, json_str)

        return TurnResponse(**{**turn_data, "timestamp": turn_model.timestamp})

    def list_turns(self, context_id: str, limit: int = 100) -> list[TurnResponse]:
        """턴 목록 조회 (MariaDB에서 직접)"""
        turns = self.mariadb_repo.list_turns(context_id, limit=limit)
        return [
            TurnResponse(
                turn_id=t.turn_id,
                context_id=t.context_id,
                global_session_key=t.global_session_key,
                turn_number=t.turn_number,
                role=t.role,
                agent_id=t.agent_id,
                agent_type=t.agent_type,
                metadata=t.metadata or {},
                timestamp=t.timestamp,
            )
            for t in turns
        ]

    # ========================================================================
    # 헬퍼 메서드
    # ========================================================================

    def _get_context_id_by_session(self, global_session_key: str) -> str:
        """세션으로부터 context_id 조회"""
        # 실제로는 sessions 테이블에서 조회해야 함
        # 여기서는 간단히 context:{session_key} 형태로 가정
        from app.models.mariadb_models import SessionModel

        session = self.db.query(SessionModel).filter(SessionModel.global_session_key == global_session_key).first()
        if not session:
            raise ValueError(f"Session not found: {global_session_key}")
        return session.context_id

    def _save_turn_to_mariadb(
        self,
        turn_id: str,
        context_id: str,
        global_session_key: str,
        turn_number: int,
        role: str,
        agent_id: str | None,
        agent_type: str | None,
        metadata: dict | None,
    ) -> None:
        """MariaDB에 턴 저장 + turn_count 증가 (백그라운드 작업)"""
        self.mariadb_repo.create_turn(
            turn_id=turn_id,
            context_id=context_id,
            global_session_key=global_session_key,
            turn_number=turn_number,
            role=role,
            agent_id=agent_id,
            agent_type=agent_type,
            metadata=metadata,
        )
        self.mariadb_repo.increment_turn_count(context_id)
