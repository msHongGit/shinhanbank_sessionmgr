"""
Session Manager - Portal API Tests (v4.0)
Portal → SM
Sprint 1: Mock Repository 사용
"""


class TestPortalSessionList:
    """Portal 세션 목록 조회 테스트"""

    def test_list_sessions(self, client, agw_headers, portal_headers, sample_agw_session_create_request):
        """세션 목록 조회"""
        # 테스트용 세션 생성
        client.post("/api/v1/agw/sessions", json=sample_agw_session_create_request, headers=agw_headers)

        # 세션 목록 조회
        response = client.get("/api/v1/portal/sessions", params={"page": 1, "page_size": 20}, headers=portal_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1
