"""세션 종료 테스트"""

import pytest


class TestSessionClose:
    """세션 종료 테스트"""

    def test_close_session_by_key(self, client, agw_headers, ma_headers):
        """세션 종료 (Master Agent용, global_session_key 경로 사용)"""
        # 세션 생성
        create_req = {
            "userId": "user_close_001",
        }
        print("[TEST] POST /api/v1/sessions 요청:", create_req)
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        print("[TEST] POST 응답:", create_resp.status_code, create_resp.json())
        assert create_resp.status_code == 201
        session = create_resp.json()

        # 세션 종료 (기존 방식, MA용)
        print(f"[TEST] DELETE /api/v1/sessions/{session['global_session_key']} 요청 (close_reason=test_completed)")
        response = client.delete(
            f"/api/v1/sessions/{session['global_session_key']}",
            params={
                "close_reason": "test_completed",
            },
            headers=ma_headers,
        )
        print("[TEST] DELETE 응답:", response.status_code, response.json())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_close_session_by_token(self, client, session_with_tokens):
        """세션 종료 (토큰 기반)"""
        tokens = session_with_tokens
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = client.delete(
            "/api/v1/sessions",
            params={"close_reason": "test_completed"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_close_session_by_token_from_cookie(self, client, session_with_tokens):
        """쿠키에서 Access Token 추출하여 세션 종료"""
        tokens = session_with_tokens
        client.cookies.set("access_token", tokens["access_token"])

        response = client.delete("/api/v1/sessions", params={"close_reason": "test_completed"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
