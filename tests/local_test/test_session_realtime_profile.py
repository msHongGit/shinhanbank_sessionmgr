"""실시간 프로파일 업데이트 테스트"""

import pytest


@pytest.mark.asyncio
class TestRealtimePersonalContext:
    """실시간 프로파일 업데이트 테스트"""

    async def test_update_realtime_personal_context(self, client, agw_headers, ma_headers, mocker):
        """실시간 프로파일 업데이트 및 세션 스냅샷 업데이트 테스트"""
        # 배치 프로파일 조회는 이 테스트에서 검증 대상이 아니므로 MinIO 레포지토리 호출을 막는다
        mocker.patch(
            "app.repositories.minio_batch_profile_repository.MinioBatchProfileRepository.get_batch_profile",
            return_value=None,
        )

        create_req = {"userId": "0616001905"}
        create_resp = await client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
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
        update_resp = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json=update_req,
            headers=headers,
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["status"] == "success"

    async def test_update_realtime_personal_context_no_token(self, client):
        """토큰 없이 호출 시 401 에러 테스트"""
        update_req = {
            "profile_data": {
                "cusSungNmS20": "홍길동",
            }
        }
        update_resp = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json=update_req,
        )
        assert update_resp.status_code == 401
