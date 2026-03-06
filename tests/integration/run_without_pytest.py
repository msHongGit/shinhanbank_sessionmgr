"""
tests/integration/run_without_pytest.py
========================================
pytest 없이 실행하는 Session Manager 완전 테스트 러너.

포함 범위
---------
  [단위 테스트 - Mock 기반, Redis 불필요]
    TC-LOG-001~010  LoggerExtraData 직렬화
    TC-AUTH-001~015 AuthService 토큰 생성/검증/갱신
    TC-PROF-001~014 ProfileService 프로파일 병합/저장
    TC-SESS-001~028 SessionService 세션 생성/조회/패치/종료

  [통합 테스트 - 실제 Redis 필요]
    IT-SESS-001~008 세션 서비스 실 Redis 검증
    IT-AUTH-001~007 인증 서비스 실 Redis 검증
    IT-PROF-001~006 프로파일 서비스 실 Redis 검증

실행 방법
---------
  # 로컬 개발 환경 (uv 가상환경 사용)
  uv run python tests/integration/run_without_pytest.py           # 전체
  uv run python tests/integration/run_without_pytest.py unit      # 단위만
  uv run python tests/integration/run_without_pytest.py auth      # TC-AUTH + IT-AUTH
  uv run python tests/integration/run_without_pytest.py profile   # TC-PROF + IT-PROF
  uv run python tests/integration/run_without_pytest.py session   # TC-SESS + IT-SESS
  uv run python tests/integration/run_without_pytest.py log       # TC-LOG
  uv run python tests/integration/run_without_pytest.py integration  # 통합만

  # K8s Pod 실행 (의존성 이미 설치된 환경)
  kubectl exec <pod> -- python tests/integration/run_without_pytest.py
  kubectl exec <pod> -- python tests/integration/run_without_pytest.py unit
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import unittest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ── 프로젝트 루트를 sys.path 에 추가 (어느 디렉터리에서 실행해도 동작) ──────
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# =============================================================================
# 전역 Redis 상태 (통합 테스트에서 공유, 단위 테스트는 사용 안 함)
# =============================================================================
_REDIS_CLIENT: Any = None
_REDIS_AVAILABLE: bool | None = None  # None=미확인


def _check_redis() -> bool:
    """Redis 연결 가능 여부 확인 (최초 1회만 실행)."""
    global _REDIS_AVAILABLE, _REDIS_CLIENT
    if _REDIS_AVAILABLE is not None:
        return _REDIS_AVAILABLE
    try:
        _REDIS_CLIENT = asyncio.run(_setup_redis())
        _REDIS_AVAILABLE = _REDIS_CLIENT is not None
    except Exception:
        _REDIS_AVAILABLE = False
    return _REDIS_AVAILABLE


async def _setup_redis() -> Any:
    from app.db.redis import get_redis_client, init_redis

    await init_redis()
    client = await get_redis_client()
    # 실제 연결 가능 여부를 PING 으로 검증
    await client.ping()
    return client


async def _cleanup_redis_keys(redis_client: Any) -> None:
    if redis_client is None:
        return
    try:
        keys = await redis_client.keys("inttest_*")
        jti_keys = await redis_client.keys("jti:*")
        all_keys = keys + jti_keys
        if all_keys:
            await redis_client.delete(*all_keys)
    except Exception:
        pass


# =============================================================================
# TC-LOG: LoggerExtraData 직렬화 단위 테스트
# =============================================================================

class TestLoggerExtraData(unittest.TestCase):
    """TC-LOG-001~010: LoggerExtraData 직렬화 검증"""

    def setUp(self):
        from app.logger_config import LoggerExtraData

        self.LoggerExtraData = LoggerExtraData

    def test_TC_LOG_001_default_fields_are_dash(self):
        """TC-LOG-001: 명시하지 않은 필드는 '-' 기본값"""
        msg = self.LoggerExtraData(logType="SESSION_CREATE", payload={})
        self.assertEqual(msg.custNo, "-")
        self.assertEqual(msg.sessionId, "-")
        self.assertEqual(msg.turnId, "-")
        self.assertEqual(msg.agentId, "-")
        self.assertEqual(msg.transactionId, "-")

    def test_TC_LOG_002_explicit_fields_override_defaults(self):
        """TC-LOG-002: 명시한 필드는 기본값을 덮어씀"""
        msg = self.LoggerExtraData(
            logType="SESSION_RESOLVE",
            custNo="123456",
            sessionId="gsess_001",
            turnId="turn_1",
            agentId="agent_1",
            transactionId="txn_1",
            payload={"key": "value"},
        )
        self.assertEqual(msg.custNo, "123456")
        self.assertEqual(msg.sessionId, "gsess_001")
        self.assertEqual(msg.turnId, "turn_1")
        self.assertEqual(msg.agentId, "agent_1")
        self.assertEqual(msg.transactionId, "txn_1")

    def test_TC_LOG_003_logtype_required_raises_validation_error(self):
        """TC-LOG-003: logType 없이 생성 시 ValidationError"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            self.LoggerExtraData(payload={})

    def test_TC_LOG_004_session_create_payload_no_field_info(self):
        """TC-LOG-004: SESSION_CREATE payload 직렬화 시 FieldInfo 없음"""
        msg = self.LoggerExtraData(
            logType="SESSION_CREATE",
            sessionId="gsess_test_001",
            payload={
                "userId": "700000001",
                "channel": "SOL",
                "startType": "ICON_ENTRY",
                "triggerId": "TRG-001",
                "createdAt": "2026-03-01T00:00:00+00:00",
            },
        )
        result = msg.model_dump_json()
        self.assertIn("SESSION_CREATE", result)
        self.assertIn("700000001", result)
        self.assertIn("gsess_test_001", result)

    def test_TC_LOG_005_session_resolve_payload_serializes(self):
        """TC-LOG-005: SESSION_RESOLVE payload 직렬화"""
        msg = self.LoggerExtraData(
            logType="SESSION_RESOLVE",
            custNo="12345678",
            sessionId="gsess_test_002",
            payload={"sessionState": "talk", "agentType": "task", "isFirstCall": False},
        )
        result = msg.model_dump_json()
        self.assertIn("SESSION_RESOLVE", result)
        self.assertIn("12345678", result)
        self.assertIn("talk", result)

    def test_TC_LOG_006_realtime_batch_profile_update_serializes(self):
        """TC-LOG-006: REALTIME_BATCH_PROFILE_UPDATE payload 직렬화"""
        msg = self.LoggerExtraData(
            logType="REALTIME_BATCH_PROFILE_UPDATE",
            custNo="99999999",
            sessionId="gsess_test_003",
            payload={"hasCusno": True, "savedRealtimeKey": "99999999", "batchProfileFetched": True},
        )
        result = msg.model_dump_json()
        self.assertIn("REALTIME_BATCH_PROFILE_UPDATE", result)
        self.assertIn("99999999", result)

    def test_TC_LOG_007_session_state_update_serializes(self):
        """TC-LOG-007: SESSION_STATE_UPDATE payload 직렬화"""
        msg = self.LoggerExtraData(
            logType="SESSION_STATE_UPDATE",
            sessionId="gsess_test_004",
            turnId="turn_001",
            agentId="agent_001",
            payload={"newSessionState": "talk", "hasStatePatch": True},
        )
        result = msg.model_dump_json()
        self.assertIn("SESSION_STATE_UPDATE", result)
        self.assertIn("talk", result)

    def test_TC_LOG_008_session_close_serializes(self):
        """TC-LOG-008: SESSION_CLOSE payload 직렬화"""
        msg = self.LoggerExtraData(
            logType="SESSION_CLOSE",
            custNo="11111111",
            sessionId="gsess_test_005",
            payload={"sessionState": "end", "closedAt": "2026-03-01T00:00:00+00:00"},
        )
        result = msg.model_dump_json()
        self.assertIn("SESSION_CLOSE", result)
        self.assertIn("end", result)

    def test_TC_LOG_009_empty_payload_serializes(self):
        """TC-LOG-009: 빈 payload dict 직렬화"""
        msg = self.LoggerExtraData(logType="TEST", payload={})
        result = msg.model_dump_json()
        self.assertIn("TEST", result)
        self.assertIn("{}", result)

    def test_TC_LOG_010_none_payload_serializes(self):
        """TC-LOG-010: None payload 직렬화"""
        msg = self.LoggerExtraData(logType="TEST", payload=None)
        result = msg.model_dump_json()
        self.assertIn("TEST", result)


