"""
Session Manager - Repository Interfaces
추상 인터페이스 정의 (ABC Pattern)

Note: Sprint 1에서는 핵심 CRUD만 정의.
      추가 메서드는 필요 시 확장.
"""

from abc import ABC, abstractmethod


class SessionRepositoryInterface(ABC):
    """세션 저장소 인터페이스 (최소화)"""

    @abstractmethod
    async def create(self, global_session_key: str, user_id: str, **kwargs) -> dict:
        """세션 생성"""
        pass

    @abstractmethod
    async def get(self, global_session_key: str) -> dict | None:
        """세션 조회"""
        pass

    @abstractmethod
    async def update(self, global_session_key: str, **kwargs) -> dict:
        """세션 업데이트"""
        pass

    @abstractmethod
    async def delete(self, global_session_key: str) -> bool:
        """세션 삭제"""
        pass


class ContextRepositoryInterface(ABC):
    """컨텍스트 저장소 인터페이스 (최소화)"""

    @abstractmethod
    async def create(self, context_id: str, global_session_key: str, user_id: str) -> dict:
        """컨텍스트 생성"""
        pass

    @abstractmethod
    async def get(self, context_id: str) -> dict | None:
        """컨텍스트 조회"""
        pass

    @abstractmethod
    async def add_turn(self, context_id: str, turn_data: dict) -> dict:
        """대화 턴 추가"""
        pass

    @abstractmethod
    async def get_turns(self, context_id: str) -> list[dict]:
        """대화 이력 조회"""
        pass

    @abstractmethod
    async def delete(self, context_id: str) -> int:
        """컨텍스트 삭제"""
        pass


class ProfileRepositoryInterface(ABC):
    """프로파일 저장소 인터페이스 (최소화)"""

    @abstractmethod
    async def get(self, user_id: str) -> list[dict]:
        """프로파일 조회"""
        pass

    @abstractmethod
    async def batch_upsert(self, profiles: list[dict]) -> int:
        """배치 Upsert"""
        pass
