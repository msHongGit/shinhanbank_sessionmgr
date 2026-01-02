"""
Session Manager - MA API Tests (v4.0)
MA → SM
Sprint 1: Mock Repository 사용
"""


class TestMASessionResolve:
    """MA 세션 조회 테스트"""

    def test_resolve_session_success(self, client, agw_headers, ma_headers, sample_agw_session_create_request):
        """세션 조회 성공 (SM이 생성한 키 사용)"""
        # 먼저 AGW로 세션 생성 - SM이 global_session_key 자동 생성
        request_data = {k: v for k, v in sample_agw_session_create_request.items() if k != "global_session_key"}
        create_response = client.post("/api/v1/agw/sessions", json=request_data, headers=agw_headers)
        assert create_response.status_code == 201
        created_session = create_response.json()
        global_session_key = created_session["global_session_key"]

        # MA로 세션 조회
        response = client.get(
            "/api/v1/ma/sessions/resolve",
            params={"global_session_key": global_session_key, "agent_type": "knowledge"},
            headers=ma_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["global_session_key"] == global_session_key
        assert data["session_state"] == "start"
        assert data["is_first_call"] is True

    def test_resolve_session_not_found(self, client, ma_headers):
        """세션 없음"""
        response = client.get(
            "/api/v1/ma/sessions/resolve", params={"global_session_key": "nonexistent_session_key", "channel": "mobile"}, headers=ma_headers
        )

        assert response.status_code == 404


class TestMAProfile:
    """MA 프로파일 테스트"""

    def test_get_customer_profile(self, client, ma_headers):
        """고객 프로파일 조회"""
        response = client.get("/api/v1/ma/profiles/user123", headers=ma_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user123"
        assert "profile" in data
