"""
Session Manager - Session API Tests
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestSessionAPI:
    """Session API 테스트"""
    
    async def test_health_check(self, client: AsyncClient):
        """헬스체크 테스트"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "session-manager"
    
    async def test_create_session_without_api_key(self, client: AsyncClient):
        """API Key 없이 세션 생성 시도"""
        response = await client.post(
            "/api/v1/sessions",
            json={
                "user_id": "user_001",
                "channel": "mobile",
                "session_key": {"scope": "global", "key": "test"},
                "request_id": "req_001"
            }
        )
        assert response.status_code == 401
    
    async def test_create_session_success(
        self,
        client: AsyncClient,
        api_headers: dict,
        sample_session_create_request: dict,
    ):
        """세션 생성 성공"""
        response = await client.post(
            "/api/v1/sessions",
            json=sample_session_create_request,
            headers=api_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "conversation_id" in data
        assert data["session_state"] == "start"
    
    async def test_resolve_session(
        self,
        client: AsyncClient,
        api_headers: dict,
    ):
        """세션 조회"""
        response = await client.get(
            "/api/v1/sessions/resolve",
            params={
                "session_key_scope": "global",
                "session_key_value": "test_resolve",
                "channel": "mobile",
            },
            headers=api_headers,
        )
        # 세션이 없으면 자동 생성되므로 201 또는 200
        assert response.status_code in [200, 201]
        data = response.json()
        assert "session_id" in data
        assert "is_first_call" in data
    
    async def test_patch_session_state(
        self,
        client: AsyncClient,
        api_headers: dict,
        sample_session_create_request: dict,
    ):
        """세션 상태 업데이트"""
        # 먼저 세션 생성
        create_response = await client.post(
            "/api/v1/sessions",
            json=sample_session_create_request,
            headers=api_headers,
        )
        session_id = create_response.json()["session_id"]
        conversation_id = create_response.json()["conversation_id"]
        
        # 상태 업데이트
        response = await client.patch(
            f"/api/v1/sessions/{session_id}",
            json={
                "conversation_id": conversation_id,
                "turn_id": "turn_001",
                "session_state": "talk",
                "state_patch": {
                    "subagent_status": "continue",
                    "action_owner": "master-agent",
                }
            },
            headers=api_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    async def test_close_session(
        self,
        client: AsyncClient,
        api_headers: dict,
        sample_session_create_request: dict,
    ):
        """세션 종료"""
        # 먼저 세션 생성
        create_response = await client.post(
            "/api/v1/sessions",
            json=sample_session_create_request,
            headers=api_headers,
        )
        session_id = create_response.json()["session_id"]
        conversation_id = create_response.json()["conversation_id"]
        
        # 세션 종료
        response = await client.post(
            f"/api/v1/sessions/{session_id}/close",
            json={
                "conversation_id": conversation_id,
                "close_reason": "user_exit",
                "final_summary": "테스트 종료",
            },
            headers=api_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "archived_conversation_id" in data
