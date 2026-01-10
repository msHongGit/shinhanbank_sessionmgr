"""Deprecated Agent Sessions API tests.

이 모듈은 더 이상 사용되지 않는 /agent-sessions API에 대한 테스트를 포함하고 있었으나,
Agent 세션 매핑은 세션 상태 업데이트(PATCH /sessions/{global_session_key}/state)를 통해
처리하도록 변경되었습니다.

실제 동작을 검증하는 테스트는 모두 Unified Sessions API 테스트로 이전되었기 때문에,
이 파일에는 더 이상 개별 테스트 함수를 두지 않습니다.
"""

# intentionally left without tests
