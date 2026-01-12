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

        # 5. turn_ids 및 dialog_context가 멀티턴 명세에 맞게 노출되는지 확인
        assert "turn_ids" in data
        assert data["turn_ids"] == ["turn_001"]

        assert "dialog_context" in data
        dialog_context = data["dialog_context"]

        # DialogContext 기본 필드 검증
        assert dialog_context["turnId"] == "turn_001"
        assert dialog_context["currentIntent"] == "계좌조회"
        assert isinstance(dialog_context["history"], list)
        assert len(dialog_context["history"]) == len(conversation_history)

        # history 내부 DialogTurn 구조 검증 (role, content 유지)
        for idx, turn in enumerate(conversation_history):
            dc_turn = dialog_context["history"][idx]
            assert dc_turn["role"] == turn["role"]
            assert dc_turn["content"] == turn["content"]

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

        # dialog_context.turnId가 마지막 턴 ID를 가리키는지 확인
        assert "dialog_context" in data
        dialog_context = data["dialog_context"]
        assert dialog_context["turnId"] == "turn_002"

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
        """AGW가 세션 생성 - 프로파일 자동 조회 (MariaDB context_db에서)"""
        request_data = {
            "userId": "user_vip_001",  # MockProfileRepository에 존재하는 사용자
        }
        print("[TEST] POST /api/v1/sessions 요청:", request_data)
        response = client.post("/api/v1/sessions", json=request_data, headers=agw_headers)
        print("[TEST] POST 응답:", response.status_code, response.json())
        assert response.status_code == 201
        data = response.json()
        assert data["global_session_key"].startswith("gsess_")
        # 응답에는 Global 세션 키만 포함된다.
        assert set(data.keys()) == {"global_session_key"}

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
        assert set(data.keys()) == {"global_session_key"}

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
        assert set(data.keys()) == {"global_session_key"}


class TestSessionResolve:
    """세션 조회 테스트 - MA 주로 사용"""

    def test_resolve_session_success(self, client, agw_headers, ma_headers):
        """세션 조회 성공"""
        # 먼저 세션 생성
        create_req = {
            "userId": "user_vip_001",  # MockProfileRepository에 존재
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
        assert data["customer_profile"]["user_id"] == "user_vip_001"

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

    def test_close_session(self, client, agw_headers, ma_headers):
        """세션 종료"""
        # 세션 생성
        create_req = {
            "userId": "user_close_001",
        }
        print("[TEST] POST /api/v1/sessions 요청:", create_req)
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        print("[TEST] POST 응답:", create_resp.status_code, create_resp.json())
        assert create_resp.status_code == 201
        session = create_resp.json()

        # 세션 종료
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
