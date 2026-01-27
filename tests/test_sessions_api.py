import pytest


class TestMultiTurnConversationHistory:
    """
    멀티턴 대화 이력(reference_information.conversation_history) 저장/조회 통합 테스트
    """

    def test_multiturn_conversation_history_patch_and_get(self, client, agw_headers, ma_headers):
        """
        PATCH로 conversation_history를 저장하고, GET에서 최상위로 노출되는지 검증
        """
        # 1. 세션 생성
        create_req = {
            "userId": "user_multiturn_001",
        }
        print("[TEST] POST /api/v1/sessions 요청:", create_req)
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        print("[TEST] POST 응답:", create_resp.status_code, create_resp.json())
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. PATCH로 멀티턴 대화 이력 포함 업데이트
        conversation_history = [{"role": "user", "content": "잔액 조회"}, {"role": "assistant", "content": "계좌번호를 알려주세요"}]
        patch_req = {
            "global_session_key": global_session_key,
            "turn_id": "turn_001",
            "session_state": "talk",
            "state_patch": {"reference_information": {"conversation_history": conversation_history, "current_intent": "계좌조회"}},
        }
        print(f"[TEST] PATCH /api/v1/sessions/{global_session_key}/state 요청:", patch_req)
        patch_resp = client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req,
            headers=ma_headers,
        )
        print("[TEST] PATCH 응답:", patch_resp.status_code, patch_resp.json())
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "success"

        # 3. GET으로 세션 조회
        print(f"[TEST] GET /api/v1/sessions/{global_session_key} 요청")
        get_resp = client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=ma_headers,
        )
        print("[TEST] GET 응답:", get_resp.status_code, get_resp.json())
        assert get_resp.status_code == 200
        data = get_resp.json()

        # 4. conversation_history, current_intent가 최상위에 노출되는지 확인
        assert "conversation_history" in data
        assert data["conversation_history"] == conversation_history
        assert data["current_intent"] == "계좌조회"

        # 5. turn_ids 가 멀티턴 명세에 맞게 노출되는지 확인
        assert "turn_ids" in data
        assert data["turn_ids"] == ["turn_001"]

    def test_multiturn_turn_ids_accumulate(self, client, agw_headers, ma_headers):
        """
        동일 세션에 대해 여러 번 PATCH 호출 시 turn_ids가 누적되고,
        dialog_context.turnId가 마지막 턴 ID로 설정되는지 검증
        """
        # 1. 세션 생성
        create_req = {
            "userId": "user_multiturn_002",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. 첫 번째 PATCH
        patch_req_1 = {
            "global_session_key": global_session_key,
            "turn_id": "turn_001",
            "session_state": "talk",
            "state_patch": {
                "reference_information": {
                    "conversation_history": [{"role": "user", "content": "첫 번째 턴"}],
                    "current_intent": "첫번째의도",
                },
            },
        }
        resp_1 = client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req_1,
            headers=ma_headers,
        )
        assert resp_1.status_code == 200

        # 3. 두 번째 PATCH (turn_id만 변경, state_patch는 생략 가능)
        patch_req_2 = {
            "global_session_key": global_session_key,
            "turn_id": "turn_002",
            "session_state": "talk",
        }
        resp_2 = client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req_2,
            headers=ma_headers,
        )
        assert resp_2.status_code == 200

        # 4. GET으로 세션 조회
        get_resp = client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=ma_headers,
        )
        assert get_resp.status_code == 200
        data = get_resp.json()

        # turn_ids가 순서대로 누적되었는지 확인
        assert data["turn_ids"] == ["turn_001", "turn_002"]

    def test_reference_information_custom_keys_roundtrip(self, client, agw_headers, ma_headers):
        """
        reference_information에 새로운 키/중첩 구조가 들어갔을 때,
        Redis에 그대로 저장되었다가 GET 응답의 reference_information에서 그대로 조회되는지 검증
        """
        # 1. 세션 생성
        create_req = {
            "userId": "user_multiturn_custom_refinfo",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. PATCH로 reference_information에 커스텀 키 포함하여 저장
        patch_req = {
            "global_session_key": global_session_key,
            "turn_id": "turn_custom_001",
            "session_state": "talk",
            "state_patch": {
                "reference_information": {
                    "conversation_history": [
                        {"role": "user", "content": "커스텀 키 테스트 1"},
                        {"role": "assistant", "content": "커스텀 키 테스트 응답"},
                    ],
                    "current_intent": "custom_intent",
                    "custom_meta": {
                        "foo": "bar",
                        "numbers": [1, 2, 3],
                    },
                    "another_list": [
                        {"key": "v1"},
                        {"key": "v2"},
                    ],
                },
            },
        }
        patch_resp = client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req,
            headers=ma_headers,
        )
        assert patch_resp.status_code == 200

        # 3. GET으로 세션 조회
        get_resp = client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=ma_headers,
        )
        assert get_resp.status_code == 200
        data = get_resp.json()

        # 최상위 멀티턴 필드들은 여전히 동작해야 함
        assert data["current_intent"] == "custom_intent"
        assert isinstance(data["conversation_history"], list)
        assert len(data["conversation_history"]) == 2

        # reference_information 전체에서 커스텀 키/값이 그대로 조회되는지 확인
        ref = data.get("reference_information") or {}
        assert "custom_meta" in ref
        assert ref["custom_meta"]["foo"] == "bar"
        assert ref["custom_meta"]["numbers"] == [1, 2, 3]

        assert "another_list" in ref
        assert isinstance(ref["another_list"], list)
        assert ref["another_list"][0]["key"] == "v1"
        assert ref["another_list"][1]["key"] == "v2"


