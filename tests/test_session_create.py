"""세션 생성 테스트"""

import pytest


class TestSessionCreate:
    """세션 생성 테스트 - 모든 호출자 공통"""

    def test_create_session_success_with_agw(self, client, agw_headers):
        """AGW가 세션 생성"""
        request_data = {
            "userId": "0616001905",
        }
        print("[TEST] POST /api/v1/sessions 요청:", request_data)
        response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)
        print("[TEST] POST 응답:", response.status_code, response.json())
        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        # 응답에는 Global 세션 키, Access Token, Refresh Token, jti가 포함된다.
        assert "access_token" in data
        assert "refresh_token" in data
        assert "jti" in data
        assert set(data.keys()) == {"global_session_key", "access_token", "refresh_token", "jti"}

    def test_create_session_success_with_ma(self, client, ma_headers):
        """MA가 세션 생성 (인증 비활성화 상태에서 가능)"""
        request_data = {
            "userId": "user_002",
        }
        print("[TEST] POST /api/v1/sessions 요청:", request_data)
        response = client.post("/api/v1/sessions", json=request_data, headers=ma_headers)
        print("[TEST] POST 응답:", response.status_code, response.json())
        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        assert "access_token" in data
        assert "refresh_token" in data
        assert "jti" in data
        assert set(data.keys()) == {"global_session_key", "access_token", "refresh_token", "jti"}

    def test_create_session_without_profile(self, client, agw_headers):
        """프로파일 없는 사용자로 세션 생성"""
        request_data = {
            "userId": "user_no_profile",
        }
        print("[TEST] POST /api/v1/sessions 요청:", request_data)
        response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)
        print("[TEST] POST 응답:", response.status_code, response.json())
        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        assert "access_token" in data
        assert "refresh_token" in data
        assert "jti" in data
        assert set(data.keys()) == {"global_session_key", "access_token", "refresh_token", "jti"}

    def test_create_session_without_user_id(self, client, agw_headers):
        """userId 없이 세션 생성 (선택적 필드)"""
        request_data = {}
        print("[TEST] POST /api/v1/sessions 요청 (no userId):", request_data)
        response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)
        print("[TEST] POST 응답:", response.status_code, response.json())
        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        assert "access_token" in data
        assert "refresh_token" in data
        assert "jti" in data
        assert set(data.keys()) == {"global_session_key", "access_token", "refresh_token", "jti"}
