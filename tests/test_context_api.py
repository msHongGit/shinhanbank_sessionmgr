"""
Session Manager - Context & Turn API Tests (Sprint 3)
대화 컨텍스트 및 턴 관리 API 테스트
"""

from datetime import UTC, datetime


class TestContextManagement:
    """컨텍스트 관리 테스트"""

    def test_create_context(self, client, agw_headers):
        """컨텍스트 생성"""
        # 먼저 세션 생성
        session_req = {
            "user_id": "user_ctx_001",
            "channel": "web",
            "request_id": "req_ctx_001",
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        assert session_resp.status_code == 201
        context_id = session_resp.json()["context_id"]

        # 컨텍스트는 세션 생성 시 자동 생성됨
        # 조회로 확인
        response = client.get(f"/api/v1/contexts/{context_id}", headers=agw_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["context_id"] == context_id

    def test_get_context(self, client, agw_headers):
        """컨텍스트 조회"""
        # 세션 생성
        session_req = {
            "user_id": "user_ctx_002",
            "channel": "web",
            "request_id": "req_ctx_002",
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        context_id = session_resp.json()["context_id"]

        # 컨텍스트 조회
        response = client.get(f"/api/v1/contexts/{context_id}", headers=agw_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["context_id"] == context_id
        assert "global_session_key" in data

    def test_update_context(self, client, agw_headers):
        """컨텍스트 업데이트"""
        # 세션 생성
        session_req = {
            "user_id": "user_ctx_003",
            "channel": "web",
            "request_id": "req_ctx_003",
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        context_id = session_resp.json()["context_id"]

        # 컨텍스트 업데이트
        update_req = {
            "summary": "Updated context summary",
        }
        response = client.patch(f"/api/v1/contexts/{context_id}", json=update_req, headers=agw_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["context_id"] == context_id


class TestTurnManagement:
    """턴 관리 테스트"""

    def test_create_turn(self, client, agw_headers, ma_headers):
        """턴 생성"""
        # 세션 생성
        session_req = {
            "user_id": "user_turn_001",
            "channel": "web",
            "request_id": "req_turn_001",
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        context_id = session_resp.json()["context_id"]

        # 턴 생성 (메타데이터 전용)
        turn_req = {
            "turn_id": "turn_001",
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": {
                "event_type": "USER_MESSAGE",
                "channel": "web",
            },
        }
        response = client.post(f"/api/v1/contexts/{context_id}/turns", json=turn_req, headers=ma_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["turn_id"] == "turn_001"

    def test_create_turn_with_api_call(self, client, agw_headers, ma_headers):
        """API 호출 결과 포함 턴 생성"""
        # 세션 생성
        session_req = {
            "user_id": "user_turn_002",
            "channel": "web",
            "request_id": "req_turn_002",
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        context_id = session_resp.json()["context_id"]

        # API 호출 정보 포함 턴 생성 (텍스트 제외, 메타데이터만)
        turn_req = {
            "turn_id": "turn_002",
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": {
                "api_call": {
                    "api_name": "get_account_balance",
                    "request": {"account_id": "1234567890"},
                    "response": {"balance": 1000000},
                    "status_code": 200,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            },
        }
        response = client.post(f"/api/v1/contexts/{context_id}/turns", json=turn_req, headers=ma_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["turn_id"] == "turn_002"
        assert "metadata" in data
        assert "api_call" in data["metadata"]

    def test_list_turns(self, client, agw_headers, ma_headers):
        """턴 목록 조회"""
        # 세션 생성
        session_req = {
            "user_id": "user_turn_003",
            "channel": "web",
            "request_id": "req_turn_003",
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        context_id = session_resp.json()["context_id"]

        # 여러 턴 생성 (메타데이터 전용)
        for i in range(3):
            turn_req = {
                "turn_id": f"turn_{i}",
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata": {
                    "event_type": "SYSTEM_EVENT",
                    "step": i,
                },
            }
            client.post(f"/api/v1/contexts/{context_id}/turns", json=turn_req, headers=ma_headers)

        # 턴 목록 조회
        response = client.get(f"/api/v1/contexts/{context_id}/turns", headers=ma_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["turns"]) == 3


def test_list_turns():
    """턴 목록 조회 테스트"""
    # Given: 컨텍스트에 여러 턴이 있음

    # When: GET /contexts/{context_id}/turns
    # Then: 200 OK, turns 배열 반환


def test_get_turn():
    """턴 조회 테스트"""
    # Given: 턴이 생성되어 있음

    # When: GET /contexts/{context_id}/turns/{turn_id}
    # Then: 200 OK, turn 정보 반환


def test_context_turn_count_increment():
    """턴 생성 시 컨텍스트 turn_count 증가 테스트"""
    # Given: 컨텍스트 생성 (turn_count = 0)

    # When: 턴 3개 생성
    # Then: context.turn_count = 3


def test_redis_cache_hit():
    """Redis 캐시 히트 테스트"""
    # Given: 컨텍스트가 MariaDB와 Redis에 저장됨

    # When: 2번째 조회
    # Then: Redis에서 반환 (캐시 히트)


def test_mariadb_persistence():
    """MariaDB 영구 저장 테스트"""
    # Given: Redis 캐시가 만료됨

    # When: 컨텍스트 조회
    # Then: MariaDB에서 조회 후 Redis 재캐싱


# TODO: 실제 구현 시 위 테스트들을 구체화
