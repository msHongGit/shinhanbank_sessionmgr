"""
Session Manager - Session Policy
세션 상태 전이 규칙 및 정책 검증
"""

from app.schemas.common import SessionState


class SessionPolicy:
    """세션 상태 전이 및 정책 검증"""

    # 허용된 상태 전이 맵
    ALLOWED_TRANSITIONS = {
        SessionState.START: [SessionState.TALK],
        SessionState.TALK: [SessionState.TALK, SessionState.END],
        SessionState.END: [],
    }

    @classmethod
    def can_transition(cls, from_state: SessionState, to_state: SessionState) -> bool:
        """
        상태 전이 가능 여부 확인

        Args:
            from_state: 현재 상태
            to_state: 전이하려는 상태

        Returns:
            전이 가능 여부
        """
        allowed = cls.ALLOWED_TRANSITIONS.get(from_state, [])
        return to_state in allowed

    @classmethod
    def validate_transition(cls, from_state: SessionState, to_state: SessionState) -> None:
        """
        상태 전이 검증 (실패 시 예외 발생)

        Args:
            from_state: 현재 상태
            to_state: 전이하려는 상태

        Raises:
            InvalidStateTransitionError: 잘못된 상태 전이인 경우
        """
        if not cls.can_transition(from_state, to_state):
            from app.core.exceptions import InvalidStateTransitionError

            raise InvalidStateTransitionError(
                from_state=from_state.value,
                to_state=to_state.value,
            )
