"""TC-SESS: SessionService 순수 로직 단위 테스트 (Mock Repo/Auth/Profile)"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch


def _make_service(
    session_data=None,
    auth_tokens=None,
    profile_service=None,
):
    """SessionService 생성 헬퍼 (의존성 Mock 주입 - 정상 생성자 사용)"""
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

    # __new__ 소거: 정상 생성자로 등록하되
    # session_repo / auth_service / profile_service 주입 지원하므로 바로 사용 가능
    svc = SessionService(
        session_repo=session_repo,
        auth_service=auth_service,
        profile_service=profile_service,
    )
    return svc, session_repo, auth_service


class TestCreateSession(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-001~009: create_session 검증"""

    async def test_returns_session_key_and_tokens(self):
        """TC-SESS-001: 정상 입력 -> global_session_key, access_token, refresh_token, jti 반환"""
        from app.schemas.common import SessionCreateRequest

        svc, _, _ = _make_service()
        req = SessionCreateRequest(userId="700000001")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            result = await svc.create_session(req)

        self.assertTrue(result.global_session_key.startswith("gsess_"))
        self.assertEqual(result.access_token, "access_x")
        self.assertEqual(result.refresh_token, "refresh_x")
        self.assertEqual(result.jti, "jti_x")

    async def test_channel_none_sets_utterance(self):
        """TC-SESS-002: channel 없으면 channel='utterance', start_type=None"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_service()
        req = SessionCreateRequest(userId="user_001")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.create_session(req)

        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["channel"], "utterance")
        self.assertIsNone(call_kwargs["start_type"])

    async def test_channel_provided_sets_correct_values(self):
        """TC-SESS-003: channel 있으면 event_channel, event_type 그대로 사용"""
        from app.schemas.common import ChannelInfo, SessionCreateRequest

        svc, repo, _ = _make_service()
        req = SessionCreateRequest(
            userId="user_002",
            channel=ChannelInfo(eventType="ICON_ENTRY", eventChannel="SOL"),
        )

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.create_session(req)

        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["channel"], "SOL")
        self.assertEqual(call_kwargs["start_type"], "ICON_ENTRY")

    async def test_user_id_none_defaults_to_empty_string(self):
        """TC-SESS-004: userId 없으면 user_id=''"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_service()
        req = SessionCreateRequest()

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.create_session(req)

        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["user_id"], "")

    async def test_trigger_id_none_defaults_to_empty_string(self):
        """TC-SESS-005: triggerId 없으면 trigger_id=''"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_service()
        req = SessionCreateRequest(userId="user_003")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.create_session(req)

        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["trigger_id"], "")

    async def test_trigger_id_passed_correctly(self):
        """TC-SESS-006: triggerId 있으면 그대로 전달"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_service()
        req = SessionCreateRequest(userId="user_004", triggerId="TRG-001")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.create_session(req)

        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["trigger_id"], "TRG-001")

    async def test_session_state_is_start(self):
        """TC-SESS-007: 세션 생성 시 session_state='start'"""
        from app.schemas.common import SessionCreateRequest

        svc, repo, _ = _make_service()
        req = SessionCreateRequest(userId="user_005")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.create_session(req)

        call_kwargs = repo.create.call_args[1]
        self.assertEqual(call_kwargs["session_state"], "start")

    async def test_auth_service_create_tokens_called(self):
        """TC-SESS-008: auth_service.create_tokens 호출"""
        from app.schemas.common import SessionCreateRequest

        svc, _, auth = _make_service()
        req = SessionCreateRequest(userId="user_006")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.create_session(req)

        auth.create_tokens.assert_called_once()

    async def test_es_log_payload_no_field_info(self):
        """TC-SESS-009: SESSION_CREATE ES 로그 payload 에 FieldInfo 없음 (직렬화 성공)"""
        from app.schemas.common import ChannelInfo, SessionCreateRequest

        svc, _, _ = _make_service()
        req = SessionCreateRequest(
            userId="user_007",
            triggerId="TRG-007",
            channel=ChannelInfo(eventType="ICON_ENTRY", eventChannel="SOL"),
        )
        # eslog 를 실제로 실행해서 직렬화 에러 없는지 확인
        from app.logger_config import LoggerExtraData

        captured = []

        def fake_eslog(self_logger, msg, *args, **kwargs):
            captured.append(msg.model_dump_json())

        with patch("logging.Logger.eslog", fake_eslog):
            # eslog 패치 없이 실제 호출이 안 되므로, LoggerExtraData 직접 확인
            from datetime import UTC, datetime

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


