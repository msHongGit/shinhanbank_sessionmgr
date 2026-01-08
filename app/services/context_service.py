"""
Session Manager - Sprint 3 Context Service
Sprint 3: Context & Turn 관리 서비스 (BackgroundTasks 패턴)
"""

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.repositories.hybrid_context_repository import HybridContextRepository
from app.schemas.contexts import (
    ContextCreate,
    ContextResponse,
    ContextUpdate,
    TurnCreate,
    TurnCreateWithAPI,
    TurnListResponse,
    TurnResponse,
)


class Sprint3ContextService:
    """Sprint 3 Context & Turn 서비스 (BackgroundTasks 패턴)"""

    def __init__(self, db: Session):
        self.repo = HybridContextRepository(db)

    # ========================================================================
    # Context 관리
    # ========================================================================

    def create_context(self, request: ContextCreate, background_tasks: BackgroundTasks) -> ContextResponse:
        """컨텍스트 생성 (Redis 즉시 + MariaDB 백그라운드)"""
        return self.repo.create_context(request, background_tasks)

    def get_context(self, context_id: str) -> ContextResponse:
        """컨텍스트 조회 (Redis 우선, Miss 시 MariaDB)"""
        context = self.repo.get_context(context_id)
        if not context:
            raise ValueError(f"Context not found: {context_id}")
        return context

    def update_context(self, context_id: str, request: ContextUpdate, background_tasks: BackgroundTasks) -> ContextResponse:
        """컨텍스트 업데이트 (Redis 즉시 + MariaDB 백그라운드)"""
        context = self.repo.update_context(context_id, request, background_tasks)
        if not context:
            raise ValueError(f"Context not found: {context_id}")
        return context

    # ========================================================================
    # Turn 관리
    # ========================================================================

    def create_turn(self, request: TurnCreate | TurnCreateWithAPI, background_tasks: BackgroundTasks) -> TurnResponse:
        """
        턴 생성 (메타데이터만, Redis 즉시 + MariaDB 백그라운드)

        - TurnCreate: 일반 대화 턴 메타데이터
        - TurnCreateWithAPI: API 호출 결과 포함
        """
        return self.repo.create_turn(request, background_tasks)

    def get_turn(self, turn_id: str) -> TurnResponse:
        """턴 조회 (Redis 우선, Miss 시 MariaDB)"""
        turn = self.repo.get_turn(turn_id)
        if not turn:
            raise ValueError(f"Turn not found: {turn_id}")
        return turn

    def list_turns(self, context_id: str, limit: int = 100) -> TurnListResponse:
        """턴 목록 조회 (MariaDB에서 직접)"""
        turns = self.repo.list_turns(context_id, limit)
        return TurnListResponse(
            context_id=context_id,
            turns=turns,
            total_count=len(turns),
        )

    # ========================================================================
    # 유틸리티
    # ========================================================================

    def record_api_call(
        self,
        turn_id: str,
        global_session_key: str,
        turn_number: int,
        api_name: str,
        params: dict,
        result: dict,
        status: str = "success",
        duration_ms: int = 0,
        background_tasks: BackgroundTasks | None = None,
    ) -> TurnResponse:
        """
        API 호출 결과 기록 (Redis 즉시 + MariaDB 백그라운드)

        턴 메타데이터에 API 호출 결과를 저장합니다.
        """
        if not background_tasks:
            background_tasks = BackgroundTasks()

        request = TurnCreateWithAPI(
            turn_id=turn_id,
            global_session_key=global_session_key,
            turn_number=turn_number,
            role="system",
            metadata={
                "api_call": {
                    "api_name": api_name,
                    "params": params,
                    "result": result,
                    "status": status,
                    "duration_ms": duration_ms,
                }
            },
        )
        return self.create_turn(request, background_tasks)