# =============================================================================
# TC-AUTH: AuthService 단위 테스트
# =============================================================================

def _make_auth_service(session_data=None):
    from app.services.auth_service import AuthService

    session_repo = MagicMock()
    session_repo.get = AsyncMock(return_value=session_data)
    session_repo.refresh_ttl = AsyncMock()
    return AuthService(session_repo=session_repo)


class TestAuthCreateTokens(unittest.IsolatedAsyncioTestCase):
    """TC-AUTH-001~004: create_tokens 검증"""

    async def test_TC_AUTH_001_returns_access_refresh_jti(self):
        """TC-AUTH-001: 정상 입력 -> access_token, refresh_token, jti 반환"""
        svc = _make_auth_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()
        with (
            patch("app.services.auth_service.get_redis_client", return_value=mock_redis),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.create_tokens("700000001", "gsess_test_001")
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)
        self.assertIn("jti", result)

    async def test_TC_AUTH_002_jti_is_uuid_format(self):
        """TC-AUTH-002: jti 가 UUID 형식"""
        import re

        svc = _make_auth_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()
        with (
            patch("app.services.auth_service.get_redis_client", return_value=mock_redis),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.create_tokens("user", "gsess_test")
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        self.assertRegex(result["jti"], uuid_pattern)

    async def test_TC_AUTH_003_jti_mapping_saved_to_redis(self):
        """TC-AUTH-003: Redis 에 jti -> global_session_key 매핑 저장"""
        svc = _make_auth_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()
        with (
            patch("app.services.auth_service.get_redis_client", return_value=mock_redis),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            await svc.create_tokens("user", "gsess_test_key")
        mock_helper.set_jti_mapping.assert_called_once()
        self.assertEqual(mock_helper.set_jti_mapping.call_args[0][1], "gsess_test_key")

    async def test_TC_AUTH_004_empty_user_id_allowed(self):
        """TC-AUTH-004: user_id 빈 문자열 허용"""
        svc = _make_auth_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()
        with (
            patch("app.services.auth_service.get_redis_client", return_value=mock_redis),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.create_tokens("", "gsess_empty_user")
        self.assertIn("access_token", result)


class TestAuthVerifyToken(unittest.IsolatedAsyncioTestCase):
    """TC-AUTH-005~009: verify_token_and_get_session 검증"""

    async def test_TC_AUTH_005_invalid_token_raises_401(self):
        """TC-AUTH-005: 위조/만료 토큰 -> 401"""
        from fastapi import HTTPException

        svc = _make_auth_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.verify_token_and_get_session("invalid_token_string")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_TC_AUTH_006_refresh_token_type_raises_401(self):
        """TC-AUTH-006: type != 'access' (refresh 토큰) -> 401"""
        from fastapi import HTTPException

        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_refresh_token

        refresh_token = create_refresh_token("test_jti", "user_id", JWT_SECRET_KEY)
        svc = _make_auth_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.verify_token_and_get_session(refresh_token)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_TC_AUTH_007_jti_not_in_redis_raises_401(self):
        """TC-AUTH-007: jti Redis 매핑 없음 -> 401"""
        from fastapi import HTTPException

        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("no_jti_in_redis", "user_id", JWT_SECRET_KEY)
        svc = _make_auth_service()
        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value=None)
        with (
            patch("app.services.auth_service.get_redis_client"),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await svc.verify_token_and_get_session(access_token)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_TC_AUTH_008_session_not_found_is_alive_false(self):
        """TC-AUTH-008: 세션 없음 -> is_alive=False"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("test_jti", "user_id", JWT_SECRET_KEY)
        svc = _make_auth_service(session_data=None)
        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_test")
        with (
            patch("app.services.auth_service.get_redis_client"),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.verify_token_and_get_session(access_token)
        self.assertFalse(result.is_alive)

    async def test_TC_AUTH_009_session_found_is_alive_true(self):
        """TC-AUTH-009: 세션 있음 -> is_alive=True"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("test_jti_2", "user_id", JWT_SECRET_KEY)
        svc = _make_auth_service(session_data={"session_state": "talk", "user_id": "user_id"})
        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_test")
        mock_helper.get_ttl = AsyncMock(return_value=300)
        with (
            patch("app.services.auth_service.get_redis_client"),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.verify_token_and_get_session(access_token)
        self.assertTrue(result.is_alive)


class TestAuthRefreshToken(unittest.IsolatedAsyncioTestCase):
    """TC-AUTH-012~015: refresh_token 검증"""

    async def test_TC_AUTH_012_invalid_refresh_raises_401(self):
        """TC-AUTH-012: 위조 refresh 토큰 -> 401"""
        from fastapi import HTTPException

        svc = _make_auth_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.refresh_token("invalid_refresh_token")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_TC_AUTH_013_access_token_as_refresh_raises_401(self):
        """TC-AUTH-013: access 토큰으로 refresh 요청 -> 401"""
        from fastapi import HTTPException

        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("jti_x", "user", JWT_SECRET_KEY)
        svc = _make_auth_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.refresh_token(access_token)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_TC_AUTH_014_valid_refresh_returns_new_tokens(self):
        """TC-AUTH-014: 정상 refresh -> 새 access_token, refresh_token, jti 반환"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_refresh_token

        old_jti = "old_jti_value"
        refresh_token = create_refresh_token(old_jti, "user_id", JWT_SECRET_KEY)
        svc = _make_auth_service(session_data={"session_state": "talk"})
        mock_redis = MagicMock()
        mock_redis.delete = AsyncMock()
        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_key")
        mock_helper.delete_jti_mapping = AsyncMock()
        mock_helper.set_jti_mapping = AsyncMock()
        with (
            patch("app.services.auth_service.get_redis_client", return_value=mock_redis),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.refresh_token(refresh_token)
        self.assertTrue(result.access_token)
        self.assertTrue(result.refresh_token)
        self.assertNotEqual(result.jti, old_jti)

    async def test_TC_AUTH_015_refresh_calls_refresh_ttl(self):
        """TC-AUTH-015: refresh 성공 시 session_repo.refresh_ttl 호출"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_refresh_token

        refresh_token = create_refresh_token("jti_refresh", "user_id", JWT_SECRET_KEY)
        svc = _make_auth_service(session_data={"session_state": "talk"})
        mock_redis = MagicMock()
        mock_redis.delete = AsyncMock()
        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_key")
        mock_helper.delete_jti_mapping = AsyncMock()
        mock_helper.set_jti_mapping = AsyncMock()
        with (
            patch("app.services.auth_service.get_redis_client", return_value=mock_redis),
            patch("app.services.auth_service.RedisHelper", return_value=mock_helper),
        ):
            await svc.refresh_token(refresh_token)
        svc.session_repo.refresh_ttl.assert_called_once_with("gsess_key")


# =============================================================================
# TC-PROF: ProfileService 단위 테스트
# =============================================================================

def _make_profile_service(session_data=None, profile_repo=None):
    from app.services.profile_service import ProfileService

    session_repo = MagicMock()
    session_repo.get = AsyncMock(return_value=session_data)
    session_repo.update = AsyncMock()
    return ProfileService(session_repo=session_repo, profile_repo=profile_repo)


class TestProfileMerge(unittest.TestCase):
    """TC-PROF-001~007: _merge_profiles 정적 메서드 검증"""

    def setUp(self):
        from app.services.profile_service import ProfileService

        self.PS = ProfileService

    def test_TC_PROF_001_both_none_returns_none(self):
        """TC-PROF-001: batch/realtime 모두 None -> None 반환"""
        self.assertIsNone(self.PS._merge_profiles(None, None))

    def test_TC_PROF_002_realtime_takes_priority(self):
        """TC-PROF-002: realtime 있으면 실시간 프로파일 우선"""
        result = self.PS._merge_profiles(None, {"cusnoN10": "12345", "membGdS2": "VIP"})
        self.assertIsNotNone(result)
        self.assertEqual(result.user_id, "12345")

    def test_TC_PROF_003_realtime_membgds2_sets_segment(self):
        """TC-PROF-003: realtime 에 membGdS2 있으면 segment 설정"""
        result = self.PS._merge_profiles(None, {"cusnoN10": "12345", "membGdS2": "VIP"})
        self.assertEqual(result.segment, "VIP")

    def test_TC_PROF_004_empty_values_excluded_from_attributes(self):
        """TC-PROF-004: realtime 빈 값('', None) -> attributes 에서 제외"""
        realtime = {
            "cusnoN10": "12345",
            "emptyField": "",
            "noneField": None,
            "validField": "abc",
        }
        result = self.PS._merge_profiles(None, realtime)
        keys = [attr.key for attr in result.attributes]
        self.assertNotIn("emptyField", keys)
        self.assertNotIn("noneField", keys)
        self.assertIn("validField", keys)

    def test_TC_PROF_005_batch_only_when_no_realtime(self):
        """TC-PROF-005: realtime 없으면 batch 반환"""
        from app.schemas.common import CustomerProfile

        batch = CustomerProfile(user_id="batch_user", attributes=[], segment=None, preferences={})
        result = self.PS._merge_profiles(batch, None)
        self.assertEqual(result.user_id, "batch_user")

    def test_TC_PROF_006_realtime_source_is_realtime(self):
        """TC-PROF-006: realtime 프로파일 source 는 'realtime'"""
        result = self.PS._merge_profiles(None, {"cusnoN10": "12345", "someField": "val"})
        self.assertEqual(result.preferences.get("source"), "realtime")

    def test_TC_PROF_007_no_cusno_falls_back_to_batch_user_id(self):
        """TC-PROF-007: realtime 에 cusnoN10 없으면 batch.user_id 사용"""
        from app.schemas.common import CustomerProfile

        batch = CustomerProfile(user_id="fallback_user", attributes=[], segment=None, preferences={})
        result = self.PS._merge_profiles(batch, {"someField": "val"})
        self.assertEqual(result.user_id, "fallback_user")


class TestProfileUpdateRealtime(unittest.IsolatedAsyncioTestCase):
    """TC-PROF-008~014: update_realtime_personal_context 검증"""

    async def test_TC_PROF_008_session_not_found_raises(self):
        """TC-PROF-008: 세션 없으면 SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import RealtimePersonalContextRequest

        svc = _make_profile_service(session_data=None)
        req = RealtimePersonalContextRequest(profile_data={"someField": "val"})
        with self.assertRaises(SessionNotFoundError):
            with patch("app.services.profile_service.get_redis_client"):
                await svc.update_realtime_personal_context("gsess_missing", req)

    async def test_TC_PROF_009_cusno_from_toplevel(self):
        """TC-PROF-009: profile_data 최상위 cusnoN10 에서 cusno 추출"""
        from app.schemas.common import RealtimePersonalContextRequest

        svc = _make_profile_service(session_data={"session_state": "start"})
        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "11111111"})
        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()
        with (
            patch("app.services.profile_service.get_redis_client"),
            patch("app.services.profile_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.update_realtime_personal_context("gsess_test", req)
        self.assertEqual(result.status, "success")
        mock_helper.set_realtime_profile.assert_called_once_with("11111111", req.profile_data)

    async def test_TC_PROF_010_cusno_from_response_data(self):
        """TC-PROF-010: profile_data.responseData 안의 cusnoN10 추출"""
        from app.schemas.common import RealtimePersonalContextRequest

        svc = _make_profile_service(session_data={"session_state": "start"})
        req = RealtimePersonalContextRequest(profile_data={"responseData": {"cusnoN10": "22222222"}})
        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        with (
            patch("app.services.profile_service.get_redis_client"),
            patch("app.services.profile_service.RedisHelper", return_value=mock_helper),
        ):
            await svc.update_realtime_personal_context("gsess_test", req)
        mock_helper.set_realtime_profile.assert_called_once_with("22222222", req.profile_data)

    async def test_TC_PROF_011_no_cusno_uses_session_key(self):
        """TC-PROF-011: cusnoN10 없으면 global_session_key 로 저장"""
        from app.schemas.common import RealtimePersonalContextRequest

        svc = _make_profile_service(session_data={"session_state": "start"})
        req = RealtimePersonalContextRequest(profile_data={"someField": "val"})
        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        with (
            patch("app.services.profile_service.get_redis_client"),
            patch("app.services.profile_service.RedisHelper", return_value=mock_helper),
        ):
            await svc.update_realtime_personal_context("gsess_test", req)
        mock_helper.set_realtime_profile.assert_called_once_with("gsess_test", req.profile_data)

    async def test_TC_PROF_012_with_profile_repo_saves_batch(self):
        """TC-PROF-012: profile_repo 있고 배치 데이터 있으면 Redis 저장"""
        from app.schemas.common import RealtimePersonalContextRequest

        batch_data = {
            "daily": {"balance": "5000000", "grade": "VIP"},
            "monthly": {"avgBalance": "4500000"},
        }
        profile_repo = MagicMock()
        profile_repo.get_batch_profile = AsyncMock(return_value=batch_data)
        svc = _make_profile_service(
            session_data={"session_state": "start"}, profile_repo=profile_repo
        )
        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "33333333"})
        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()
        with (
            patch("app.services.profile_service.get_redis_client"),
            patch("app.services.profile_service.RedisHelper", return_value=mock_helper),
        ):
            await svc.update_realtime_personal_context("gsess_test", req)
        mock_helper.set_batch_profile.assert_called_once_with("33333333", batch_data)

    async def test_TC_PROF_013_without_profile_repo_no_batch(self):
        """TC-PROF-013: profile_repo 없으면 배치 조회 없음"""
        from app.schemas.common import RealtimePersonalContextRequest

        svc = _make_profile_service(session_data={"session_state": "start"}, profile_repo=None)
        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "44444444"})
        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()
        with (
            patch("app.services.profile_service.get_redis_client"),
            patch("app.services.profile_service.RedisHelper", return_value=mock_helper),
        ):
            await svc.update_realtime_personal_context("gsess_test", req)
        mock_helper.set_batch_profile.assert_not_called()

    async def test_TC_PROF_014_response_status_success(self):
        """TC-PROF-014: 정상 처리 시 응답 status == 'success'"""
        from app.schemas.common import RealtimePersonalContextRequest

        svc = _make_profile_service(session_data={"session_state": "start"})
        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "55555555"})
        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()
        with (
            patch("app.services.profile_service.get_redis_client"),
            patch("app.services.profile_service.RedisHelper", return_value=mock_helper),
        ):
            result = await svc.update_realtime_personal_context("gsess_test", req)
        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.updated_at)


# =============================================================================
# TC-SESS: SessionService 단위 테스트
# =============================================================================

def _make_session_service(session_data=None, auth_tokens=None, profile_service=None):
    from app.services.session_service import SessionService

    session_repo = MagicMock()
    session_repo.create = AsyncMock()
    session_repo.get = AsyncMock(return_value=session_data)
    session_repo.update = AsyncMock()
    session_repo.refresh_ttl = AsyncMock()
    session_repo.get_local_mapping = AsyncMock(return_value=None)
    session_repo.set_local_mapping = AsyncMock()

    if auth_tokens is None:
        auth_tokens = {"access_token": "access_x", "refresh_token": "refresh_x", "jti": "jti_x"}
    auth_service = MagicMock()
    auth_service.create_tokens = AsyncMock(return_value=auth_tokens)

    if profile_service is None:
        profile_service = MagicMock()
        profile_service.get_batch_and_realtime_profiles = AsyncMock(return_value=(None, None))

    svc = SessionService(
        session_repo=session_repo,
        auth_service=auth_service,
        profile_service=profile_service,
    )
    return svc, session_repo, auth_service


_ESLOG_PATCH = patch("app.logger_config.logging.Logger.eslog", return_value=None)


class TestSessionCreate(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-001~009: create_session 검증"""

    async def test_TC_SESS_001_returns_key_and_tokens(self):
        """TC-SESS-001: 정상 입력 -> global_session_key, access_token, refresh_token, jti 반환"""
        from app.schemas.common import SessionCreateRequest

        svc, _, _ = _make_session_service()
        req = SessionCreateRequest(userId="700000001")
        with _ESLOG_PATCH:
            result = await svc.create_session(req)
        self.assertTrue(result.global_session_key.startswith("gsess_"))
        self.assertEqual(result.access_token, "access_x")
        self.assertEqual(result.refresh_token, "refresh_x")
        self.assertEqual(result.jti, "jti_x")

    async def test_TC_SESS_002_channel_none_sets_utterance(self):
        """TC-SESS-002: channel 없으면 channel='utterance', start_type=None"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_session_service()
        req = SessionCreateRequest(userId="user_001")
        with _ESLOG_PATCH:
            await svc.create_session(req)
        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["channel"], "utterance")
        self.assertIsNone(call_kwargs["start_type"])

    async def test_TC_SESS_003_channel_provided_sets_correct_values(self):
        """TC-SESS-003: channel 있으면 event_channel, event_type 그대로 사용"""
        from app.schemas.common import ChannelInfo, SessionCreateRequest

        svc, repo, _ = _make_session_service()
        req = SessionCreateRequest(
            userId="user_002",
            channel=ChannelInfo(eventType="ICON_ENTRY", eventChannel="SOL"),
        )
        with _ESLOG_PATCH:
            await svc.create_session(req)
        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["channel"], "SOL")
        self.assertEqual(call_kwargs["start_type"], "ICON_ENTRY")

    async def test_TC_SESS_004_user_id_none_defaults_to_empty(self):
        """TC-SESS-004: userId 없으면 user_id=''"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_session_service()
        req = SessionCreateRequest()
        with _ESLOG_PATCH:
            await svc.create_session(req)
        self.assertEqual(repo.create.call_args[1]["user_id"], "")

    async def test_TC_SESS_005_trigger_id_none_defaults_to_empty(self):
        """TC-SESS-005: triggerId 없으면 trigger_id=''"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_session_service()
        req = SessionCreateRequest(userId="user_003")
        with _ESLOG_PATCH:
            await svc.create_session(req)
        self.assertEqual(repo.create.call_args[1]["trigger_id"], "")

    async def test_TC_SESS_006_trigger_id_passed_correctly(self):
        """TC-SESS-006: triggerId 있으면 그대로 전달"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_session_service()
        req = SessionCreateRequest(userId="user_004", triggerId="TRG-001")
        with _ESLOG_PATCH:
            await svc.create_session(req)
        self.assertEqual(repo.create.call_args[1]["trigger_id"], "TRG-001")

    async def test_TC_SESS_007_session_state_is_start(self):
        """TC-SESS-007: 세션 생성 시 session_state='start'"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_session_service()
        req = SessionCreateRequest(userId="user_005")
        with _ESLOG_PATCH:
            await svc.create_session(req)
        self.assertEqual(repo.create.call_args[1]["session_state"], "start")

    async def test_TC_SESS_008_auth_service_called(self):
        """TC-SESS-008: auth_service.create_tokens 호출"""
        from app.schemas.common import SessionCreateRequest

        svc, _, auth = _make_session_service()
        req = SessionCreateRequest(userId="user_006")
        with _ESLOG_PATCH:
            await svc.create_session(req)
        auth.create_tokens.assert_called_once()

    async def test_TC_SESS_009_es_log_payload_no_field_info(self):
        """TC-SESS-009: SESSION_CREATE ES 로그 payload 직렬화 성공 (FieldInfo 없음)"""
        from datetime import UTC, datetime

        from app.logger_config import LoggerExtraData

        log_msg = LoggerExtraData(
            logType="SESSION_CREATE",
            sessionId="gsess_test",
            payload={
                "userId": "user_007",
                "channel": "SOL",
                "startType": "ICON_ENTRY",
                "triggerId": "TRG-007",
                "createdAt": datetime.now(UTC).isoformat(),
            },
        )
        json_str = log_msg.model_dump_json()
        self.assertIn("SESSION_CREATE", json_str)
        self.assertIn("user_007", json_str)


class TestSessionResolve(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-010~015: resolve_session 검증"""

    async def test_TC_SESS_010_session_not_found_raises(self):
        """TC-SESS-010: 세션 없음 -> SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import AgentType, SessionResolveRequest

        svc, _, _ = _make_session_service(session_data=None)
        req = SessionResolveRequest(global_session_key="gsess_missing", agent_type=AgentType.KNOWLEDGE)
        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)
        with (
            patch("app.services.session_service.get_redis_client"),
            patch("app.services.session_service.RedisHelper", return_value=mock_helper),
            _ESLOG_PATCH,
        ):
            with self.assertRaises(SessionNotFoundError):
                await svc.resolve_session(req)

    async def test_TC_SESS_011_session_found_returns_response(self):
        """TC-SESS-011: 세션 있음 -> SessionResolveResponse 반환"""
        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "start",
            "user_id": "user_001",
            "channel": "SOL",
            "start_type": "ICON_ENTRY",
            "task_queue_status": "null",
            "subagent_status": "undefined",
        }
        svc, _, _ = _make_session_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_found", agent_type=AgentType.KNOWLEDGE)
        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)
        with (
            patch("app.services.session_service.get_redis_client"),
            patch("app.services.session_service.RedisHelper", return_value=mock_helper),
            _ESLOG_PATCH,
        ):
            result = await svc.resolve_session(req)
        self.assertEqual(result.global_session_key, "gsess_found")
        self.assertEqual(result.session_state.value, "start")

    async def test_TC_SESS_012_cusno_calls_batch_profiles(self):
        """TC-SESS-012: 세션에 cusno 있으면 get_batch_and_realtime_profiles 호출"""
        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "talk",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "cusno": "12345678",
        }
        profile_service = MagicMock()
        profile_service.get_batch_and_realtime_profiles = AsyncMock(
            return_value=({"batch": "data"}, {"realtime": "data"})
        )
        svc, _, _ = _make_session_service(session_data=session_data, profile_service=profile_service)
        req = SessionResolveRequest(global_session_key="gsess_cusno", agent_type=AgentType.KNOWLEDGE)
        with _ESLOG_PATCH:
            await svc.resolve_session(req)
        profile_service.get_batch_and_realtime_profiles.assert_called_once_with("12345678")

    async def test_TC_SESS_013_no_cusno_uses_session_key(self):
        """TC-SESS-013: 세션에 cusno 없으면 session_key 로 실시간 프로파일 조회"""
        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "start",
            "task_queue_status": "null",
            "subagent_status": "undefined",
        }
        svc, _, _ = _make_session_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_nocusno", agent_type=AgentType.KNOWLEDGE)
        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)
        with (
            patch("app.services.session_service.get_redis_client"),
            patch("app.services.session_service.RedisHelper", return_value=mock_helper),
            _ESLOG_PATCH,
        ):
            await svc.resolve_session(req)
        mock_helper.get_realtime_profile.assert_called_once_with("gsess_nocusno")

    async def test_TC_SESS_014_invalid_conversation_history_becomes_none(self):
        """TC-SESS-014: reference_information.conversation_history 가 list 아니면 None"""
        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "talk",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "reference_information": json.dumps({"conversation_history": "invalid_string"}),
        }
        svc, _, _ = _make_session_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_ref", agent_type=AgentType.KNOWLEDGE)
        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)
        with (
            patch("app.services.session_service.get_redis_client"),
            patch("app.services.session_service.RedisHelper", return_value=mock_helper),
            _ESLOG_PATCH,
        ):
            result = await svc.resolve_session(req)
        self.assertIsNone(result.conversation_history)

    async def test_TC_SESS_015_invalid_turn_count_becomes_none(self):
        """TC-SESS-015: reference_information.turn_count 가 int 아니면 None"""
        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "talk",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "reference_information": json.dumps({"turn_count": "not_int"}),
        }
        svc, _, _ = _make_session_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_tc", agent_type=AgentType.KNOWLEDGE)
        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)
        with (
            patch("app.services.session_service.get_redis_client"),
            patch("app.services.session_service.RedisHelper", return_value=mock_helper),
            _ESLOG_PATCH,
        ):
            result = await svc.resolve_session(req)
        self.assertIsNone(result.turn_count)


class TestSessionPatch(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-016~021: patch_session_state 검증"""

    async def test_TC_SESS_016_session_not_found_raises(self):
        """TC-SESS-016: 세션 없음 -> SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import SessionPatchRequest, SessionState

        svc, _, _ = _make_session_service(session_data=None)
        req = SessionPatchRequest(global_session_key="gsess_missing", session_state=SessionState.TALK)
        with self.assertRaises(SessionNotFoundError):
            with _ESLOG_PATCH:
                await svc.patch_session_state(req)

    async def test_TC_SESS_017_talk_state_calls_refresh_ttl(self):
        """TC-SESS-017: session_state=TALK 이면 refresh_ttl 호출"""
        from app.schemas.common import SessionPatchRequest, SessionState

        svc, repo, _ = _make_session_service(
            session_data={"session_state": "start", "task_queue_status": "null"}
        )
        req = SessionPatchRequest(global_session_key="gsess_talk", session_state=SessionState.TALK)
        with _ESLOG_PATCH:
            await svc.patch_session_state(req)
        repo.refresh_ttl.assert_called_once_with("gsess_talk")

    async def test_TC_SESS_018_non_talk_no_refresh_ttl(self):
        """TC-SESS-018: session_state=TALK 이 아니면 refresh_ttl 미호출"""
        from app.schemas.common import SessionPatchRequest, SessionState

        svc, repo, _ = _make_session_service(
            session_data={"session_state": "start", "task_queue_status": "null"}
        )
        req = SessionPatchRequest(global_session_key="gsess_end", session_state=SessionState.END)
        with _ESLOG_PATCH:
            await svc.patch_session_state(req)
        repo.refresh_ttl.assert_not_called()

    async def test_TC_SESS_019_turn_id_accumulated(self):
        """TC-SESS-019: turn_id 중복 없이 누적 저장"""
        from app.schemas.common import SessionPatchRequest

        existing_turns = json.dumps(["turn_001", "turn_002"])
        svc, repo, _ = _make_session_service(
            session_data={
                "session_state": "talk",
                "task_queue_status": "null",
                "turn_ids": existing_turns,
            }
        )
        req = SessionPatchRequest(global_session_key="gsess_turn", turn_id="turn_003")
        with _ESLOG_PATCH:
            await svc.patch_session_state(req)
        turn_ids = json.loads(repo.update.call_args[1]["turn_ids"])
        self.assertIn("turn_003", turn_ids)
        self.assertEqual(len([t for t in turn_ids if t == "turn_003"]), 1)

    async def test_TC_SESS_020_duplicate_turn_id_not_added(self):
        """TC-SESS-020: 이미 있는 turn_id 는 중복 추가 안 됨"""
        from app.schemas.common import SessionPatchRequest

        existing_turns = json.dumps(["turn_001"])
        svc, repo, _ = _make_session_service(
            session_data={
                "session_state": "talk",
                "task_queue_status": "null",
                "turn_ids": existing_turns,
            }
        )
        req = SessionPatchRequest(global_session_key="gsess_dup", turn_id="turn_001")
        with _ESLOG_PATCH:
            await svc.patch_session_state(req)
        turn_ids = json.loads(repo.update.call_args[1]["turn_ids"])
        self.assertEqual(turn_ids.count("turn_001"), 1)

    async def test_TC_SESS_021_invalid_conversation_history_raises_400(self):
        """TC-SESS-021: conversation_history 가 list 아니면 400"""
        from fastapi import HTTPException

        from app.schemas.common import SessionPatchRequest, StatePatch

        svc, _, _ = _make_session_service(
            session_data={"session_state": "talk", "task_queue_status": "null"}
        )
        req = SessionPatchRequest(
            global_session_key="gsess_invalid",
            state_patch=StatePatch(reference_information={"conversation_history": "not_a_list"}),
        )
        with self.assertRaises(HTTPException) as ctx:
            with _ESLOG_PATCH:
                await svc.patch_session_state(req)
        self.assertEqual(ctx.exception.status_code, 400)


class TestSessionClose(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-022~025: close_session 검증"""

    async def test_TC_SESS_022_session_not_found_raises(self):
        """TC-SESS-022: 세션 없음 -> SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import SessionCloseRequest

        svc, _, _ = _make_session_service(session_data=None)
        req = SessionCloseRequest(global_session_key="gsess_missing", close_reason="test")
        with self.assertRaises(SessionNotFoundError):
            with _ESLOG_PATCH:
                await svc.close_session(req)

    async def test_TC_SESS_023_close_sets_state_end(self):
        """TC-SESS-023: 정상 종료 -> session_state='end' 업데이트"""
        from app.schemas.common import SessionCloseRequest

        svc, repo, _ = _make_session_service(
            session_data={"session_state": "talk", "task_queue_status": "null"}
        )
        req = SessionCloseRequest(global_session_key="gsess_close", close_reason="user_request")
        with _ESLOG_PATCH:
            await svc.close_session(req)
        update_call = repo.update.call_args[1]
        self.assertEqual(update_call["session_state"], "end")
        self.assertEqual(update_call["close_reason"], "user_request")

    async def test_TC_SESS_024_archived_id_format(self):
        """TC-SESS-024: archived_id = 'arch_{global_session_key}'"""
        from app.schemas.common import SessionCloseRequest

        svc, _, _ = _make_session_service(
            session_data={"session_state": "talk", "task_queue_status": "null"}
        )
        req = SessionCloseRequest(global_session_key="gsess_arch", close_reason="done")
        with _ESLOG_PATCH:
            result = await svc.close_session(req)
        self.assertEqual(result.archived_conversation_id, "arch_gsess_arch")

    async def test_TC_SESS_025_final_summary_saved(self):
        """TC-SESS-025: final_summary 있으면 업데이트에 포함"""
        from app.schemas.common import SessionCloseRequest

        svc, repo, _ = _make_session_service(
            session_data={"session_state": "talk", "task_queue_status": "null"}
        )
        req = SessionCloseRequest(
            global_session_key="gsess_summary",
            close_reason="done",
            final_summary="This is summary",
        )
        with _ESLOG_PATCH:
            await svc.close_session(req)
        self.assertEqual(repo.update.call_args[1]["final_summary"], "This is summary")


class TestSerializeReferenceInformation(unittest.TestCase):
    """TC-SESS-026~028: _serialize_reference_information 정적 메서드 검증"""

    def setUp(self):
        from app.services.session_service import SessionService

        self.SS = SessionService

    def test_TC_SESS_026_empty_dict(self):
        """TC-SESS-026: 빈 dict -> '{}'"""
        self.assertEqual(self.SS._serialize_reference_information({}), "{}")

    def test_TC_SESS_027_keys_are_sorted(self):
        """TC-SESS-027: 출력 JSON 키가 정렬됨"""
        result = self.SS._serialize_reference_information({"z_key": 1, "a_key": 2})
        keys = list(json.loads(result).keys())
        self.assertEqual(keys, sorted(keys))

    def test_TC_SESS_028_list_order_preserved(self):
        """TC-SESS-028: list 순서 유지"""
        data = {"conversation_history": [{"msg": "first"}, {"msg": "second"}]}
        parsed = json.loads(self.SS._serialize_reference_information(data))
        self.assertEqual(parsed["conversation_history"][0]["msg"], "first")
        self.assertEqual(parsed["conversation_history"][1]["msg"], "second")


# =============================================================================
# 통합 테스트 베이스 (Redis 필요)
# =============================================================================

class IntegrationBase(unittest.IsolatedAsyncioTestCase):
    """통합 테스트 공통 베이스: Redis 없으면 전체 클래스 스킵."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not _check_redis():
            raise unittest.SkipTest("Redis 연결 불가 — 통합 테스트 스킵")

    async def asyncSetUp(self) -> None:
        import uuid

        self.test_key = f"inttest_{uuid.uuid4().hex[:12]}"
        self.redis = _REDIS_CLIENT

    async def asyncTearDown(self) -> None:
        await _cleanup_redis_keys(self.redis)


# =============================================================================
# IT-SESS: 세션 서비스 통합 테스트
# =============================================================================

class TestIntegrationSession(IntegrationBase):
    """IT-SESS-001~008: 세션 서비스 실 Redis 검증"""

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        from app.repositories.redis_session_repository import RedisSessionRepository
        from app.services.auth_service import AuthService
        from app.services.profile_service import ProfileService
        from app.services.session_service import SessionService

        repo = RedisSessionRepository()
        auth_svc = AuthService(session_repo=repo)
        profile_svc = ProfileService(session_repo=repo)
        self.svc = SessionService(
            session_repo=repo, auth_service=auth_svc, profile_service=profile_svc
        )
        self._gskey: str = ""

    async def _create(self):
        from app.schemas.common import SessionCreateRequest

        req = SessionCreateRequest(userId="IT700000001")
        with _ESLOG_PATCH:
            result = await self.svc.create_session(req)
        self._gskey = result.global_session_key
        return result

    async def test_IT_SESS_001_create_stores_in_redis(self):
        """IT-SESS-001: 세션 생성 후 Redis 에 데이터 저장 확인"""
        result = await self._create()
        self.assertTrue(result.global_session_key.startswith("gsess_"))
        raw = await self.redis.get(result.global_session_key)
        self.assertIsNotNone(raw)

    async def test_IT_SESS_002_create_ttl_set(self):
        """IT-SESS-002: 세션 생성 후 TTL > 0"""
        result = await self._create()
        self.assertGreater(await self.redis.ttl(result.global_session_key), 0)

    async def test_IT_SESS_003_resolve_returns_session(self):
        """IT-SESS-003: 생성된 세션 조회"""
        from app.schemas.common import AgentType, SessionResolveRequest

        created = await self._create()
        req = SessionResolveRequest(
            global_session_key=created.global_session_key, agent_type=AgentType.KNOWLEDGE
        )
        with _ESLOG_PATCH:
            resolved = await self.svc.resolve_session(req)
        self.assertEqual(resolved.global_session_key, created.global_session_key)

    async def test_IT_SESS_004_resolve_missing_raises(self):
        """IT-SESS-004: 없는 세션 조회 -> SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import AgentType, SessionResolveRequest

        req = SessionResolveRequest(
            global_session_key="gsess_it_nonexist_12345", agent_type=AgentType.KNOWLEDGE
        )
        with self.assertRaises(SessionNotFoundError):
            with _ESLOG_PATCH:
                await self.svc.resolve_session(req)

    async def test_IT_SESS_005_patch_adds_turn_id(self):
        """IT-SESS-005: patch 후 turn_id 누적 저장"""
        from app.schemas.common import SessionPatchRequest

        created = await self._create()
        req = SessionPatchRequest(
            global_session_key=created.global_session_key, turn_id="it_turn_001"
        )
        with _ESLOG_PATCH:
            await self.svc.patch_session_state(req)
        raw = await self.redis.get(created.global_session_key)
        turn_ids = json.loads(json.loads(raw).get("turn_ids", "[]"))
        self.assertIn("it_turn_001", turn_ids)

    async def test_IT_SESS_006_patch_duplicate_turn_id_ignored(self):
        """IT-SESS-006: 동일 turn_id 두 번 patch 해도 중복 없음"""
        from app.schemas.common import SessionPatchRequest

        created = await self._create()
        for _ in range(2):
            with _ESLOG_PATCH:
                await self.svc.patch_session_state(
                    SessionPatchRequest(
                        global_session_key=created.global_session_key, turn_id="it_turn_dup"
                    )
                )
        raw = await self.redis.get(created.global_session_key)
        turn_ids = json.loads(json.loads(raw).get("turn_ids", "[]"))
        self.assertEqual(turn_ids.count("it_turn_dup"), 1)

    async def test_IT_SESS_007_close_sets_state_end(self):
        """IT-SESS-007: 세션 종료 후 session_state 변경 확인"""
        from app.schemas.common import SessionCloseRequest

        created = await self._create()
        req = SessionCloseRequest(
            global_session_key=created.global_session_key, close_reason="USER_LOGOUT"
        )
        with _ESLOG_PATCH:
            result = await self.svc.close_session(req)
        state_val = getattr(result.session_state, "value", result.session_state)
        self.assertIn(state_val.lower(), ("end", "closed"))

    async def test_IT_SESS_008_close_archived_id_format(self):
        """IT-SESS-008: close 응답 archived_conversation_id 에 세션키 포함"""
        from app.schemas.common import SessionCloseRequest

        created = await self._create()
        req = SessionCloseRequest(
            global_session_key=created.global_session_key, close_reason="done"
        )
        with _ESLOG_PATCH:
            result = await self.svc.close_session(req)
        self.assertIn(created.global_session_key, result.archived_conversation_id)


# =============================================================================
# IT-AUTH: 인증 서비스 통합 테스트
# =============================================================================

class TestIntegrationAuth(IntegrationBase):
    """IT-AUTH-001~007: 인증 서비스 실 Redis 검증"""

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        from app.repositories.redis_session_repository import RedisSessionRepository
        from app.services.auth_service import AuthService

        repo = RedisSessionRepository()
        self.svc = AuthService(session_repo=repo)
        self._gskey = f"gsess_it_{self.test_key}"

    async def asyncTearDown(self) -> None:
        jti_keys = await self.redis.keys("jti:*")
        if jti_keys:
            await self.redis.delete(*jti_keys)
        await super().asyncTearDown()

    async def test_IT_AUTH_001_create_tokens_saves_jti(self):
        """IT-AUTH-001: 토큰 생성 후 jti Redis 저장 확인"""
        result = await self.svc.create_tokens("IT_user_001", self._gskey)
        self.assertIn("access_token", result)
        self.assertGreater(len(result["access_token"]), 20)
        jti_keys = await self.redis.keys("jti:*")
        self.assertGreaterEqual(len(jti_keys), 1)

    async def test_IT_AUTH_002_verify_returns_session_info(self):
        """IT-AUTH-002: 발급된 access token 검증 -> 세션 정보 반환"""
        result = await self.svc.create_tokens("IT_user_002", self._gskey)
        verify = await self.svc.verify_token_and_get_session(result["access_token"])
        self.assertIsNotNone(verify)

    async def test_IT_AUTH_003_refresh_rotates_jti(self):
        """IT-AUTH-003: Refresh 후 jti 갱신"""
        first = await self.svc.create_tokens("IT_user_003", self._gskey)
        jti_before = {
            (k.decode() if isinstance(k, bytes) else k)
            for k in await self.redis.keys("jti:*")
        }
        refreshed = await self.svc.refresh_token(first["refresh_token"])
        self.assertGreater(len(refreshed.access_token), 20)
        jti_after = {
            (k.decode() if isinstance(k, bytes) else k)
            for k in await self.redis.keys("jti:*")
        }
        self.assertNotEqual(jti_before, jti_after)

    async def test_IT_AUTH_004_invalid_token_raises_401(self):
        """IT-AUTH-004: 위조 access token -> 401"""
        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            await self.svc.verify_token_and_get_session("not.a.real.token")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_IT_AUTH_005_refresh_with_access_token_raises_401(self):
        """IT-AUTH-005: access token 으로 refresh 요청 -> 401"""
        from fastapi import HTTPException

        result = await self.svc.create_tokens("IT_user_005", self._gskey)
        with self.assertRaises(HTTPException) as ctx:
            await self.svc.refresh_token(result["access_token"])
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_IT_AUTH_006_jti_ttl_positive(self):
        """IT-AUTH-006: jti Redis 키 TTL > 0"""
        await self.svc.create_tokens("IT_user_006", self._gskey)
        keys = await self.redis.keys("jti:*")
        self.assertGreaterEqual(len(keys), 1)
        self.assertGreater(await self.redis.ttl(keys[0]), 0)

    async def test_IT_AUTH_007_token_jti_uuid_format(self):
        """IT-AUTH-007: 발급된 jti 가 UUID 형식"""
        import re

        result = await self.svc.create_tokens("IT_user_007", self._gskey)
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        self.assertRegex(result["jti"], uuid_pattern)


# =============================================================================
# IT-PROF: 프로파일 서비스 통합 테스트
# =============================================================================

class TestIntegrationProfile(IntegrationBase):
    """IT-PROF-001~006: 프로파일 서비스 실 Redis 검증 (RedisHelper 직접 사용)"""

    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        import uuid

        from app.db.redis import RedisHelper
        from app.repositories.redis_session_repository import RedisSessionRepository
        from app.services.profile_service import ProfileService

        self.cusno = f"9{uuid.uuid4().int % 10 ** 7:07d}"
        repo = RedisSessionRepository()
        self.svc = ProfileService(session_repo=repo)
        self.helper = RedisHelper(self.redis)

    async def asyncTearDown(self) -> None:
        for pattern in (f"realtime:{self.cusno}*", f"batch:{self.cusno}*"):
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        await super().asyncTearDown()

    async def test_IT_PROF_001_set_and_get_realtime_profile(self):
        """IT-PROF-001: 실시간 프로파일 저장 후 조회"""
        sample = {"risk_grade": "3", "asset_total": "5000000"}
        await self.helper.set_realtime_profile(self.cusno, sample)
        stored = await self.helper.get_realtime_profile(self.cusno)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.get("risk_grade"), "3")

    async def test_IT_PROF_002_realtime_ttl_set(self):
        """IT-PROF-002: 실시간 프로파일 Redis TTL > 0"""
        await self.helper.set_realtime_profile(self.cusno, {"k": "v"})
        key = f"realtime:{self.cusno}"
        ttl = await self.redis.ttl(key)
        self.assertGreater(ttl, 0)

    async def test_IT_PROF_003_batch_set_and_get(self):
        """IT-PROF-003: 배치 프로파일 저장 후 조회"""
        batch = {"daily": {"loan_total": "1000000"}, "monthly": {}}
        await self.helper.set_batch_profile(self.cusno, batch)
        stored = await self.helper.get_batch_profile(self.cusno)
        self.assertIsNotNone(stored)
        self.assertIn("daily", stored)

    async def test_IT_PROF_004_get_profiles_returns_both(self):
        """IT-PROF-004: get_batch_and_realtime_profiles -> (batch, realtime) 반환"""
        await self.helper.set_realtime_profile(self.cusno, {"risk_grade": "4"})
        await self.helper.set_batch_profile(
            self.cusno, {"daily": {"amount": "100"}, "monthly": {}}
        )
        batch, realtime = await self.svc.get_batch_and_realtime_profiles(self.cusno)
        self.assertIsNotNone(batch)
        self.assertIsNotNone(realtime)

    async def test_IT_PROF_005_missing_cusno_returns_none(self):
        """IT-PROF-005: Redis 에 없는 cusno -> (None, None) 반환"""
        batch, realtime = await self.svc.get_batch_and_realtime_profiles("00000000IT")
        self.assertIsNone(batch)
        self.assertIsNone(realtime)

    async def test_IT_PROF_006_get_merged_profile_realtime_priority(self):
        """IT-PROF-006: 실시간 프로파일이 배치보다 우선 (merged_profile)"""
        await self.helper.set_realtime_profile(
            self.cusno, {"cusnoN10": self.cusno, "risk_grade": "RT"}
        )
        await self.helper.set_batch_profile(
            self.cusno,
            {"daily": {"risk_grade": "BATCH"}, "monthly": {}},
        )
        _, realtime = await self.svc.get_batch_and_realtime_profiles(self.cusno)
        self.assertIsNotNone(realtime)
        self.assertEqual(realtime.get("risk_grade"), "RT")


# =============================================================================
# 러너
# =============================================================================

# 카테고리 → 테스트 클래스 매핑
_UNIT: dict[str, list[type]] = {
    "log": [TestLoggerExtraData],
    "auth": [TestAuthCreateTokens, TestAuthVerifyToken, TestAuthRefreshToken],
    "profile": [TestProfileMerge, TestProfileUpdateRealtime],
    "session": [
        TestSessionCreate,
        TestSessionResolve,
        TestSessionPatch,
        TestSessionClose,
        TestSerializeReferenceInformation,
    ],
}
_INTEGRATION: dict[str, list[type]] = {
    "auth": [TestIntegrationAuth],
    "profile": [TestIntegrationProfile],
    "session": [TestIntegrationSession],
}


def _build_suite(filter_arg: str | None) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    def _add(classes: list[type]) -> None:
        for cls in classes:
            suite.addTests(loader.loadTestsFromTestCase(cls))

    if filter_arg == "unit":
        for classes in _UNIT.values():
            _add(classes)
    elif filter_arg == "integration":
        for classes in _INTEGRATION.values():
            _add(classes)
    elif filter_arg in _UNIT:
        _add(_UNIT[filter_arg])
        if filter_arg in _INTEGRATION:
            _add(_INTEGRATION[filter_arg])
    elif filter_arg is None:
        for classes in _UNIT.values():
            _add(classes)
        for classes in _INTEGRATION.values():
            _add(classes)
    else:
        valid = sorted(set(list(_UNIT) + list(_INTEGRATION) + ["unit", "integration"]))
        print(f"알 수 없는 필터: {filter_arg!r}\n가능한 값: {valid}", file=sys.stderr)
        sys.exit(2)

    return suite


def main() -> int:
    filter_arg = sys.argv[1].lower() if len(sys.argv) > 1 else None

    redis_ok: bool | None = None
    if filter_arg not in ("unit", "log"):
        redis_ok = _check_redis()
        redis_status = "연결됨" if redis_ok else "불가 (통합 테스트 자동 스킵)"
    else:
        redis_status = "사용 안 함 (단위 테스트만)"

    print()
    print("=" * 65)
    print("  Session Manager 테스트 러너  (pytest-free)")
    print(f"  대상    : {filter_arg or '전체 (단위 + 통합)'}")
    print(f"  Redis   : {redis_status}")
    print("=" * 65)
    print()

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(_build_suite(filter_arg))

    skipped = len(result.skipped)
    print()
    print("=" * 65)
    if result.wasSuccessful():
        print(
            f"  PASSED  run={result.testsRun}  fail=0  error=0  skip={skipped}"
        )
        return 0
    else:
        print(
            f"  FAILED  run={result.testsRun}"
            f"  fail={len(result.failures)}"
            f"  error={len(result.errors)}"
            f"  skip={skipped}"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
