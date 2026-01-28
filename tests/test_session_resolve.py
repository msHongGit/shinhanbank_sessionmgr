"""세션 조회 테스트"""

import pytest


class TestSessionResolve:
    """세션 조회 테스트 - MA 주로 사용"""

    def test_resolve_session_success(self, client, agw_headers, ma_headers):
        """세션 조회 성공"""
        # 먼저 세션 생성
        create_req = {
            "userId": "0616001905",
            "channel": {
                "eventType": "ICON_ENTRY",
                "eventChannel": "web",
            },
        }
        print("[TEST] POST /api/v1/sessions 요청:", create_req)
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        print("[TEST] POST 응답:", create_resp.status_code, create_resp.json())
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 세션 조회
        print(f"[TEST] GET /api/v1/sessions/{global_session_key} 요청 (channel=web)")
        response = client.get(
            f"/api/v1/sessions/{global_session_key}",
            params={"channel": "web"},
            headers=ma_headers,
        )
        print("[TEST] GET 응답:", response.status_code, response.json())

        assert response.status_code == 200
        data = response.json()
        assert data["global_session_key"] == global_session_key
        assert data["channel"]["eventChannel"] == "web"
        assert data["channel"]["eventType"] == "ICON_ENTRY"
        assert data["session_state"] == "start"
        assert data["is_first_call"] is True
        # user_id는 응답에서 제외됨 (임시값이므로)
        assert "user_id" not in data
        # customer_profile은 None으로 반환됨 (통합 프로파일 제거)
        assert data.get("customer_profile") is None

    def test_resolve_session_not_found(self, client, ma_headers):
        """세션 없음"""
        print("[TEST] GET /api/v1/sessions/nonexistent_key 요청 (channel=web)")
        response = client.get(
            "/api/v1/sessions/nonexistent_key",
            params={"channel": "web"},
            headers=ma_headers,
        )
        print("[TEST] GET 응답:", response.status_code, response.json())
        assert response.status_code == 404
