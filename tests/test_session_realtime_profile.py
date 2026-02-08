"""실시간 프로파일 업데이트 테스트"""

import pytest


class TestRealtimePersonalContext:
    """실시간 프로파일 업데이트 테스트"""

    def test_update_realtime_personal_context(self, client, agw_headers, ma_headers, mocker):
        """실시간 프로파일 업데이트 및 세션 스냅샷 업데이트 테스트"""
        # MariaDB 조회 완전 차단 (repository 메서드를 직접 mock)
        mocker.patch(
            "app.repositories.mariadb_batch_profile_repository.MariaDBBatchProfileRepository.get_batch_profile",
            return_value=None,
        )

        create_req = {"userId": "0616001905"}
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        body = create_resp.json()
        access_token = body["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}

        update_req = {
            "profile_data": {
                "cusSungNmS20": "홍길동",
                "hpNoS12": "01031286270",
            }
        }
        update_resp = client.post(
            "/api/v1/sessions/realtime-personal-context",
            json=update_req,
            headers=headers,
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["status"] == "success"

    def test_update_realtime_personal_context_no_token(self, client):
        """토큰 없이 호출 시 401 에러 테스트"""
        update_req = {
            "profile_data": {
                "cusSungNmS20": "홍길동",
            }
        }
        update_resp = client.post(
            "/api/v1/sessions/realtime-personal-context",
            json=update_req,
        )
        assert update_resp.status_code == 401
