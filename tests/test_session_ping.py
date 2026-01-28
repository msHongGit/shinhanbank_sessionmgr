"""세션 Ping 테스트"""

import pytest


class TestSessionPing:
    """세션 Ping 테스트 (토큰 기반)"""

    def test_ping_session_with_token(self, client, session_with_tokens):
        """토큰 기반 세션 Ping"""
        tokens = session_with_tokens
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = client.get("/api/v1/sessions/ping", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert "is_alive" in data
        assert data["is_alive"] is True
        assert "expires_at" in data
        # global_session_key는 응답에 포함되지 않음
        assert "global_session_key" not in data

    def test_ping_session_invalid_token(self, client):
        """유효하지 않은 토큰으로 Ping"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/sessions/ping", headers=headers)
        assert response.status_code == 401

    def test_ping_session_from_cookie(self, client, session_with_tokens):
        """쿠키에서 Access Token 추출하여 Ping"""
        tokens = session_with_tokens
        client.cookies.set("access_token", tokens["access_token"])

        response = client.get("/api/v1/sessions/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["is_alive"] is True
