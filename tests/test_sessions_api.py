"""
Session Manager - Sessions API Tests (통합 API)
모든 호출자(AGW, MA, CLIENT 등)가 사용하는 통합 API 테스트
"""


class TestHealthCheck:
    """헬스체크 테스트"""

    def test_health_check(self, client):
        """헬스체크"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check(self, client):
        """레디니스 체크"""
        response = client.get("/")
        assert response.status_code == 200


class TestSessionCreate:
    """세션 생성 테스트 - 모든 호출자 공통"""

    def test_create_session_success_with_agw(self, client, agw_headers):
        """AGW가 세션 생성 - 프로파일 자동 조회 (MariaDB context_db에서)"""
        request_data = {
            "user_id": "user_vip_001",  # MockProfileRepository에 존재하는 사용자
            "channel": "web",
            "request_id": "req_test_001",
        }
        response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        assert data["session_state"] == "start"
        assert data["is_new"] is True
        assert "context_id" in data
        assert "customer_profile" in data
        # MockProfileRepository에서 자동 조회된 프로파일
        assert data["customer_profile"]["user_id"] == "user_vip_001"
        assert "attributes" in data["customer_profile"]

    def test_create_session_success_with_ma(self, client, ma_headers):
        """MA가 세션 생성 (인증 비활성화 상태에서 가능)"""
        request_data = {
            "user_id": "user_002",
            "channel": "mobile",
            "request_id": "req_test_002",
        }
        response = client.post("/api/v1/sessions", json=request_data, headers=ma_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        assert data["is_new"] is True

    def test_create_session_without_profile(self, client, agw_headers):
        """프로파일 없는 사용자로 세션 생성"""
        request_data = {
            "user_id": "user_no_profile",  # MockProfileRepository에 없는 사용자
            "channel": "web",
            "request_id": "req_test_003",
        }
        response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        # customer_profile은 None
        assert data["customer_profile"] is None


class TestSessionResolve:
    """세션 조회 테스트 - MA 주로 사용"""

    def test_resolve_session_success(self, client, agw_headers, ma_headers):
        """세션 조회 성공"""
        # 먼저 세션 생성
        create_req = {
            "user_id": "user_vip_001",  # MockProfileRepository에 존재
            "channel": "web",
            "request_id": "req_resolve_001",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 세션 조회
        response = client.get(
            f"/api/v1/sessions/{global_session_key}",
            params={"channel": "web"},
            headers=ma_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["global_session_key"] == global_session_key
        assert data["session_state"] == "start"
        assert data["is_first_call"] is True
        assert "customer_profile" in data
        assert data["customer_profile"]["user_id"] == "user_vip_001"

    def test_resolve_session_not_found(self, client, ma_headers):
        """세션 없음"""
        response = client.get(
            "/api/v1/sessions/nonexistent_key",
            params={"channel": "web"},
            headers=ma_headers,
        )

        assert response.status_code == 404


class TestSessionStatePatch:
    """세션 상태 업데이트 테스트"""

    def test_patch_session_state(self, client, agw_headers, ma_headers):
        """세션 상태 업데이트"""
        # 세션 생성
        create_req = {
            "user_id": "user_patch_001",
            "channel": "web",
            "request_id": "req_patch_001",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        session = create_resp.json()

        # 상태 업데이트
        patch_req = {
            "global_session_key": session["global_session_key"],
            "conversation_id": "conv_patch_001",
            "turn_id": "turn_001",
            "session_state": "talk",
            "state_patch": {
                "subagent_status": "continue",
                "agent_session_key": "asess_transfer_001",
                "last_agent_id": "transfer_agent",
                "last_agent_type": "task",
            },
        }
        response = client.patch(
            f"/api/v1/sessions/{session['global_session_key']}/state",
            json=patch_req,
            headers=ma_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # 업데이트 후 세션 조회 시 agent_session_key가 매핑되어야 함
        resolve_resp = client.get(
            f"/api/v1/sessions/{session['global_session_key']}",
            params={"channel": "web", "agent_type": "task", "agent_id": "transfer_agent"},
            headers=ma_headers,
        )

        assert resolve_resp.status_code == 200
        resolved = resolve_resp.json()
        assert resolved["agent_session_key"] == "asess_transfer_001"


class TestSessionClose:
    """세션 종료 테스트"""

    def test_close_session(self, client, agw_headers, ma_headers):
        """세션 종료"""
        # 세션 생성
        create_req = {
            "user_id": "user_close_001",
            "channel": "web",
            "request_id": "req_close_001",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        session = create_resp.json()

        # 세션 종료
        response = client.delete(
            f"/api/v1/sessions/{session['global_session_key']}",
            params={
                "conversation_id": "conv_close_001",
                "close_reason": "test_completed",
            },
            headers=ma_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