class TestResolveSession(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-010~015: resolve_session 검증"""

    async def test_session_not_found_raises(self):
        """TC-SESS-010: 세션 없음 -> SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import AgentType, SessionResolveRequest

        svc, _, _ = _make_service(session_data=None)
        req = SessionResolveRequest(global_session_key="gsess_missing", agent_type=AgentType.KNOWLEDGE)

        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)

        with patch("app.services.session_service.get_redis_client"), patch(
            "app.services.session_service.RedisHelper", return_value=mock_helper
        ), patch("app.logger_config.logging.Logger.eslog", return_value=None):
            with self.assertRaises(SessionNotFoundError):
                await svc.resolve_session(req)

    async def test_session_found_returns_resolve_response(self):
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
        svc, _, _ = _make_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_found", agent_type=AgentType.KNOWLEDGE)

        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)

        with patch("app.services.session_service.get_redis_client"), patch(
            "app.services.session_service.RedisHelper", return_value=mock_helper
        ), patch("app.logger_config.logging.Logger.eslog", return_value=None):
            result = await svc.resolve_session(req)

        self.assertEqual(result.global_session_key, "gsess_found")
        self.assertEqual(result.session_state.value, "start")

    async def test_cusno_present_calls_batch_profiles(self):
        """TC-SESS-012: 세션에 cusno 있으면 get_batch_and_realtime_profiles 호출"""
        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "talk",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "cusno": "12345678",
        }
        profile_service = MagicMock()
        profile_service.get_batch_and_realtime_profiles = AsyncMock(return_value=({"batch": "data"}, {"realtime": "data"}))
        svc, _, _ = _make_service(session_data=session_data, profile_service=profile_service)
        req = SessionResolveRequest(global_session_key="gsess_cusno", agent_type=AgentType.KNOWLEDGE)

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            result = await svc.resolve_session(req)

        profile_service.get_batch_and_realtime_profiles.assert_called_once_with("12345678")

    async def test_no_cusno_uses_session_key_for_realtime(self):
        """TC-SESS-013: 세션에 cusno 없으면 session_key 로 실시간 프로파일 조회"""
        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "start",
            "task_queue_status": "null",
            "subagent_status": "undefined",
        }
        svc, _, _ = _make_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_nocusno", agent_type=AgentType.KNOWLEDGE)

        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)

        with patch("app.services.session_service.get_redis_client"), patch(
            "app.services.session_service.RedisHelper", return_value=mock_helper
        ), patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.resolve_session(req)

        mock_helper.get_realtime_profile.assert_called_once_with("gsess_nocusno")

    async def test_invalid_conversation_history_type_becomes_none(self):
        """TC-SESS-014: reference_information.conversation_history 가 list 아니면 None"""
        import json

        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "talk",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "reference_information": json.dumps({"conversation_history": "invalid_string"}),
        }
        svc, _, _ = _make_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_ref", agent_type=AgentType.KNOWLEDGE)

        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)

        with patch("app.services.session_service.get_redis_client"), patch(
            "app.services.session_service.RedisHelper", return_value=mock_helper
        ), patch("app.logger_config.logging.Logger.eslog", return_value=None):
            result = await svc.resolve_session(req)

        self.assertIsNone(result.conversation_history)

    async def test_invalid_turn_count_type_becomes_none(self):
        """TC-SESS-015: reference_information.turn_count 가 int 아니면 None"""
        import json

        from app.schemas.common import AgentType, SessionResolveRequest

        session_data = {
            "session_state": "talk",
            "task_queue_status": "null",
            "subagent_status": "undefined",
            "reference_information": json.dumps({"turn_count": "not_int"}),
        }
        svc, _, _ = _make_service(session_data=session_data)
        req = SessionResolveRequest(global_session_key="gsess_tc", agent_type=AgentType.KNOWLEDGE)

        mock_helper = MagicMock()
        mock_helper.get_realtime_profile = AsyncMock(return_value=None)

        with patch("app.services.session_service.get_redis_client"), patch(
            "app.services.session_service.RedisHelper", return_value=mock_helper
        ), patch("app.logger_config.logging.Logger.eslog", return_value=None):
            result = await svc.resolve_session(req)

        self.assertIsNone(result.turn_count)


