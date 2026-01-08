"""
Session Manager - MariaDB Context Repository
Sprint 3: Context & Turn 영구 저장소
"""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.mariadb_models import ContextModel, ConversationTurnModel


class MariaDBContextRepository:
    """MariaDB Context Repository (동기)"""

    def __init__(self, db: Session):
        self.db = db

    def create_context(
        self,
        context_id: str,
        global_session_key: str,
    ) -> ContextModel:
        """컨텍스트 생성"""
        context = ContextModel(
            context_id=context_id,
            global_session_key=global_session_key,
            turn_count=0,
            current_slots={},
            entities=[],
            metadata={},
        )
        self.db.add(context)
        self.db.commit()
        self.db.refresh(context)
        return context

    def get_context(self, context_id: str) -> ContextModel | None:
        """컨텍스트 조회"""
        return self.db.query(ContextModel).filter(ContextModel.context_id == context_id).first()

    def update_context(
        self,
        context_id: str,
        current_intent: str | None = None,
        current_slots: dict[str, Any] | None = None,
        entities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ContextModel | None:
        """컨텍스트 업데이트"""
        context = self.get_context(context_id)
        if not context:
            return None

        if current_intent is not None:
            context.current_intent = current_intent
        if current_slots is not None:
            context.current_slots = current_slots
        if entities is not None:
            context.entities = entities
        if metadata is not None:
            context.metadata = metadata

        self.db.commit()
        self.db.refresh(context)
        return context

    def increment_turn_count(self, context_id: str) -> bool:
        """턴 카운트 증가"""
        context = self.get_context(context_id)
        if not context:
            return False

        context.turn_count += 1
        self.db.commit()
        return True

    def create_turn(
        self,
        turn_id: str,
        context_id: str,
        global_session_key: str,
        turn_number: int,
        role: str,
        agent_id: str | None = None,
        agent_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConversationTurnModel:
        """턴 생성 (메타데이터만)"""
        turn = ConversationTurnModel(
            turn_id=turn_id,
            context_id=context_id,
            global_session_key=global_session_key,
            turn_number=turn_number,
            role=role,
            agent_id=agent_id,
            agent_type=agent_type,
            metadata=metadata or {},
        )
        self.db.add(turn)
        self.db.commit()
        self.db.refresh(turn)
        return turn

    def get_turn(self, turn_id: str) -> ConversationTurnModel | None:
        """턴 조회"""
        return self.db.query(ConversationTurnModel).filter(ConversationTurnModel.turn_id == turn_id).first()

    def list_turns(self, context_id: str, limit: int = 100, offset: int = 0) -> list[ConversationTurnModel]:
        """턴 목록 조회"""
        return (
            self.db.query(ConversationTurnModel)
            .filter(ConversationTurnModel.context_id == context_id)
            .order_by(ConversationTurnModel.turn_number.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def count_turns(self, context_id: str) -> int:
        """턴 개수 조회"""
        return self.db.query(ConversationTurnModel).filter(ConversationTurnModel.context_id == context_id).count()
