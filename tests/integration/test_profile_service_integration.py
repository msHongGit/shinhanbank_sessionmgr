"""
tests/integration/test_profile_service_integration.py

ProfileService 통합 테스트 - 실제 Redis(Sentinel) + 선택적 MinIO 연동.

단위 테스트와의 차이점:
    - 실제 Redis에 실시간 프로파일 저장/조회
    - profile_repo가 있으면 실제 MinIO에서 배치 프로파일 조회
    - profile_repo=None이면 배치 테스트는 skip
    - cusno 추출 경로(최상위 / responseData)를 실제 Redis 키로 검증
"""

import pytest

pytestmark = pytest.mark.profile


# ---------------------------------------------------------------------------
# IT-PROF-001: update_realtime_personal_context → Redis 실시간 프로파일 저장
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_realtime_profile_saved_with_cusno_key(
    profile_service, session_repo, test_session_key, redis_client
):
    """cusnoN10 있을 때 Redis에 realtime:{cusno} 키로 저장되는지 확인."""
    from app.schemas.common import RealtimePersonalContextRequest

    import unittest.mock as mock

    # 세션 생성
    await session_repo.create(
        global_session_key=test_session_key,
        user_id="IT_PROF_USER",
        channel="SOL",
        conversation_id=f"conv_{test_session_key}",
        session_state="start",
        task_queue_status="null",
        subagent_status="undefined",
    )

    profile_data = {
        "cusnoN10": "99887766",
        "membGdS2": "VIP",
        "acno": "110-123-456789",
    }
    req = RealtimePersonalContextRequest(profile_data=profile_data)

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        result = await profile_service.update_realtime_personal_context(test_session_key, req)

    assert result.status == "success"

    # Redis에서 직접 확인: realtime:99887766
    stored = await redis_client.get("realtime:99887766")
    assert stored is not None, "Redis realtime:99887766 키가 없습니다"

    import json

    parsed = json.loads(stored)
    assert parsed.get("cusnoN10") == "99887766"
    assert parsed.get("membGdS2") == "VIP"

    # 정리
    await redis_client.delete("realtime:99887766")


# ---------------------------------------------------------------------------
# IT-PROF-002: update_realtime_personal_context → session.cusno 업데이트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_cusno_updated_after_realtime_profile(
    profile_service, session_repo, test_session_key, redis_client
):
    """cusnoN10이 있으면 세션 Hash의 cusno 필드가 업데이트되는지 확인."""
    from app.schemas.common import RealtimePersonalContextRequest

    import unittest.mock as mock

    await session_repo.create(
        global_session_key=test_session_key,
        user_id="IT_CUSNO_USER",
        channel="SOL",
        conversation_id=f"conv_{test_session_key}",
        session_state="start",
        task_queue_status="null",
        subagent_status="undefined",
    )

    req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "11223344", "grade": "GOLD"})

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        await profile_service.update_realtime_personal_context(test_session_key, req)

    session_hash = await redis_client.hgetall(f"session:{test_session_key}")
    assert session_hash.get("cusno") == "11223344", (
        f"세션 cusno 업데이트 안 됨: {session_hash.get('cusno')}"
    )

    await redis_client.delete("realtime:11223344")


# ---------------------------------------------------------------------------
# IT-PROF-003: update_realtime_personal_context → responseData 안의 cusnoN10
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cusno_extracted_from_response_data(
    profile_service, session_repo, test_session_key, redis_client
):
    """profile_data.responseData.cusnoN10 경로에서 cusno 추출 확인."""
    from app.schemas.common import RealtimePersonalContextRequest

    import unittest.mock as mock

    await session_repo.create(
        global_session_key=test_session_key,
        user_id="IT_RESP_USER",
        channel="SOL",
        conversation_id=f"conv_{test_session_key}",
        session_state="start",
        task_queue_status="null",
        subagent_status="undefined",
    )

    req = RealtimePersonalContextRequest(
        profile_data={"responseData": {"cusnoN10": "55443322", "grade": "SILVER"}}
    )

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        await profile_service.update_realtime_personal_context(test_session_key, req)

    stored = await redis_client.get("realtime:55443322")
    assert stored is not None
    session_hash = await redis_client.hgetall(f"session:{test_session_key}")
    assert session_hash.get("cusno") == "55443322"

    await redis_client.delete("realtime:55443322")


