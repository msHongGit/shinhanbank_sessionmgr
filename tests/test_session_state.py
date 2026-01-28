"""세션 상태 업데이트 테스트"""

import pytest


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