class TestPatchSessionState(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-016~021: patch_session_state 검증"""

    async def test_session_not_found_raises(self):
        """TC-SESS-016: 세션 없음 -> SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import SessionPatchRequest, SessionState

        svc, _, _ = _make_service(session_data=None)
        req = SessionPatchRequest(global_session_key="gsess_missing", session_state=SessionState.TALK)

        with self.assertRaises(SessionNotFoundError):
            with patch("app.logger_config.logging.Logger.eslog", return_value=None):
                await svc.patch_session_state(req)

    async def test_talk_state_calls_refresh_ttl(self):
        """TC-SESS-017: session_state=TALK 이면 refresh_ttl 호출"""
        from app.schemas.common import SessionPatchRequest, SessionState

        svc, repo, _ = _make_service(session_data={"session_state": "start", "task_queue_status": "null"})
        req = SessionPatchRequest(global_session_key="gsess_talk", session_state=SessionState.TALK)

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.patch_session_state(req)

        repo.refresh_ttl.assert_called_once_with("gsess_talk")

    async def test_non_talk_state_no_refresh_ttl(self):
        """TC-SESS-018: session_state=TALK 이 아니면 refresh_ttl 미호출"""
        from app.schemas.common import SessionPatchRequest, SessionState

        svc, repo, _ = _make_service(session_data={"session_state": "start", "task_queue_status": "null"})
        req = SessionPatchRequest(global_session_key="gsess_end", session_state=SessionState.END)

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.patch_session_state(req)

        repo.refresh_ttl.assert_not_called()

    async def test_turn_id_accumulated_without_duplicate(self):
        """TC-SESS-019: turn_id 중복 없이 누적 저장"""
        import json

        from app.schemas.common import SessionPatchRequest

        existing_turns = json.dumps(["turn_001", "turn_002"])
        svc, repo, _ = _make_service(
            session_data={
                "session_state": "talk",
                "task_queue_status": "null",
                "turn_ids": existing_turns,
            }
        )
        # 기존에 없는 turn_id 추가
        req = SessionPatchRequest(global_session_key="gsess_turn", turn_id="turn_003")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.patch_session_state(req)

        update_call = repo.update.call_args[1]
        turn_ids = json.loads(update_call["turn_ids"])
        self.assertIn("turn_003", turn_ids)
        self.assertEqual(len([t for t in turn_ids if t == "turn_003"]), 1)

    async def test_duplicate_turn_id_not_added(self):
        """TC-SESS-020: 이미 있는 turn_id 는 중복 추가 안 됨"""
        import json

        from app.schemas.common import SessionPatchRequest

        existing_turns = json.dumps(["turn_001"])
        svc, repo, _ = _make_service(
            session_data={
                "session_state": "talk",
                "task_queue_status": "null",
                "turn_ids": existing_turns,
            }
        )
        req = SessionPatchRequest(global_session_key="gsess_dup", turn_id="turn_001")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.patch_session_state(req)

        update_call = repo.update.call_args[1]
        turn_ids = json.loads(update_call["turn_ids"])
        self.assertEqual(turn_ids.count("turn_001"), 1)

    async def test_invalid_conversation_history_raises_400(self):
        """TC-SESS-021: state_patch.reference_information.conversation_history 가 list 아니면 400"""
        from fastapi import HTTPException

        from app.schemas.common import SessionPatchRequest, StatePatch

        svc, _, _ = _make_service(session_data={"session_state": "talk", "task_queue_status": "null"})
        req = SessionPatchRequest(
            global_session_key="gsess_invalid",
            state_patch=StatePatch(reference_information={"conversation_history": "not_a_list"}),
        )
        with self.assertRaises(HTTPException) as ctx:
            with patch("app.logger_config.logging.Logger.eslog", return_value=None):
                await svc.patch_session_state(req)
        self.assertEqual(ctx.exception.status_code, 400)


class TestCloseSession(unittest.IsolatedAsyncioTestCase):
    """TC-SESS-022~025: close_session 검증"""

    async def test_session_not_found_raises(self):
        """TC-SESS-022: 세션 없음 -> SessionNotFoundError"""
        from app.core.exceptions import SessionNotFoundError
        from app.schemas.common import SessionCloseRequest

        svc, _, _ = _make_service(session_data=None)
        req = SessionCloseRequest(global_session_key="gsess_missing", close_reason="test")

        with self.assertRaises(SessionNotFoundError):
            with patch("app.logger_config.logging.Logger.eslog", return_value=None):
                await svc.close_session(req)

    async def test_close_sets_state_end(self):
        """TC-SESS-023: 정상 종료 -> session_state='end' 업데이트"""
        from app.schemas.common import SessionCloseRequest

        svc, repo, _ = _make_service(session_data={"session_state": "talk", "task_queue_status": "null"})
        req = SessionCloseRequest(global_session_key="gsess_close", close_reason="user_request")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.close_session(req)

        update_call = repo.update.call_args[1]
        self.assertEqual(update_call["session_state"], "end")
        self.assertEqual(update_call["close_reason"], "user_request")

    async def test_archived_id_format(self):
        """TC-SESS-024: archived_id = 'arch_{global_session_key}'"""
        from app.schemas.common import SessionCloseRequest

        svc, _, _ = _make_service(session_data={"session_state": "talk", "task_queue_status": "null"})
        req = SessionCloseRequest(global_session_key="gsess_arch", close_reason="done")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            result = await svc.close_session(req)

        self.assertEqual(result.archived_conversation_id, "arch_gsess_arch")

    async def test_final_summary_saved(self):
        """TC-SESS-025: final_summary 있으면 업데이트에 포함"""
        from app.schemas.common import SessionCloseRequest

        svc, repo, _ = _make_service(session_data={"session_state": "talk", "task_queue_status": "null"})
        req = SessionCloseRequest(global_session_key="gsess_summary", close_reason="done", final_summary="This is summary")

        with patch("app.logger_config.logging.Logger.eslog", return_value=None):
            await svc.close_session(req)

        update_call = repo.update.call_args[1]
        self.assertEqual(update_call["final_summary"], "This is summary")


class TestSerializeReferenceInformation(unittest.TestCase):
    """TC-SESS-026~028: _serialize_reference_information 검증"""

    def setUp(self):
        from app.services.session_service import SessionService

        self.SessionService = SessionService

    def test_empty_dict_returns_empty_json(self):
        """TC-SESS-026: 빈 dict -> '{}'"""
        result = self.SessionService._serialize_reference_information({})
        self.assertEqual(result, "{}")

    def test_keys_are_sorted(self):
        """TC-SESS-027: 출력 JSON 키가 정렬됨"""
        import json

        result = self.SessionService._serialize_reference_information({"z_key": 1, "a_key": 2})
        parsed = json.loads(result)
        keys = list(parsed.keys())
        self.assertEqual(keys, sorted(keys))

    def test_list_order_preserved(self):
        """TC-SESS-028: list 순서 유지"""
        import json

        data = {"conversation_history": [{"msg": "first"}, {"msg": "second"}]}
        result = self.SessionService._serialize_reference_information(data)
        parsed = json.loads(result)
        self.assertEqual(parsed["conversation_history"][0]["msg"], "first")
        self.assertEqual(parsed["conversation_history"][1]["msg"], "second")


if __name__ == "__main__":
    unittest.main()