# ---------------------------------------------------------------------------
# IT-PROF-004: update_realtime_personal_context → cusnoN10 없으면 session_key 기반 저장
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_cusno_uses_session_key(
    profile_service, session_repo, test_session_key, redis_client
):
    """cusnoN10이 없으면 realtime:{test_session_key} 키로 저장."""
    from app.schemas.common import RealtimePersonalContextRequest

    import unittest.mock as mock

    await session_repo.create(
        global_session_key=test_session_key,
        user_id="IT_NOCUSNO_USER",
        channel="SOL",
        conversation_id=f"conv_{test_session_key}",
        session_state="start",
        task_queue_status="null",
        subagent_status="undefined",
    )

    req = RealtimePersonalContextRequest(profile_data={"someField": "someValue"})

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        await profile_service.update_realtime_personal_context(test_session_key, req)

    stored = await redis_client.get(f"realtime:{test_session_key}")
    assert stored is not None, f"Redis realtime:{test_session_key} 키가 없습니다"

    # cusno 필드는 업데이트 안 됨
    session_hash = await redis_client.hgetall(f"session:{test_session_key}")
    assert not session_hash.get("cusno"), "cusno가 없는 상황에서 session.cusno가 설정됨"


# ---------------------------------------------------------------------------
# IT-PROF-005: get_batch_and_realtime_profiles → Redis에서 profile 조회
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_batch_and_realtime_profiles_from_redis(
    profile_service, redis_client
):
    """Redis에 미리 저장한 realtime/batch 프로파일을 올바르게 읽어오는지 확인."""
    import json

    cusno = "IT_GETPROF_001"
    realtime_data = {"cusnoN10": cusno, "grade": "GOLD"}
    batch_data = {
        "daily": {"balance": "1000000"},
        "monthly": {"avgBalance": "900000"},
    }

    # Redis에 직접 저장 (IT 테스트용)
    await redis_client.set(f"realtime:{cusno}", json.dumps(realtime_data))
    await redis_client.set(f"batch:{cusno}", json.dumps(batch_data))

    try:
        batch_result, realtime_result = await profile_service.get_batch_and_realtime_profiles(cusno)

        assert realtime_result is not None
        assert realtime_result.get("cusnoN10") == cusno
        assert batch_result is not None
        assert "daily" in batch_result
    finally:
        await redis_client.delete(f"realtime:{cusno}", f"batch:{cusno}")


# ---------------------------------------------------------------------------
# IT-PROF-006: MinIO 배치 프로파일 조회 (profile_repo 있는 경우만)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_minio_batch_profile_fetch(
    profile_service, profile_repo, session_repo, test_session_key, redis_client
):
    """MinIO에서 배치 프로파일을 실제 조회해 Redis에 저장하는지 확인.
    profile_repo=None이면 자동으로 skip.
    """
    if profile_repo is None:
        pytest.skip("MinIO profile_repo가 설정되지 않아 skip합니다.")

    from app.schemas.common import RealtimePersonalContextRequest

    import unittest.mock as mock

    # 실제 MinIO에 존재하는 cusno 값으로 테스트 (환경 맞게 교체 필요)
    test_cusno = "0616001905"

    await session_repo.create(
        global_session_key=test_session_key,
        user_id=test_cusno,
        channel="SOL",
        conversation_id=f"conv_{test_session_key}",
        session_state="start",
        task_queue_status="null",
        subagent_status="undefined",
    )

    req = RealtimePersonalContextRequest(profile_data={"cusnoN10": test_cusno})

    with mock.patch("app.logger_config.logging.Logger.eslog", return_value=None):
        result = await profile_service.update_realtime_personal_context(test_session_key, req)

    assert result.status == "success"

    # Redis batch:{cusno} 키 확인
    stored_batch = await redis_client.get(f"batch:{test_cusno}")
    assert stored_batch is not None, (
        f"MinIO에서 배치 프로파일을 가져와 Redis batch:{test_cusno}에 저장되지 않았습니다."
    )

    import json

    parsed = json.loads(stored_batch)
    assert "daily" in parsed or "monthly" in parsed, f"배치 데이터 형식 이상: {list(parsed.keys())}"

    # 정리
    await redis_client.delete(f"realtime:{test_cusno}", f"batch:{test_cusno}")
