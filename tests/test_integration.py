"""
Session Manager - Integration Tests (v4.0)
E2E 통합 테스트
Sprint 1: Mock Repository 사용
"""


class TestSessionLifecycle:
    """세션 전체 라이프사이클 테스트"""

    def test_full_session_lifecycle(self, client, agw_headers, ma_headers):
        """세션 생성 → 조회 → 업데이트 → 종료"""
        # 1. 세션 생성 (AGW)
        create_req = {
            "global_session_key": "integration_test_session",
            "user_id": "user_int_test",
            "channel": "mobile",
            "request_id": "req_int_001"
        }
        create_resp = client.post(
            "/api/v1/agw/sessions",
            json=create_req,
            headers=agw_headers
        )
        assert create_resp.status_code == 201
        session = create_resp.json()
        assert session["is_new"] is True

        # 2. 세션 조회 (MA)
        resolve_resp = client.get(
            "/api/v1/ma/sessions/resolve",
            params={
                "global_session_key": create_req["global_session_key"],
                "channel": "mobile"
            },
            headers=ma_headers
        )
        assert resolve_resp.status_code == 200
        resolved = resolve_resp.json()
        assert resolved["session_state"] == "start"

        # 3. 세션 상태 업데이트 (MA)
        patch_req = {
            "global_session_key": create_req["global_session_key"],
            "conversation_id": session["conversation_id"],
            "turn_id": "turn_001",
            "session_state": "talk",
            "state_patch": {
                "subagent_status": "continue"
            }
        }
        patch_resp = client.patch(
            "/api/v1/ma/sessions/state",
            json=patch_req,
            headers=ma_headers
        )
        assert patch_resp.status_code == 200

        # 4. 세션 종료 (MA)
        close_req = {
            "global_session_key": create_req["global_session_key"],
            "conversation_id": session["conversation_id"],
            "close_reason": "test_completed"
        }
        close_resp = client.post(
            "/api/v1/ma/sessions/close",
            json=close_req,
            headers=ma_headers
        )
        assert close_resp.status_code == 200
        closed = close_resp.json()
        assert closed["status"] == "success"
