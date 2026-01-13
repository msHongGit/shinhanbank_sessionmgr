"""Session Manager - SOL 실시간 API 결과 저장 API 테스트."""

from datetime import UTC, datetime


def test_save_sol_api_result_as_turn_metadata(client, agw_headers, ma_headers):
    """/api/v1/contexts/turn-results 로 SOL API 결과를 저장한다."""

    # 1) 세션 생성 (global_session_key 확보)
    session_req = {
        "userId": "user_sol_001",
        "channel": {
            "eventType": "ICON_ENTRY",
            "eventChannel": "web",
        },
    }
    session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
    assert session_resp.status_code == 201
    global_session_key = session_resp.json()["global_session_key"]

    # 2) SOL API 결과 저장 요청 (sol_api.md 스펙 기반)
    body = {
        "sessionId": global_session_key,
        "turnId": "turn_sol_001",
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

    resp = client.post("/api/v1/contexts/turn-results", json=body, headers=ma_headers)
    assert resp.status_code == 201

    data = resp.json()
    assert data["turn_id"] == "turn_sol_001"
    assert "metadata" in data
    assert "sol_api" in data["metadata"]

    sol_meta = data["metadata"]["sol_api"]
    assert sol_meta["sessionId"] == global_session_key
    assert sol_meta["turnId"] == "turn_sol_001"
    assert sol_meta["agent"] == "dbs_caller"

    # 요청/응답 메타데이터가 구조적으로 포함되었는지 확인
    assert "request" in sol_meta
    assert "response" in sol_meta
    assert sol_meta["response"]["globId"] == "GLOB123"
    assert sol_meta["response"]["result"] == "SUCCESS"


def test_get_session_full_info(client, agw_headers, ma_headers):
    """세션 전체 정보 조회 (세션 메타데이터 + 턴 목록) API 테스트."""

    # 1) 세션 생성
    session_req = {
        "userId": "user_full_001",
        "channel": {
            "eventType": "ICON_ENTRY",
            "eventChannel": "mobile",
        },
    }
    session_resp = client.post("/api/v1/sessions", json=session_req, headers=agw_headers)
    assert session_resp.status_code == 201
    global_session_key = session_resp.json()["global_session_key"]

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
        "sessionId": global_session_key,
        "turnId": "turn_full_001",
        "agent": "balance_agent",
        "result": "SUCCESS",
        "transactionResult": [
            {
                "trxCd": "BAL001",
                "responseData": {"balance": 500000},
            }
        ],
    }
    sol_resp = client.post("/api/v1/contexts/turn-results", json=sol_body, headers=ma_headers)
    assert sol_resp.status_code == 201

    # 4) 세션 전체 정보 조회
    full_resp = client.get(f"/api/v1/contexts/sessions/{global_session_key}/full", headers=ma_headers)
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
