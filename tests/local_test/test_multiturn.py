"""멀티턴 대화 이력 테스트"""

import pytest


class TestMultiTurnConversationHistory:
    """
    멀티턴 대화 이력(reference_information.conversation_history) 저장/조회 통합 테스트
    """

    @pytest.mark.asyncio
    async def test_multiturn_conversation_history_patch_and_get(self, client, agw_headers, ma_headers):
        """
        PATCH로 conversation_history를 저장하고, GET에서 최상위로 노출되는지 검증
        """
        # 1. 세션 생성
        create_req = {
            "userId": "user_multiturn_001",
        }
        print("[TEST] POST /api/v1/sessions 요청:", create_req)
        create_resp = await client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
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
        patch_resp = await client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req,
            headers=ma_headers,
        )
        print("[TEST] PATCH 응답:", patch_resp.status_code, patch_resp.json())
        assert patch_resp.status_code == 200
        assert patch_resp.json()["status"] == "success"

        # 3. GET으로 세션 조회
        print(f"[TEST] GET /api/v1/sessions/{global_session_key} 요청")
        get_resp = await client.get(
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

    @pytest.mark.asyncio
    async def test_multiturn_turn_ids_accumulate(self, client, agw_headers, ma_headers):
        """
        동일 세션에 대해 여러 번 PATCH 호출 시 turn_ids가 누적되고,
        dialog_context.turnId가 마지막 턴 ID로 설정되는지 검증
        """
        # 1. 세션 생성
        create_req = {
            "userId": "user_multiturn_002",
        }
        create_resp = await client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
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
        resp_1 = await client.patch(
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
        resp_2 = await client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req_2,
            headers=ma_headers,
        )
        assert resp_2.status_code == 200

        # 4. GET으로 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=ma_headers,
        )
        assert get_resp.status_code == 200
        data = get_resp.json()

        # turn_ids가 순서대로 누적되었는지 확인
        assert data["turn_ids"] == ["turn_001", "turn_002"]

    @pytest.mark.asyncio
    async def test_reference_information_custom_keys_roundtrip(self, client, agw_headers, ma_headers):
        """
        reference_information에 새로운 키/중첩 구조가 들어갔을 때,
        Redis에 그대로 저장되었다가 GET 응답의 reference_information에서 그대로 조회되는지 검증
        """
        # 1. 세션 생성
        create_req = {
            "userId": "user_multiturn_custom_refinfo",
        }
        create_resp = await client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
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
        patch_resp = await client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req,
            headers=ma_headers,
        )
        assert patch_resp.status_code == 200

        # 3. GET으로 세션 조회
        get_resp = await client.get(
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
