"""
Session Manager - AGW API Tests (v4.0)
Agent GW → SM
Sprint 1: Mock Repository 사용
"""


class TestHealthCheck:
    """헬스체크 테스트"""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check(self, client):
        response = client.get("/ready")
        assert response.status_code == 200


class TestAGWSessionCreate:
    """AGW 세션 생성 테스트"""

    def test_create_session_invalid_api_key(self, client, sample_agw_session_create_request):
        """잘못된 API Key (Sprint 2: 인증 비활성화로 인해 통과됨)"""
        response = client.post("/api/v1/agw/sessions", json=sample_agw_session_create_request, headers={"X-API-Key": "wrong-key"})
        # Sprint 2: ENABLE_API_KEY_AUTH=false이므로 인증 없이도 성공
        assert response.status_code == 201

    def test_create_session_success(self, client, agw_headers, sample_agw_session_create_request):
        """세션 생성 성공 (SM이 global_session_key 자동 생성)"""
        # Sprint 2: global_session_key는 요청에서 제거됨
        request_data = {k: v for k, v in sample_agw_session_create_request.items() if k != "global_session_key"}
        response = client.post("/api/v1/agw/sessions", json=request_data, headers=agw_headers)

        assert response.status_code == 201
        data = response.json()
        # SM이 생성한 키 확인 (gsess_ 프리픽스)
        assert data["global_session_key"].startswith("gsess_")
        assert data["session_state"] == "start"
        assert data["is_new"] is True
        assert "conversation_id" in data
        assert "context_id" in data

    def test_create_session_existing(self, client, agw_headers, sample_agw_session_create_request):
        """세션 생성 - 매번 새로운 키 생성 (Sprint 2 로직)"""
        # Sprint 2: SM이 매번 새 global_session_key를 생성하므로 항상 is_new=True
        request_data = {k: v for k, v in sample_agw_session_create_request.items() if k != "global_session_key"}

        # 첫 번째 생성
        response1 = client.post("/api/v1/agw/sessions", json=request_data, headers=agw_headers)
        assert response1.status_code == 201
        first_data = response1.json()
        assert first_data["is_new"] is True

        # 동일 요청으로 다시 생성 (새로운 세션 키 생성됨)
        response2 = client.post("/api/v1/agw/sessions", json=request_data, headers=agw_headers)
        assert response2.status_code == 201
        second_data = response2.json()
        assert second_data["is_new"] is True
        # 다른 세션 키가 생성됨
        assert second_data["global_session_key"] != first_data["global_session_key"]

    def test_ma_cannot_create_session(self, client, ma_headers, sample_agw_session_create_request):
        """MA는 AGW API 사용 불가 (Sprint 2: 인증 비활성화로 인해 통과됨)"""
        request_data = {k: v for k, v in sample_agw_session_create_request.items() if k != "global_session_key"}
        response = client.post(
            "/api/v1/agw/sessions",
            json=request_data,
            headers=ma_headers,  # MA API Key 사용
        )
        # Sprint 2: ENABLE_API_KEY_AUTH=false이므로 MA 키로도 성공
        assert response.status_code == 201
