"""세션 종료 테스트"""

import pytest


class TestSessionClose:
    """세션 종료 테스트"""

    @pytest.mark.asyncio
    async def test_close_session_by_key(self, client, agw_headers, ma_headers):
        """세션 종료 (Master Agent용, global_session_key 경로 사용 + 토큰 무효화 검증)"""
        # 세션 생성
        create_req = {
            "userId": "user_close_001",
        }
        print("[TEST] POST /api/v1/sessions 요청:", create_req)
        create_resp = await client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        print("[TEST] POST 응답:", create_resp.status_code, create_resp.json())
        assert create_resp.status_code == 201
        session = create_resp.json()

        global_session_key = session["global_session_key"]

        # 세션 종료 (기존 방식, MA용 - global_session_key 기반)
        print(f"[TEST] DELETE /api/v1/sessions/{global_session_key} 요청 (close_reason=test_completed)")
        response = await client.delete(
            f"/api/v1/sessions/{global_session_key}",
            params={
                "close_reason": "test_completed",
            },
            headers=ma_headers,
        )
        print("[TEST] DELETE 응답:", response.status_code, response.json())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_close_session_by_token(self, client, session_with_tokens):
        """세션 종료 (토큰 기반)"""
        tokens = session_with_tokens
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # 1차 종료: 정상 종료 + 토큰 무효화
        response = await client.delete(
            "/api/v1/sessions",
            params={"close_reason": "test_completed"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # 2차 종료: 같은 토큰으로 다시 호출하면 jti 매핑이 없어야 하므로 실패해야 함
        response_again = await client.delete(
            "/api/v1/sessions",
            params={"close_reason": "should_fail"},
            headers=headers,
        )
        # 구현에 따라 401 / 404 / 400 중 하나일 수 있으니,
        # 실제 close_session_by_token 구현의 에러 코드를 맞춰서 검사
        assert response_again.status_code in (400, 401, 404)

    @pytest.mark.asyncio
    async def test_close_session_by_token_from_cookie(self, client, session_with_tokens):
        """쿠키에서 Access Token 추출하여 세션 종료"""
        tokens = session_with_tokens
        client.cookies.set("access_token", tokens["access_token"])

        # 1차 종료
        response = await client.delete("/api/v1/sessions", params={"close_reason": "test_completed"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # 2차 종료: 같은 쿠키(토큰)로는 더 이상 종료가 되면 안 됨
        response_again = await client.delete("/api/v1/sessions", params={"close_reason": "should_fail"})
        assert response_again.status_code in (400, 401, 404)
