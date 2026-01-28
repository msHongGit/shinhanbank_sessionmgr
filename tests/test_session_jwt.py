"""JWT 토큰 검증 및 갱신 테스트"""

import pytest


class TestJWTTokenVerification:
    """JWT 토큰 검증 및 갱신 테스트"""

    def test_verify_token_and_get_session(self, client, session_with_tokens):
        """토큰 검증 및 세션 정보 조회"""
        tokens = session_with_tokens
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        response = client.get("/api/v1/sessions/verify", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["global_session_key"] == tokens["global_session_key"]
        assert data["is_alive"] is True
        assert "session_state" in data
        assert "expires_at" in data
        # user_id는 응답에서 제외됨 (임시값이므로)
        assert "user_id" not in data

    def test_verify_token_invalid(self, client):
        """유효하지 않은 토큰 검증"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/sessions/verify", headers=headers)
        assert response.status_code == 401

    def test_verify_token_missing(self, client):
        """토큰 없이 검증 요청"""
        response = client.get("/api/v1/sessions/verify")
        assert response.status_code == 401

    def test_refresh_token(self, client, session_with_tokens):
        """토큰 갱신"""
        tokens = session_with_tokens
        headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}

        response = client.post("/api/v1/sessions/refresh", headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["global_session_key"] == tokens["global_session_key"]
        # Refresh Token Rotation으로 새 jti가 생성됨
        assert data["jti"] != tokens["jti"]
        # 새 토큰이 발급되었는지 확인
        assert data["access_token"] != tokens["access_token"]
        assert data["refresh_token"] != tokens["refresh_token"]

    def test_refresh_token_from_cookie(self, client, session_with_tokens):
        """쿠키에서 Refresh Token 추출하여 갱신"""
        tokens = session_with_tokens
        client.cookies.set("refresh_token", tokens["refresh_token"])

        response = client.post("/api/v1/sessions/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
