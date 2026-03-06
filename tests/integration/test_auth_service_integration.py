"""
tests/integration/test_auth_service_integration.py

AuthService 통합 테스트 - 실제 Redis(Sentinel) + 실제 JWT 서명.

단위 테스트와의 차이점:
    - 실제 JWT_SECRET_KEY로 토큰 서명/검증
    - 실제 Redis에 jti:{jti} 키 저장 및 조회
    - 회전(refresh token rotation) 후 실제 키 변경 확인
"""

import pytest

pytestmark = pytest.mark.auth


# ---------------------------------------------------------------------------
# IT-AUTH-001: create_tokens → Redis jti 매핑 실제 저장
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tokens_jti_stored_in_redis(auth_service, test_session_key, redis_client):
    """실제 Redis에 jti:{jti} 키가 저장되는지 확인."""
    result = await auth_service.create_tokens("IT_USER_001", test_session_key)

    jti = result["jti"]
    stored_key = await redis_client.get(f"jti:{jti}")

    assert stored_key == test_session_key, (
        f"Redis jti 매핑 불일치: expected={test_session_key}, got={stored_key}"
    )


# ---------------------------------------------------------------------------
# IT-AUTH-002: create_tokens → jti TTL 확인
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tokens_jti_has_ttl(auth_service, test_session_key, redis_client):
    """jti 키의 TTL이 SESSION_CACHE_TTL 이하로 설정되는지 확인."""
    from app.config import SESSION_CACHE_TTL

    result = await auth_service.create_tokens("IT_USER_TTL", test_session_key)
    jti = result["jti"]

    ttl = await redis_client.ttl(f"jti:{jti}")
    assert 0 < ttl <= SESSION_CACHE_TTL, f"jti TTL 이상: {ttl}"


# ---------------------------------------------------------------------------
# IT-AUTH-003: verify_token_and_get_session → 세션 없으면 is_alive=False
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_token_no_session_is_alive_false(auth_service, test_session_key, redis_client):
    """세션이 Redis에 없을 때 is_alive=False를 반환하는지 확인."""
    tokens = await auth_service.create_tokens("IT_USER_VERIFY", test_session_key)
    access_token = tokens["access_token"]

    # 세션 Hash는 생성하지 않음 (jti 매핑만 존재)
    result = await auth_service.verify_token_and_get_session(access_token)
    assert result.is_alive is False


# ---------------------------------------------------------------------------
# IT-AUTH-004: verify_token_and_get_session → 세션 있으면 is_alive=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_token_with_session_is_alive_true(
    auth_service, session_repo, test_session_key, redis_client
):
    """세션 Hash 생성 후 verify 시 is_alive=True를 반환하는지 확인."""
    tokens = await auth_service.create_tokens("IT_USER_ALIVE", test_session_key)
    access_token = tokens["access_token"]

    # 실제 세션 Hash 생성
    await session_repo.create(
        global_session_key=test_session_key,
        user_id="IT_USER_ALIVE",
        channel="SOL",
        conversation_id=f"conv_{test_session_key}",
        session_state="start",
        task_queue_status="null",
        subagent_status="undefined",
    )

    result = await auth_service.verify_token_and_get_session(access_token)
    assert result.is_alive is True
    assert result.global_session_key == test_session_key


# ---------------------------------------------------------------------------
# IT-AUTH-005: verify_token → 위조 토큰 → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_forged_token_raises_401(auth_service):
    """위조된 토큰으로 verify 시 HTTPException(401)이 발생하는지 확인."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.verify_token_and_get_session("this.is.not.a.valid.jwt")

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# IT-AUTH-006: refresh_token → 신규 jti Redis 저장 / 구 jti 삭제
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_token_rotates_jti_in_redis(
    auth_service, session_repo, test_session_key, redis_client
):
    """refresh_token 호출 후 구 jti는 삭제되고 새 jti가 Redis에 저장되는지 확인."""
    tokens = await auth_service.create_tokens("IT_USER_REFRESH", test_session_key)
    old_jti = tokens["jti"]
    refresh_token = tokens["refresh_token"]

    # 세션 Hash 생성 (refresh_ttl 호출에 필요)
    await session_repo.create(
        global_session_key=test_session_key,
        user_id="IT_USER_REFRESH",
        channel="SOL",
        conversation_id=f"conv_{test_session_key}",
        session_state="start",
        task_queue_status="null",
        subagent_status="undefined",
    )

    new_tokens = await auth_service.refresh_token(refresh_token)
    new_jti = new_tokens.jti

    # 구 jti 삭제 확인
    old_jti_val = await redis_client.get(f"jti:{old_jti}")
    assert old_jti_val is None, f"구 jti가 삭제되지 않음: jti:{old_jti} = {old_jti_val}"

    # 새 jti 저장 확인
    new_jti_val = await redis_client.get(f"jti:{new_jti}")
    assert new_jti_val == test_session_key, (
        f"새 jti 매핑 불일치: expected={test_session_key}, got={new_jti_val}"
    )


# ---------------------------------------------------------------------------
# IT-AUTH-007: access 토큰으로 refresh 요청 → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_with_access_token_raises_401(auth_service, test_session_key):
    """access 토큰으로 refresh_token() 호출 시 HTTPException(401)."""
    from fastapi import HTTPException

    tokens = await auth_service.create_tokens("IT_USER_WRONG_TYPE", test_session_key)
    access_token = tokens["access_token"]

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_token(access_token)

    assert exc_info.value.status_code == 401
