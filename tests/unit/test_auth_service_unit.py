"""TC-AUTH: AuthService 순수 로직 단위 테스트 (Mock Redis)"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCreateTokens(unittest.IsolatedAsyncioTestCase):
    """TC-AUTH-001~004: create_tokens 검증"""

    def _make_service(self, session_repo=None):
        from app.services.auth_service import AuthService

        return AuthService(session_repo=session_repo or MagicMock())

    async def test_returns_access_refresh_jti(self):
        """TC-AUTH-001: 정상 입력 -> access_token, refresh_token, jti 반환"""
        svc = self._make_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()

        with patch("app.services.auth_service.get_redis_client", return_value=mock_redis), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.create_tokens("700000001", "gsess_test_001")

        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)
        self.assertIn("jti", result)

    async def test_jti_is_uuid_format(self):
        """TC-AUTH-002: jti 가 UUID 형식"""
        import re

        svc = self._make_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()

        with patch("app.services.auth_service.get_redis_client", return_value=mock_redis), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.create_tokens("user", "gsess_test")

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        self.assertRegex(result["jti"], uuid_pattern)

    async def test_jti_mapping_saved_to_redis(self):
        """TC-AUTH-003: Redis 에 jti -> global_session_key 매핑 저장"""
        svc = self._make_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()

        with patch("app.services.auth_service.get_redis_client", return_value=mock_redis), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            await svc.create_tokens("user", "gsess_test_key")

        mock_helper.set_jti_mapping.assert_called_once()
        call_args = mock_helper.set_jti_mapping.call_args
        self.assertEqual(call_args[0][1], "gsess_test_key")

    async def test_empty_user_id_allowed(self):
        """TC-AUTH-004: user_id 빈 문자열허용"""
        svc = self._make_service()
        mock_redis = MagicMock()
        mock_helper = MagicMock()
        mock_helper.set_jti_mapping = AsyncMock()

        with patch("app.services.auth_service.get_redis_client", return_value=mock_redis), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.create_tokens("", "gsess_empty_user")

        self.assertIn("access_token", result)


class TestVerifyTokenAndGetSession(unittest.IsolatedAsyncioTestCase):
    """TC-AUTH-005~011: verify_token_and_get_session 검증"""

    def _make_service(self, session_data=None):
        from app.services.auth_service import AuthService

        session_repo = MagicMock()
        session_repo.get = AsyncMock(return_value=session_data)
        return AuthService(session_repo=session_repo)

    async def test_invalid_token_raises_401(self):
        """TC-AUTH-005: 위조/만료 토큰 -> 401"""
        from fastapi import HTTPException

        svc = self._make_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.verify_token_and_get_session("invalid_token_string")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_refresh_token_type_raises_401(self):
        """TC-AUTH-006: type != 'access' (refresh 토큰) -> 401"""
        from fastapi import HTTPException

        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_refresh_token

        refresh_token = create_refresh_token("test_jti", "user_id", JWT_SECRET_KEY)
        svc = self._make_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.verify_token_and_get_session(refresh_token)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_jti_not_in_redis_raises_401(self):
        """TC-AUTH-007: jti Redis 매핑 없음 -> 401"""
        from fastapi import HTTPException

        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("no_jti_in_redis", "user_id", JWT_SECRET_KEY)
        svc = self._make_service()

        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value=None)

        with patch("app.services.auth_service.get_redis_client"), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            with self.assertRaises(HTTPException) as ctx:
                await svc.verify_token_and_get_session(access_token)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_session_not_found_returns_is_alive_false(self):
        """TC-AUTH-008: 세션 없음 -> is_alive=False"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("test_jti", "user_id", JWT_SECRET_KEY)
        svc = self._make_service(session_data=None)

        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_test")

        with patch("app.services.auth_service.get_redis_client"), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.verify_token_and_get_session(access_token)

        self.assertFalse(result.is_alive)

    async def test_session_found_returns_is_alive_true(self):
        """TC-AUTH-009: 세션 있음 -> is_alive=True"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("test_jti_2", "user_id", JWT_SECRET_KEY)
        svc = self._make_service(session_data={"session_state": "talk", "user_id": "user_id"})

        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_test")
        mock_helper.get_ttl = AsyncMock(return_value=300)

        with patch("app.services.auth_service.get_redis_client"), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.verify_token_and_get_session(access_token)

        self.assertTrue(result.is_alive)


class TestRefreshToken(unittest.IsolatedAsyncioTestCase):
    """TC-AUTH-012~015: refresh_token 검증"""

    def _make_service(self, session_data=None):
        from app.services.auth_service import AuthService

        session_repo = MagicMock()
        session_repo.get = AsyncMock(return_value=session_data)
        session_repo.refresh_ttl = AsyncMock()
        return AuthService(session_repo=session_repo)

    async def test_invalid_refresh_token_raises_401(self):
        """TC-AUTH-012: 위조 refresh 토큰 -> 401"""
        from fastapi import HTTPException

        svc = self._make_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.refresh_token("invalid_refresh_token")
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_access_token_used_as_refresh_raises_401(self):
        """TC-AUTH-013: access 토큰으로 refresh 요청 -> 401"""
        from fastapi import HTTPException

        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_access_token

        access_token = create_access_token("jti_x", "user", JWT_SECRET_KEY)
        svc = self._make_service()
        with self.assertRaises(HTTPException) as ctx:
            await svc.refresh_token(access_token)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_valid_refresh_returns_new_tokens(self):
        """TC-AUTH-014: 정상 refresh -> 새 access_token, refresh_token, jti 반환"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_refresh_token

        old_jti = "old_jti_value"
        refresh_token = create_refresh_token(old_jti, "user_id", JWT_SECRET_KEY)

        svc = self._make_service(session_data={"session_state": "talk"})

        mock_redis = MagicMock()
        mock_redis.delete = AsyncMock()

        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_key")
        mock_helper.delete_jti_mapping = AsyncMock()
        mock_helper.set_jti_mapping = AsyncMock()

        with patch("app.services.auth_service.get_redis_client", return_value=mock_redis), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.refresh_token(refresh_token)

        self.assertTrue(result.access_token)
        self.assertTrue(result.refresh_token)
        self.assertNotEqual(result.jti, old_jti)

    async def test_refresh_calls_refresh_ttl(self):
        """TC-AUTH-015: refresh 성공 시 session_repo.refresh_ttl 호출"""
        from app.config import JWT_SECRET_KEY
        from app.core.jwt import create_refresh_token

        refresh_token = create_refresh_token("jti_refresh", "user_id", JWT_SECRET_KEY)
        svc = self._make_service(session_data={"session_state": "talk"})

        mock_redis = MagicMock()
        mock_redis.delete = AsyncMock()

        mock_helper = MagicMock()
        mock_helper.get_global_session_key_by_jti = AsyncMock(return_value="gsess_key")
        mock_helper.delete_jti_mapping = AsyncMock()
        mock_helper.set_jti_mapping = AsyncMock()

        with patch("app.services.auth_service.get_redis_client", return_value=mock_redis), patch(
            "app.services.auth_service.RedisHelper", return_value=mock_helper
        ):
            await svc.refresh_token(refresh_token)

        svc.session_repo.refresh_ttl.assert_called_once_with("gsess_key")


if __name__ == "__main__":
    unittest.main()
