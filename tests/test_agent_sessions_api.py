"""Deprecated Agent Sessions API tests.

이 모듈은 더 이상 사용되지 않는 /agent-sessions API에 대한 테스트를 포함하고 있었으나,
Agent 세션 매핑은 세션 상태 업데이트(PATCH /sessions/{global_session_key}/state)를 통해
처리하도록 변경되었습니다. pytest 수집 시 영향을 주지 않도록 테스트 코드를 제거합니다.
"""


def test_placeholder_noop() -> None:  # pragma: no cover
    """Placeholder to keep module importable without running legacy tests."""
    assert True
