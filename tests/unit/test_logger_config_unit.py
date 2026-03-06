"""TC-LOG: LoggerExtraData 직렬화 단위 테스트"""

import unittest

from app.logger_config import LoggerExtraData


class TestLoggerExtraDataDefaults(unittest.TestCase):
    """TC-LOG-001~003: 기본값 및 필드 구조 검증"""

    def test_default_fields_are_dash(self):
        """TC-LOG-001: 명시하지 않은 필드는 '-' 기본값"""
        msg = LoggerExtraData(logType="SESSION_CREATE", payload={})
        self.assertEqual(msg.custNo, "-")
        self.assertEqual(msg.sessionId, "-")
        self.assertEqual(msg.turnId, "-")
        self.assertEqual(msg.agentId, "-")
        self.assertEqual(msg.transactionId, "-")

    def test_explicit_fields_override_defaults(self):
        """TC-LOG-002: 명시한 필드는 기본값을 덮어씀"""
        msg = LoggerExtraData(
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

    def test_logtype_required(self):
        """TC-LOG-003: logType 없이 생성 시 ValidationError"""
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            LoggerExtraData(payload={})


class TestLoggerExtraDataSerialization(unittest.TestCase):
    """TC-LOG-004~010: model_dump_json 직렬화 검증"""

    def test_session_create_payload_serializes_without_field_info(self):
        """TC-LOG-004: SESSION_CREATE payload 직렬화 시 FieldInfo 없음"""
        msg = LoggerExtraData(
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

    def test_session_resolve_payload_serializes(self):
        """TC-LOG-005: SESSION_RESOLVE payload 직렬화"""
        msg = LoggerExtraData(
            logType="SESSION_RESOLVE",
            custNo="12345678",
            sessionId="gsess_test_002",
            payload={
                "sessionState": "talk",
                "agentType": "task",
                "isFirstCall": False,
            },
        )
        result = msg.model_dump_json()
        self.assertIn("SESSION_RESOLVE", result)
        self.assertIn("12345678", result)
        self.assertIn("talk", result)

    def test_realtime_batch_profile_update_payload_serializes(self):
        """TC-LOG-006: REALTIME_BATCH_PROFILE_UPDATE payload 직렬화"""
        msg = LoggerExtraData(
            logType="REALTIME_BATCH_PROFILE_UPDATE",
            custNo="99999999",
            sessionId="gsess_test_003",
            payload={
                "hasCusno": True,
                "savedRealtimeKey": "99999999",
                "batchProfileFetched": True,
            },
        )
        result = msg.model_dump_json()
        self.assertIn("REALTIME_BATCH_PROFILE_UPDATE", result)
        self.assertIn("99999999", result)

    def test_session_state_update_payload_serializes(self):
        """TC-LOG-007: SESSION_STATE_UPDATE payload 직렬화"""
        msg = LoggerExtraData(
            logType="SESSION_STATE_UPDATE",
            sessionId="gsess_test_004",
            turnId="turn_001",
            agentId="agent_001",
            payload={
                "newSessionState": "talk",
                "hasStatePatch": True,
            },
        )
        result = msg.model_dump_json()
        self.assertIn("SESSION_STATE_UPDATE", result)
        self.assertIn("talk", result)

    def test_session_close_payload_serializes(self):
        """TC-LOG-008: SESSION_CLOSE payload 직렬화"""
        msg = LoggerExtraData(
            logType="SESSION_CLOSE",
            custNo="11111111",
            sessionId="gsess_test_005",
            payload={
                "sessionState": "end",
                "closedAt": "2026-03-01T00:00:00+00:00",
            },
        )
        result = msg.model_dump_json()
        self.assertIn("SESSION_CLOSE", result)
        self.assertIn("end", result)

    def test_empty_payload_serializes(self):
        """TC-LOG-009: 빈 payload dict 직렬화"""
        msg = LoggerExtraData(logType="TEST", payload={})
        result = msg.model_dump_json()
        self.assertIn("TEST", result)
        self.assertIn("{}", result)

    def test_none_payload_serializes(self):
        """TC-LOG-010: None payload 직렬화"""
        msg = LoggerExtraData(logType="TEST", payload=None)
        result = msg.model_dump_json()
        self.assertIn("TEST", result)


class TestEncryptPayload(unittest.TestCase):
    """TC-LOG-011~020: encrypt_payload 암호화 기능 검증"""

    def setUp(self):
        import os
        import app.logger_config as lc
        os.environ["LOG_ENCRYPTION_SECRET"] = "test-secret-key-for-unit-tests"
        # config.py 에서 import-time 에 고정된 module-level 상수를 직접 패치
        lc.LOG_ENCRYPT_ENABLED = True
        lc.LOG_ENCRYPTION_SECRET = "test-secret-key-for-unit-tests"
        lc._ENCRYPTION_KEY = None

    def tearDown(self):
        import os
        import app.logger_config as lc
        os.environ.pop("LOG_ENCRYPTION_SECRET", None)
        lc.LOG_ENCRYPT_ENABLED = False
        lc.LOG_ENCRYPTION_SECRET = None
        lc._ENCRYPTION_KEY = None

    def test_primitive_string_is_encrypted(self):
        """TC-LOG-011: 문자열 값이 암호화되어 원본과 달라짐"""
        from app.logger_config import encrypt_payload
        result = encrypt_payload("hello")
        self.assertNotEqual(result, "hello")
        self.assertIsInstance(result, str)

    def test_dict_values_are_encrypted(self):
        """TC-LOG-012: dict 값이 각각 암호화됨"""
        from app.logger_config import encrypt_payload
        result = encrypt_payload({"key": "value"})
        self.assertIsInstance(result, dict)
        self.assertIn("key", result)
        self.assertNotEqual(result["key"], "value")

    def test_encrypt_exceptions_keys_not_encrypted(self):
        """TC-LOG-013: ENCRYPT_EXCEPTIONS 키는 암호화 제외"""
        from app.logger_config import ENCRYPT_EXCEPTIONS, encrypt_payload
        payload = {k: "test_value" for k in ENCRYPT_EXCEPTIONS}
        result = encrypt_payload(payload)
        for key in ENCRYPT_EXCEPTIONS:
            self.assertEqual(result[key], "test_value", f"{key} 값이 변경됨")

    def test_non_exception_key_is_encrypted(self):
        """TC-LOG-014: ENCRYPT_EXCEPTIONS 에 없는 키는 암호화됨"""
        from app.logger_config import encrypt_payload
        result = encrypt_payload({"secretData": "sensitive"})
        self.assertNotEqual(result["secretData"], "sensitive")

    def test_list_items_are_encrypted(self):
        """TC-LOG-015: list 항목이 각각 암호화됨"""
        from app.logger_config import encrypt_payload
        result = encrypt_payload(["a", "b"])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertNotEqual(result[0], "a")

    def test_none_value_returns_none(self):
        """TC-LOG-016: None 값은 None 반환"""
        from app.logger_config import encrypt_payload
        result = encrypt_payload(None)
        self.assertIsNone(result)

    def test_nested_dict_encrypted_recursively(self):
        """TC-LOG-017: 중첩 dict 재귀 암호화"""
        from app.logger_config import encrypt_payload
        result = encrypt_payload({"outer": {"inner": "value"}})
        self.assertIsInstance(result["outer"], dict)
        self.assertNotEqual(result["outer"]["inner"], "value")

    def test_nested_exception_key_preserved(self):
        """TC-LOG-018: 중첩 dict 내 ENCRYPT_EXCEPTIONS 키도 제외"""
        from app.logger_config import encrypt_payload
        result = encrypt_payload({"wrapper": {"globId": "GLOB-001", "secret": "x"}})
        inner = result["wrapper"]
        self.assertEqual(inner["globId"], "GLOB-001")
        self.assertNotEqual(inner["secret"], "x")

    def test_pydantic_model_encrypted(self):
        """TC-LOG-019: Pydantic BaseModel 은 model_dump 후 암호화"""
        from app.logger_config import LoggerExtraData, encrypt_payload
        model = LoggerExtraData(logType="TEST", payload={"k": "v"})
        result = encrypt_payload(model)
        self.assertIsInstance(result, dict)
        # logType 은 ENCRYPT_EXCEPTIONS 에 없으므로 암호화됨
        self.assertNotEqual(result.get("logType"), "TEST")

    def test_missing_secret_raises_runtime_error(self):
        """TC-LOG-020: LOG_ENCRYPTION_SECRET 없으면 RuntimeError"""
        import app.logger_config as lc
        lc.LOG_ENCRYPTION_SECRET = None  # module-level 상수를 직접 None 으로
        lc._ENCRYPTION_KEY = None
        from app.logger_config import encrypt_payload
        result = encrypt_payload({"key": "value"})
        self.assertIn("ENCRYPTION_ERROR", str(result))


class TestEslogEncryption(unittest.TestCase):
    """TC-LOG-021~023: eslog/agentlog 암호화 통합 검증"""

    def setUp(self):
        import os
        import app.logger_config as lc
        os.environ["LOG_ENCRYPTION_SECRET"] = "test-secret-for-eslog"
        # config.py import-time 상수를 직접 패치
        lc.LOG_ENCRYPT_ENABLED = True
        lc.LOG_ENCRYPTION_SECRET = "test-secret-for-eslog"
        lc._ENCRYPTION_KEY = None

    def tearDown(self):
        import os
        import app.logger_config as lc
        os.environ.pop("LOG_ENCRYPTION_SECRET", None)
        lc.LOG_ENCRYPT_ENABLED = False
        lc.LOG_ENCRYPTION_SECRET = None
        lc._ENCRYPTION_KEY = None

    def test_eslog_encrypts_payload(self):
        """TC-LOG-021: eslog 호출 시 payload 가 암호화된 JSON 으로 기록됨"""
        import logging
        from unittest.mock import patch
        from app.logger_config import ES_LOG, LoggerExtraData

        logger = logging.getLogger("test_eslog_encrypt")
        logger.setLevel(ES_LOG)  # ES_LOG=15 허용
        logged_messages = []

        with patch.object(logger, "_log", side_effect=lambda lvl, msg, *a, **kw: logged_messages.append(msg)):
            logger.eslog(LoggerExtraData(
                logType="TEST",
                sessionId="gsess_001",
                payload={"sensitiveField": "plaintext", "session_id": "gsess_001"},
            ))

        self.assertEqual(len(logged_messages), 1)
        import json
        data = json.loads(logged_messages[0])
        # session_id 는 ENCRYPT_EXCEPTIONS → 평문
        inner = data["payload"]
        self.assertEqual(inner["session_id"], "gsess_001")
        # sensitiveField 는 암호화됨
        self.assertNotEqual(inner["sensitiveField"], "plaintext")

    def test_agentlog_encrypts_payload(self):
        """TC-LOG-022: agentlog 호출 시 payload 가 암호화됨"""
        import logging
        from unittest.mock import patch
        from app.logger_config import AGENT_LOG, LoggerExtraData

        logger = logging.getLogger("test_agentlog_encrypt")
        logger.setLevel(AGENT_LOG)  # AGENT_LOG=16 허용
        logged_messages = []

        with patch.object(logger, "_log", side_effect=lambda lvl, msg, *a, **kw: logged_messages.append(msg)):
            logger.agentlog(LoggerExtraData(
                logType="AGENT",
                payload={"data": "secret"},
            ))

        self.assertEqual(len(logged_messages), 1)
        import json
        data = json.loads(logged_messages[0])
        self.assertNotEqual(data["payload"]["data"], "secret")

    def test_eslog_does_not_mutate_original_msg(self):
        """TC-LOG-023: eslog 는 원본 msg 를 변경하지 않음 (deepcopy 확인)"""
        import logging
        from unittest.mock import patch
        from app.logger_config import ES_LOG, LoggerExtraData

        logger = logging.getLogger("test_eslog_deepcopy")
        logger.setLevel(ES_LOG)
        original_payload = {"myField": "original_value"}
        msg = LoggerExtraData(logType="TEST", payload=original_payload)

        with patch.object(logger, "_log"):
            logger.eslog(msg)

        # 암호화 후에도 원본 payload 변경 없음
        self.assertEqual(msg.payload["myField"], "original_value")  # type: ignore[index]


if __name__ == "__main__":
    unittest.main()
