"""
Session Manager - Context Service (v4.0 - Sync)
대화 이력 관리 (Sync 방식)
"""

from datetime import UTC, datetime

from app.core.exceptions import ContextNotFoundError, SessionNotFoundError
from app.repositories import (
    ContextRepositoryInterface,
    MockContextRepository,
    MockSessionRepository,
    RedisContextRepository,
    RedisSessionRepository,
    SessionRepositoryInterface,
)
from app.schemas.common import ConversationTurn
from app.schemas.ma import (
    ConversationHistoryResponse,
    ConversationTurnSaveRequest,
    ConversationTurnSaveResponse,
)
from app.schemas.portal import ContextDeleteRequest, ContextDeleteResponse, ContextInfoResponse


class ContextService:
    """Context (대화 이력) 관리 서비스 (Sync)"""

    def __init__(
        self,
        context_repo: ContextRepositoryInterface | None = None,
        session_repo: SessionRepositoryInterface | None = None,
    ):
        if context_repo is not None and session_repo is not None:
            self.context_repo = context_repo
            self.session_repo = session_repo
            return

        # Sprint 2: 대화 컨텍스트는 항상 Redis를 사용
        self.context_repo = RedisContextRepository()
        self.session_repo = RedisSessionRepository()

    # ============ MA API ============

    def get_conversation_history(
        self,
        global_session_key: str,
        context_id: str | None = None,
    ) -> ConversationHistoryResponse:
        """대화 이력 조회 (MA → SM)"""
        session = self.session_repo.get(global_session_key)
        if not session:
            raise SessionNotFoundError(global_session_key)

        ctx_id = context_id or session.get("context_id")
        if not ctx_id:
            raise ContextNotFoundError(context_id or "unknown")

        context = self.context_repo.get(ctx_id)
        if not context:
            raise ContextNotFoundError(ctx_id)

        turns_data = self.context_repo.get_turns(ctx_id)
        turns = [ConversationTurn(**t) for t in turns_data]

        return ConversationHistoryResponse(
            context_id=ctx_id,
            global_session_key=global_session_key,
            conversation_id=session.get("conversation_id", ""),
            turns=turns,
            total_turns=len(turns),
        )

    def save_conversation_turn(self, request: ConversationTurnSaveRequest) -> ConversationTurnSaveResponse:
        """대화 턴 저장 (MA → SM)"""
        session = self.session_repo.get(request.global_session_key)
        if not session:
            raise SessionNotFoundError(request.global_session_key)

        context = self.context_repo.get(request.context_id)
        if not context:
            raise ContextNotFoundError(request.context_id)

        turn_data = request.turn.model_dump()
        if isinstance(turn_data.get("timestamp"), datetime):
            turn_data["timestamp"] = turn_data["timestamp"].isoformat()

        self.context_repo.add_turn(request.context_id, turn_data)

        return ConversationTurnSaveResponse(
            status="success",
            turn_id=request.turn.turn_id,
            saved_at=datetime.now(UTC),
        )

    # ============ Portal API ============

    def delete_context(self, request: ContextDeleteRequest) -> ContextDeleteResponse:
        """Context 삭제 (Portal → SM)"""
        context = self.context_repo.get(request.context_id)
        if not context:
            raise ContextNotFoundError(request.context_id)

        deleted_turns = self.context_repo.delete(request.context_id)

        return ContextDeleteResponse(
            status="success",
            context_id=request.context_id,
            deleted_turns=deleted_turns,
            deleted_at=datetime.now(UTC),
        )

    def get_context_info(self, context_id: str) -> ContextInfoResponse:
        """Context 정보 조회 (Portal → SM)"""
        context = self.context_repo.get(context_id)
        if not context:
            raise ContextNotFoundError(context_id)

        turns = self.context_repo.get_turns(context_id)

        return ContextInfoResponse(
            context_id=context_id,
            global_session_key=context.get("global_session_key", ""),
            user_id=context.get("user_id", ""),
            turn_count=len(turns),
            created_at=datetime.fromisoformat(context.get("created_at", datetime.now(UTC).isoformat())),
            updated_at=datetime.fromisoformat(context.get("last_updated_at", context.get("created_at", datetime.now(UTC).isoformat()))),
        )


def get_context_service() -> ContextService:
    """ContextService 인스턴스 반환 (DI)"""
    return ContextService()
