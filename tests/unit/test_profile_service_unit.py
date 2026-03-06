"""TC-PROF: ProfileService 순수 로직 단위 테스트 (Mock Redis/Repo)"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMergeProfiles(unittest.TestCase):
    """TC-PROF-001~007: _merge_profiles 정적 메서드 검증"""

    def setUp(self):
        from app.services.profile_service import ProfileService

        self.ProfileService = ProfileService

    def test_both_none_returns_none(self):
        """TC-PROF-001: batch/realtime 모두 None -> None 반환"""
        result = self.ProfileService._merge_profiles(None, None)
        self.assertIsNone(result)

    def test_realtime_profile_takes_priority(self):
        """TC-PROF-002: realtime 있으면 실시간 프로파일 우선"""
        realtime = {"cusnoN10": "12345", "membGdS2": "VIP"}
        result = self.ProfileService._merge_profiles(None, realtime)
        self.assertIsNotNone(result)
        self.assertEqual(result.user_id, "12345")

    def test_realtime_membgds2_sets_segment(self):
        """TC-PROF-003: realtime 에 membGdS2 있으면 segment 설정"""
        realtime = {"cusnoN10": "12345", "membGdS2": "VIP"}
        result = self.ProfileService._merge_profiles(None, realtime)
        self.assertEqual(result.segment, "VIP")

    def test_realtime_empty_values_excluded_from_attributes(self):
        """TC-PROF-004: realtime 빈 값('', None) -> attributes 에서 제외"""
        realtime = {"cusnoN10": "12345", "emptyField": "", "noneField": None, "validField": "abc"}
        result = self.ProfileService._merge_profiles(None, realtime)
        keys = [attr.key for attr in result.attributes]
        self.assertNotIn("emptyField", keys)
        self.assertNotIn("noneField", keys)
        self.assertIn("validField", keys)

    def test_batch_only_when_no_realtime(self):
        """TC-PROF-005: realtime 없으면 batch 반환"""
        from app.schemas.common import CustomerProfile

        batch = CustomerProfile(user_id="batch_user", attributes=[], segment=None, preferences={})
        result = self.ProfileService._merge_profiles(batch, None)
        self.assertEqual(result.user_id, "batch_user")

    def test_realtime_profile_source_is_realtime(self):
        """TC-PROF-006: realtime 프로파일 source 는 'realtime'"""
        realtime = {"cusnoN10": "12345", "someField": "val"}
        result = self.ProfileService._merge_profiles(None, realtime)
        self.assertEqual(result.preferences.get("source"), "realtime")

    def test_realtime_without_cusno_falls_back_to_batch_user_id(self):
        """TC-PROF-007: realtime 에 cusnoN10 없으면 batch.user_id 사용"""
        from app.schemas.common import CustomerProfile

        batch = CustomerProfile(user_id="fallback_user", attributes=[], segment=None, preferences={})
        realtime = {"someField": "val"}
        result = self.ProfileService._merge_profiles(batch, realtime)
        self.assertEqual(result.user_id, "fallback_user")


class TestUpdateRealtimePersonalContext(unittest.IsolatedAsyncioTestCase):
    """TC-PROF-008~014: update_realtime_personal_context 검증"""

    def _make_service(self, session_data=None, profile_repo=None):
        from app.services.profile_service import ProfileService

        session_repo = MagicMock()
        session_repo.get = AsyncMock(return_value=session_data)
        session_repo.update = AsyncMock()
        return ProfileService(session_repo=session_repo, profile_repo=profile_repo)

    async def test_session_not_found_raises(self):
        """TC-PROF-008: 세션 없으면 SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError

        svc = self._make_service(session_data=None)
        from app.schemas.common import RealtimePersonalContextRequest

        req = RealtimePersonalContextRequest(profile_data={"someField": "val"})
        with self.assertRaises(SessionNotFoundError):
            with patch("app.services.profile_service.get_redis_client"):
                await svc.update_realtime_personal_context("gsess_missing", req)

    async def test_cusno_from_toplevel(self):
        """TC-PROF-009: profile_data 최상위 cusnoN10 에서 cusno 추출"""
        svc = self._make_service(session_data={"session_state": "start"})
        from app.schemas.common import RealtimePersonalContextRequest

        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "11111111"})

        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()

        with patch("app.services.profile_service.get_redis_client"), patch(
            "app.services.profile_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.update_realtime_personal_context("gsess_test", req)

        self.assertEqual(result.status, "success")
        mock_helper.set_realtime_profile.assert_called_once_with("11111111", req.profile_data)

    async def test_cusno_from_response_data(self):
        """TC-PROF-010: profile_data.responseData 안의 cusnoN10 에서 cusno 추출"""
        svc = self._make_service(session_data={"session_state": "start"})
        from app.schemas.common import RealtimePersonalContextRequest

        req = RealtimePersonalContextRequest(profile_data={"responseData": {"cusnoN10": "22222222"}})

        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()

        with patch("app.services.profile_service.get_redis_client"), patch(
            "app.services.profile_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.update_realtime_personal_context("gsess_test", req)

        mock_helper.set_realtime_profile.assert_called_once_with("22222222", req.profile_data)

    async def test_no_cusno_uses_session_key(self):
        """TC-PROF-011: cusnoN10 없으면 global_session_key 로 저장"""
        svc = self._make_service(session_data={"session_state": "start"})
        from app.schemas.common import RealtimePersonalContextRequest

        req = RealtimePersonalContextRequest(profile_data={"someField": "val"})

        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()

        with patch("app.services.profile_service.get_redis_client"), patch(
            "app.services.profile_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.update_realtime_personal_context("gsess_test", req)

        mock_helper.set_realtime_profile.assert_called_once_with("gsess_test", req.profile_data)

    async def test_with_profile_repo_fetches_batch(self):
        """TC-PROF-012: profile_repo 있고 배치 프로파일 있으면 Redis 저장"""
        # MinIO/MariaDB에서 실제 반환하는 배치 데이터 구조와 동일한 형식
        batch_data = {
            "daily": {"balance": "5000000", "grade": "VIP"},
            "monthly": {"avgBalance": "4500000"},
        }
        profile_repo = MagicMock()
        profile_repo.get_batch_profile = AsyncMock(return_value=batch_data)

        svc = self._make_service(session_data={"session_state": "start"}, profile_repo=profile_repo)
        from app.schemas.common import RealtimePersonalContextRequest

        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "33333333"})

        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()

        with patch("app.services.profile_service.get_redis_client"), patch(
            "app.services.profile_service.RedisHelper", return_value=mock_helper
        ):
            await svc.update_realtime_personal_context("gsess_test", req)

        mock_helper.set_batch_profile.assert_called_once_with("33333333", batch_data)

    async def test_without_profile_repo_no_batch_fetch(self):
        """TC-PROF-013: profile_repo 없으면 배치 조회 없음"""
        svc = self._make_service(session_data={"session_state": "start"}, profile_repo=None)
        from app.schemas.common import RealtimePersonalContextRequest

        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "44444444"})

        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()

        with patch("app.services.profile_service.get_redis_client"), patch(
            "app.services.profile_service.RedisHelper", return_value=mock_helper
        ):
            await svc.update_realtime_personal_context("gsess_test", req)

        mock_helper.set_batch_profile.assert_not_called()

    async def test_response_status_is_success(self):
        """TC-PROF-014: 정상 처리 시 응답 status == 'success'"""
        svc = self._make_service(session_data={"session_state": "start"})
        from app.schemas.common import RealtimePersonalContextRequest

        req = RealtimePersonalContextRequest(profile_data={"cusnoN10": "55555555"})

        mock_helper = MagicMock()
        mock_helper.set_realtime_profile = AsyncMock()
        mock_helper.set_batch_profile = AsyncMock()

        with patch("app.services.profile_service.get_redis_client"), patch(
            "app.services.profile_service.RedisHelper", return_value=mock_helper
        ):
            result = await svc.update_realtime_personal_context("gsess_test", req)

        self.assertEqual(result.status, "success")
        self.assertIsNotNone(result.updated_at)


if __name__ == "__main__":
    unittest.main()