"""
Session Manager - Sessions API Tests (통합 API)
모든 호출자(AGW, MA, CLIENT 등)가 사용하는 통합 API 테스트
"""


class TestHealthCheck:
    """헬스체크 테스트"""

    def test_health_check(self, client):
        """헬스체크"""
        print("[TEST] GET / (health check)")
        response = client.get("/")
        print("[TEST] GET / 응답:", response.status_code, response.json())
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_readiness_check(self, client):
        """레디니스 체크"""
        print("[TEST] GET / (readiness check)")
        response = client.get("/")
        print("[TEST] GET / 응답:", response.status_code, response.json())
        assert response.status_code == 200


class TestSessionCreate:
    """세션 생성 테스트 - 모든 호출자 공통"""

    def test_create_session_success_with_agw(self, client, agw_headers):
        """AGW가 세션 생성 - 프로파일 자동 조회 (Profile Repository에서)"""
        request_data = {
            "userId": "0616001905",  # MockProfileRepository에 존재하는 사용자
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
            "userId": "user_no_profile",  # MockProfileRepository에 없는 사용자
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
        assert data["user_id"] == "0616001905"
        assert data["is_alive"] is True
        assert "session_state" in data
        assert "expires_at" in data

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


class TestSessionResolve:
    """세션 조회 테스트 - MA 주로 사용"""

    def test_resolve_session_success(self, client, agw_headers, ma_headers):
        """세션 조회 성공"""
        # 먼저 세션 생성
        create_req = {
            "userId": "0616001905",  # MockProfileRepository에 존재하는 사용자 ID
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
        assert "customer_profile" in data
        # customer_profile이 None일 수 있으므로 조건부 검증
        if data["customer_profile"] is not None:
            assert data["customer_profile"]["user_id"] == "0616001905"

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


class TestSessionStatePatch:
    """세션 상태 업데이트 테스트"""

    def test_patch_session_state(self, client, agw_headers, ma_headers):
        """세션 상태 업데이트"""
        # 세션 생성
        create_req = {
            "userId": "user_patch_001",
        }
        print("[TEST] POST /api/v1/sessions 요청:", create_req)
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        print("[TEST] POST 응답:", create_resp.status_code, create_resp.json())
        assert create_resp.status_code == 201
        session = create_resp.json()

        # 상태 업데이트
        patch_req = {
            "global_session_key": session["global_session_key"],
            "turn_id": "turn_001",
            "session_state": "talk",
            "state_patch": {
                "subagent_status": "continue",
                "agent_session_key": "asess_transfer_001",
                "last_agent_id": "transfer_agent",
                "last_agent_type": "task",
            },
        }
        print(f"[TEST] PATCH /api/v1/sessions/{session['global_session_key']}/state 요청:", patch_req)
        response = client.patch(
            f"/api/v1/sessions/{session['global_session_key']}/state",
            json=patch_req,
            headers=ma_headers,
        )
        print("[TEST] PATCH 응답:", response.status_code, response.json())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # 업데이트 후 세션 조회 시 agent_session_key가 매핑되어야 함
        print(f"[TEST] GET /api/v1/sessions/{session['global_session_key']} 요청 (agent_type=task, agent_id=transfer_agent)")
        resolve_resp = client.get(
            f"/api/v1/sessions/{session['global_session_key']}",
            params={"channel": "web", "agent_type": "task", "agent_id": "transfer_agent"},
            headers=ma_headers,
        )
        print("[TEST] GET 응답:", resolve_resp.status_code, resolve_resp.json())
        assert resolve_resp.status_code == 200
        resolved = resolve_resp.json()
        assert resolved["agent_session_key"] == "asess_transfer_001"


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


class TestSOLAPIResults:
    """SOL 실시간 API 결과 저장 및 세션 전체 정보 조회 테스트"""

    def test_save_sol_api_result_as_turn_metadata(self, client, agw_headers, ma_headers):
        """/api/v1/sessions/{global_session_key}/api-results 로 SOL API 결과를 저장한다."""

        # 1) 세션 생성 (global_session_key 확보)
        session_req = {
            "userId": "0616001906",
            "channel": {
                "eventType": "ICON_ENTRY",
                "eventChannel": "web",
            },
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        assert session_resp.status_code == 201
        session_data = session_resp.json()
        global_session_key = session_data["global_session_key"]
        # JWT 토큰 응답 확인
        assert "access_token" in session_data
        assert "refresh_token" in session_data
        assert "jti" in session_data

        # 2) SOL API 결과 저장 요청 (sol_api.md 스펙 기반)
        body = {
            "global_session_key": global_session_key,
            "turn_id": "turn_sol_001",
            "agent": "dbs_caller",
            "transactionPayload": [
                {
                    "trxCd": "TRX001",
                    "dataBody": {"foo": "bar"},
                }
            ],
            "globId": "GLOB123",
            "requestId": "REQ123",
            "result": "SUCCESS",
            "resultCode": "0000",
            "resultMsg": "OK",
            "transactionResult": [
                {
                    "trxCd": "TRX001",
                    "responseData": {"balance": 100000},
                }
            ],
        }

        resp = client.post(f"/api/v1/sessions/{global_session_key}/api-results", json=body, headers=ma_headers)
        assert resp.status_code == 201

        data = resp.json()
        # turn_id, global_session_key는 스키마에서 필수 필드로 정의되어 있어 자동 검증됨
        assert "metadata" in data
        assert "sol_api" in data["metadata"]

        sol_meta = data["metadata"]["sol_api"]
        assert sol_meta["global_session_key"] == global_session_key
        assert sol_meta["turn_id"] == "turn_sol_001"
        assert sol_meta["agent"] == "dbs_caller"

        # 요청/응답 메타데이터가 구조적으로 포함되었는지 확인
        assert "request" in sol_meta
        assert "response" in sol_meta
        assert sol_meta["response"]["globId"] == "GLOB123"
        assert sol_meta["response"]["result"] == "SUCCESS"

    def test_get_session_full_info(self, client, agw_headers, ma_headers):
        """세션 전체 정보 조회 (세션 메타데이터 + 턴 목록) API 테스트."""

        # 1) 세션 생성
        session_req = {
            "userId": "0616001907",
            "channel": {
                "eventType": "ICON_ENTRY",
                "eventChannel": "mobile",
            },
        }
        session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
        assert session_resp.status_code == 201
        session_data = session_resp.json()
        global_session_key = session_data["global_session_key"]
        # JWT 토큰 응답 확인
        assert "access_token" in session_data
        assert "refresh_token" in session_data
        assert "jti" in session_data

        # 2) 세션 상태 업데이트 (멀티턴 컨텍스트 추가)
        patch_req = {
            "global_session_key": global_session_key,
            "turn_id": "turn_full_001",
            "session_state": "talk",
            "state_patch": {
                "subagent_status": "continue",
                "reference_information": {
                    "conversation_history": [
                        {"role": "user", "content": "잔액 조회"},
                        {"role": "assistant", "content": "계좌번호를 알려주세요"},
                    ],
                    "current_intent": "계좌조회",
                },
            },
        }
        patch_resp = client.patch(f"/api/v1/sessions/{global_session_key}/state", json=patch_req, headers=ma_headers)
        assert patch_resp.status_code == 200

        # 3) SOL API 결과 저장 (턴 메타데이터)
        sol_body = {
            "global_session_key": global_session_key,
            "turn_id": "turn_full_001",
            "agent": "balance_agent",
            "result": "SUCCESS",
            "transactionResult": [
                {
                    "trxCd": "BAL001",
                    "responseData": {"balance": 500000},
                }
            ],
        }
        sol_resp = client.post(f"/api/v1/sessions/{global_session_key}/api-results", json=sol_body, headers=ma_headers)
        assert sol_resp.status_code == 201

        # 4) 세션 전체 정보 조회
        full_resp = client.get(f"/api/v1/sessions/{global_session_key}/full", headers=ma_headers)
        assert full_resp.status_code == 200

        full_data = full_resp.json()

        # 세션 메타데이터 확인
        assert "session" in full_data
        assert full_data["session"]["global_session_key"] == global_session_key
        assert full_data["session"]["session_state"] == "talk"
        assert full_data["session"]["subagent_status"] == "continue"
        assert "conversation_history" in full_data["session"]
        assert len(full_data["session"]["conversation_history"]) == 2

        # 턴 목록 확인
        assert "turns" in full_data
        assert full_data["total_turns"] == 1
        assert len(full_data["turns"]) == 1

        turn = full_data["turns"][0]
        assert turn["turn_id"] == "turn_full_001"
        assert "metadata" in turn
        assert "sol_api" in turn["metadata"]
        assert turn["metadata"]["sol_api"]["agent"] == "balance_agent"
        assert turn["metadata"]["sol_api"]["response"]["result"] == "SUCCESS"


class TestRealtimePersonalContext:
    """실시간 프로파일 업데이트 테스트"""

    def test_update_realtime_personal_context(self, client, agw_headers, ma_headers):
        """실시간 프로파일 업데이트 및 세션 스냅샷 업데이트 테스트"""
        # 1. 세션 생성
        create_req = {
            "userId": "0616001905",
            "channel": {
                "eventType": "ICON_ENTRY",
                "eventChannel": "web",
            },
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. 실시간 프로파일 업데이트
        profile_data = {
            "cusnoS10": "0616001905",
            "cusSungNmS20": "홍길동",
            "hpNoS12": "01031286270",
            "biryrMmddS6": "710115",
            "onlyAgeN3": 55,
            "membGdS2": "02",
            "loginDt": "2026.01.21",
            "loginTimesS6": "14:23:59",
        }
        update_req = {
            "profile_data": profile_data,
        }
        update_resp = client.post(
            f"/api/v1/sessions/{global_session_key}/realtime-personal-context",
            json=update_req,
            headers=ma_headers,
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["status"] == "success"
        assert "updated_at" in update_data
        # user_id는 응답에 포함되지 않음
        assert "user_id" not in update_data

        # 3. 세션 조회하여 customer_profile이 업데이트되었는지 확인
        get_resp = client.get(f"/api/v1/sessions/{global_session_key}", headers=ma_headers)
        assert get_resp.status_code == 200
        session_data = get_resp.json()
        
        # customer_profile이 존재하고 실시간 프로파일 데이터가 포함되어 있는지 확인
        assert "customer_profile" in session_data
        assert session_data["customer_profile"] is not None
        
        customer_profile = session_data["customer_profile"]
        assert customer_profile["user_id"] == "0616001905"
        assert "attributes" in customer_profile
        
        # 실시간 프로파일의 주요 필드가 attributes에 포함되어 있는지 확인
        attributes_dict = {attr["key"]: attr["value"] for attr in customer_profile["attributes"]}
        assert "cusnoS10" in attributes_dict
        assert attributes_dict["cusnoS10"] == "0616001905"
        assert "cusSungNmS20" in attributes_dict
        assert attributes_dict["cusSungNmS20"] == "홍길동"
        assert "membGdS2" in attributes_dict
        assert attributes_dict["membGdS2"] == "02"
        
        # segment가 membGdS2 값으로 설정되었는지 확인
        assert customer_profile["segment"] == "02"

    def test_update_realtime_personal_context_session_not_found(self, client, ma_headers):
        """존재하지 않는 세션에 대한 실시간 프로파일 업데이트 테스트"""
        profile_data = {
            "cusnoS10": "0616001905",
            "cusSungNmS20": "홍길동",
        }
        update_req = {
            "profile_data": profile_data,
        }
        update_resp = client.post(
            "/api/v1/sessions/nonexistent_session_key/realtime-personal-context",
            json=update_req,
            headers=ma_headers,
        )
        assert update_resp.status_code == 404
