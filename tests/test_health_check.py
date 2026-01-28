"""헬스체크 테스트"""

import pytest


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
