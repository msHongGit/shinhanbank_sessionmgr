"""
tests/integration/test_session_service_integration.py

SessionService 통합 테스트 - 실제 Redis(Sentinel) 연동.

단위 테스트와의 차이점:
    - Mock 없음: 실제 Redis에 데이터를 쓰고 읽음
    - test_session_key fixture로 테스트마다 고유 키 사용
    - autouse _cleanup_test_keys fixture로 테스트 후 자동 삭제
    - 실제 JWT 발급 → 실제 Redis jti 매핑 → 실제 세션 조회
"""

import json

import pytest
import pytest_asyncio

pytestmark = pytest.mark.session


# ---------------------------------------------------------------------------
# IT-SESS-001: create_session - 정상 생성
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_returns_key_and_tokens(session_service, test_session_key):
    """실제 Redis에 세션 생성 후 global_session_key / token 반환 확인."""
    from app.schemas.common import SessionCreateRequest

    # global_session_key를 제어하기 어려우므로 prefix만 검증
    req = SessionCreateRequest(userId="700000001", triggerId="IT-TRG-001")

    import unittest.mock as mock

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        result = await session_service.create_session(req)

    assert result.global_session_key.startswith("gsess_")
    assert result.access_token
    assert result.refresh_token
    assert result.jti


# ---------------------------------------------------------------------------
# IT-SESS-002: create_session → Redis 실제 저장 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_stored_in_redis(session_service, redis_client):
    """생성된 세션 키가 실제 Redis에 Hash로 저장되는지 확인."""
    from app.schemas.common import SessionCreateRequest

    req = SessionCreateRequest(userId="IT_USER_001")

    import unittest.mock as mock

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        result = await session_service.create_session(req)

    gskey = result.global_session_key
    session_hash = await redis_client.hgetall(f"session:{gskey}")

    assert session_hash, f"Redis에 session:{gskey} 키가 없습니다"
    assert session_hash.get("session_state") == "start"
    assert session_hash.get("user_id") == "IT_USER_001"


# ---------------------------------------------------------------------------
# IT-SESS-003: create_session TTL 설정 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session_has_ttl(session_service, redis_client):
    """생성된 세션 키에 TTL이 설정되어 있는지 확인."""
    from app.schemas.common import SessionCreateRequest

    req = SessionCreateRequest(userId="IT_USER_TTL")

    import unittest.mock as mock

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        result = await session_service.create_session(req)

    ttl = await redis_client.ttl(f"session:{result.global_session_key}")
    # TTL이 0보다 크고 SESSION_CACHE_TTL 이하
    from app.config import SESSION_CACHE_TTL

    assert 0 < ttl <= SESSION_CACHE_TTL, f"TTL 이상: {ttl}"


# ---------------------------------------------------------------------------
# IT-SESS-004: resolve_session - 존재하는 세션 조회
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_session_returns_data(session_service):
    """생성 → 조회 전체 플로우: 실제 Redis에 저장된 데이터를 resolve로 읽어온다."""
    from app.schemas.common import AgentType, SessionCreateRequest, SessionResolveRequest

    import unittest.mock as mock

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        created = await session_service.create_session(
            SessionCreateRequest(userId="IT_RESOLVE_USER")
        )
        resolved = await session_service.resolve_session(
            SessionResolveRequest(
                global_session_key=created.global_session_key,
                agent_type=AgentType.KNOWLEDGE,
            )
        )

    assert resolved.global_session_key == created.global_session_key
    assert resolved.session_state.value == "start"
    assert resolved.is_first_call is True


# ---------------------------------------------------------------------------
# IT-SESS-005: resolve_session - 없는 세션 → SessionNotFoundError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_session_not_found(session_service):
    """존재하지 않는 키로 resolve_session 호출 시 SessionNotFoundError."""
    from app.core.exceptions import SessionNotFoundError
    from app.schemas.common import AgentType, SessionResolveRequest

    with pytest.raises(SessionNotFoundError):
        await session_service.resolve_session(
            SessionResolveRequest(
                global_session_key="gsess_NONEXISTENT_KEY_12345",
                agent_type=AgentType.KNOWLEDGE,
            )
        )


# ---------------------------------------------------------------------------
# IT-SESS-006: patch_session_state → TALK 전환 후 TTL 연장 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_to_talk_refreshes_ttl(session_service, redis_client):
    """TALK 상태로 patch 후 Redis TTL이 갱신되는지 확인."""
    import asyncio

    from app.schemas.common import SessionCreateRequest, SessionPatchRequest, SessionState

    import unittest.mock as mock

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        created = await session_service.create_session(SessionCreateRequest(userId="IT_TTL_USER"))

    # 잠시 대기해 TTL이 줄어드는지 확인 가능하도록
    await asyncio.sleep(1)
    ttl_before = await redis_client.ttl(f"session:{created.global_session_key}")

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        await session_service.patch_session_state(
            SessionPatchRequest(
                global_session_key=created.global_session_key,
                session_state=SessionState.TALK,
            )
        )

    ttl_after = await redis_client.ttl(f"session:{created.global_session_key}")
    assert ttl_after >= ttl_before, "TALK patch 후 TTL이 갱신되지 않았습니다"


# ---------------------------------------------------------------------------
# IT-SESS-007: patch_session_state → turn_id 누적 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_turn_id_accumulated_in_redis(session_service, redis_client):
    """turn_id가 Redis에 JSON 배열로 누적되는지 확인."""
    from app.schemas.common import SessionCreateRequest, SessionPatchRequest

    import unittest.mock as mock

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        created = await session_service.create_session(SessionCreateRequest(userId="IT_TURN_USER"))
        gskey = created.global_session_key

        await session_service.patch_session_state(
            SessionPatchRequest(global_session_key=gskey, turn_id="IT_TURN_001")
        )
        await session_service.patch_session_state(
            SessionPatchRequest(global_session_key=gskey, turn_id="IT_TURN_002")
        )
        # 중복 시도
        await session_service.patch_session_state(
            SessionPatchRequest(global_session_key=gskey, turn_id="IT_TURN_001")
        )

    raw = await redis_client.hget(f"session:{gskey}", "turn_ids")
    turn_ids = json.loads(raw)
    assert "IT_TURN_001" in turn_ids
    assert "IT_TURN_002" in turn_ids
    assert turn_ids.count("IT_TURN_001") == 1, "중복 turn_id가 저장되었습니다"


# ---------------------------------------------------------------------------
# IT-SESS-008: close_session → session_state='end'
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_session_sets_state_end(session_service, redis_client):
    """close_session 후 Redis의 session_state가 'end'로 변경되는지 확인."""
    from app.schemas.common import SessionCloseRequest, SessionCreateRequest

    import unittest.mock as mock

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        created = await session_service.create_session(SessionCreateRequest(userId="IT_CLOSE_USER"))
        gskey = created.global_session_key

        result = await session_service.close_session(
            SessionCloseRequest(
                global_session_key=gskey,
                close_reason="IT_test_close",
                final_summary="통합 테스트 종료",
            )
        )

    assert result.archived_conversation_id == f"arch_{gskey}"

    # Redis에서 직접 확인
    raw = await redis_client.hgetall(f"session:{gskey}")
    assert raw.get("session_state") == "end"
    assert raw.get("close_reason") == "IT_test_close"
    assert raw.get("final_summary") == "통합 테스트 종료"
