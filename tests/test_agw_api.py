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
        """잘못된 API Key"""
        response = client.post(
            "/api/v1/agw/sessions",
            json=sample_agw_session_create_request,
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_create_session_success(self, client, agw_headers, sample_agw_session_create_request):
        """세션 생성 성공"""
        response = client.post(
            "/api/v1/agw/sessions",
            json=sample_agw_session_create_request,
            headers=agw_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"] == sample_agw_session_create_request["global_session_key"]
        assert data["session_state"] == "start"
        assert data["is_new"] is True
        assert "conversation_id" in data
        assert "context_id" in data

    def test_create_session_existing(self, client, agw_headers, sample_agw_session_create_request):
        """기존 세션 반환"""
        # 첫 번째 생성
        response1 = client.post(
            "/api/v1/agw/sessions",
            json=sample_agw_session_create_request,
            headers=agw_headers
        )
        assert response1.status_code == 201
        first_data = response1.json()
        assert first_data["is_new"] is True

        # 동일 세션 키로 다시 요청 (기존 세션 반환)
        response2 = client.post(
            "/api/v1/agw/sessions",
            json=sample_agw_session_create_request,
            headers=agw_headers
        )

        assert response2.status_code == 201
        data = response2.json()
        assert data["is_new"] is False
        # 기존 세션 정보 유지 확인
        assert data["conversation_id"] == first_data["conversation_id"]

    def test_ma_cannot_create_session(self, client, ma_headers, sample_agw_session_create_request):
        """MA는 AGW API 사용 불가"""
        response = client.post(
            "/api/v1/agw/sessions",
            json=sample_agw_session_create_request,
            headers=ma_headers  # MA API Key 사용
        )
        assert response.status_code == 401
