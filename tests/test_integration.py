"""
Session Manager - Integration Tests (v4.0)
E2E 통합 테스트
Sprint 1: Mock Repository 사용
"""


class TestSessionLifecycle:
    """세션 전체 라이프사이클 테스트"""

    def test_full_session_lifecycle(self, client, agw_headers, ma_headers):
        """세션 생성 → 조회 → 업데이트 → 종료"""
        # 1. 세션 생성 (AGW) - SM이 global_session_key 자동 생성
        create_req = {
            "user_id": "user_int_test",
            "channel": "mobile",
            "request_id": "req_int_001",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        session = create_resp.json()
        # 세션 생성 응답은 Global 세션 키만 포함
        assert set(session.keys()) == {"global_session_key"}
        global_session_key = session["global_session_key"]

        # 2. 세션 조회 (MA)
        resolve_resp = client.get(
            f"/api/v1/sessions/{global_session_key}",
            params={"agent_type": "knowledge"},
            headers=ma_headers,
        )
        assert resolve_resp.status_code == 200
        resolved = resolve_resp.json()
        assert resolved["session_state"] == "start"

        # 3. 세션 상태 업데이트 (MA)
        patch_req = {
            "global_session_key": global_session_key,
            "turn_id": "turn_001",
            "session_state": "talk",
            "state_patch": {
                "subagent_status": "continue",
                "task_queue_status": "null",
            },
        }
        patch_resp = client.patch(f"/api/v1/sessions/{global_session_key}/state", json=patch_req, headers=ma_headers)
        assert patch_resp.status_code == 200

        # 4. 세션 종료 (MA)
        close_resp = client.delete(
            f"/api/v1/sessions/{global_session_key}",
            params={
                "close_reason": "test_completed",
            },
            headers=ma_headers,
        )
        assert close_resp.status_code == 200
        closed = close_resp.json()
        assert closed["status"] == "success"
