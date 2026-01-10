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
