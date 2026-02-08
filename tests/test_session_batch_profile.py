"""배치 프로파일 통합 테스트"""

import pytest


@pytest.mark.asyncio
class TestBatchProfileIntegration:
    """배치 프로파일 통합 테스트"""

    async def test_realtime_profile_saves_batch_and_realtime_profiles_separately(self, client, agw_headers, ma_headers):
        """실시간 프로파일 업데이트 시 배치와 실시간 프로파일이 분리 저장됨"""
        # 1. 세션 생성
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"user_id": "123"},
            headers=agw_headers,
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        global_session_key = session_data["global_session_key"]
        access_token = session_data["access_token"]

        # 2. 실시간 프로파일 업데이트
        profile_data = {
            "profile_data": {
                "responseData": {
                    "cusnoN10": "616001905",
                    "cusSungNmS20": "홍길동",
                    "userName": "홍길동",
                }
            }
        }

        profile_headers = ma_headers.copy()
        profile_headers["Authorization"] = f"Bearer {access_token}"

        update_resp = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json={
                "global_session_key": global_session_key,
                "profile_data": profile_data["profile_data"],
            },
            headers=profile_headers,
        )
        assert update_resp.status_code == 200

        # 3. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 4. 실시간 프로파일 검증
        realtime_profile = session_data.get("realtime_profile")
        assert realtime_profile is not None

        actual_data = realtime_profile.get("responseData", realtime_profile)

        assert actual_data["cusnoN10"] == "616001905"
        assert actual_data["cusSungNmS20"] == "홍길동"

        # 5. 배치 프로파일 검증
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is not None
        assert "daily" in batch_profile
        assert "monthly" in batch_profile
        assert batch_profile["daily"]["CUSNO"] == "616001905"
        assert batch_profile["monthly"]["CUSNO"] == "616001905"

    async def test_fetch_batch_profile_from_mariadb(self, client, agw_headers, ma_headers):
        """MariaDB에서 배치 프로파일 조회 및 Redis 저장"""
        # 1. 세션 생성
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"user_id": "123"},
            headers=agw_headers,
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        global_session_key = session_data["global_session_key"]
        access_token = session_data["access_token"]

        # 2. 실시간 프로파일 업데이트 (cusnoN10 포함)
        profile_data = {
            "profile_data": {
                "responseData": {
                    "cusnoN10": "616001905",
                    "cusSungNmS20": "홍길동",
                }
            }
        }

        profile_headers = ma_headers.copy()
        profile_headers["Authorization"] = f"Bearer {access_token}"

        update_resp = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json={
                "global_session_key": global_session_key,
                "profile_data": profile_data["profile_data"],
            },
            headers=profile_headers,
        )
        assert update_resp.status_code == 200

        # 3. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 4. 배치 프로파일 검증
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is not None
        assert "daily" in batch_profile
        assert "monthly" in batch_profile
        assert batch_profile["daily"]["CUSNO"] == "616001905"
        assert batch_profile["monthly"]["CUSNO"] == "616001905"
        # 실제 테이블 스키마에 존재하는 컬럼 검증
        assert "STD_DT" in batch_profile["daily"]
        assert "CUSNM" in batch_profile["daily"]
        assert "STD_YM" in batch_profile["monthly"] or len(batch_profile["monthly"]) > 0

    async def test_session_without_cusno_does_not_fetch_batch_profile(self, client, agw_headers, ma_headers):
        """cusnoN10 없는 실시간 프로파일은 배치 프로파일 조회 안 함"""
        # 1. 세션 생성
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"user_id": "test_user_no_cusno"},
            headers=agw_headers,
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        global_session_key = session_data["global_session_key"]
        access_token = session_data["access_token"]

        # 2. 실시간 프로파일 업데이트 (cusnoN10 없음)
        profile_data = {
            "profile_data": {
                "responseData": {
                    "userName": "테스트유저",
                    "someOtherField": "value",
                }
            }
        }

        profile_headers = ma_headers.copy()
        profile_headers["Authorization"] = f"Bearer {access_token}"

        update_resp = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json={
                "global_session_key": global_session_key,
                "profile_data": profile_data["profile_data"],
            },
            headers=profile_headers,
        )
        assert update_resp.status_code == 200

        # 3. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 4. 실시간 프로파일 검증
        realtime_profile = session_data.get("realtime_profile")
        assert realtime_profile is not None

        actual_data = realtime_profile.get("responseData", realtime_profile)

        assert actual_data.get("userName") == "테스트유저"
        assert "cusnoN10" not in actual_data

        # 5. 배치 프로파일이 없는지 확인
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is None

    async def test_multiple_realtime_profile_updates_preserve_batch_profile(self, client, agw_headers, ma_headers):
        """실시간 프로파일 여러 번 업데이트해도 배치 프로파일 유지"""
        # 1. 세션 생성
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"user_id": "123"},
            headers=agw_headers,
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        global_session_key = session_data["global_session_key"]
        access_token = session_data["access_token"]

        # 2. 첫 번째 실시간 프로파일 업데이트
        profile_data_1 = {
            "profile_data": {
                "responseData": {
                    "cusnoN10": "616001905",
                    "cusSungNmS20": "홍길동",
                }
            }
        }

        profile_headers = ma_headers.copy()
        profile_headers["Authorization"] = f"Bearer {access_token}"

        update_resp_1 = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json={
                "global_session_key": global_session_key,
                "profile_data": profile_data_1["profile_data"],
            },
            headers=profile_headers,
        )
        assert update_resp_1.status_code == 200

        # 3. 두 번째 실시간 프로파일 업데이트
        profile_data_2 = {
            "profile_data": {
                "responseData": {
                    "cusnoN10": "616001905",
                    "cusSungNmS20": "김철수",
                    "newField": "newValue",
                }
            }
        }

        update_resp_2 = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json={
                "global_session_key": global_session_key,
                "profile_data": profile_data_2["profile_data"],
            },
            headers=profile_headers,
        )
        assert update_resp_2.status_code == 200

        # 4. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 5. 실시간 프로파일 검증 (최신 데이터)
        realtime_profile = session_data.get("realtime_profile")
        assert realtime_profile is not None

        actual_data = realtime_profile.get("responseData", realtime_profile)

        assert actual_data["cusnoN10"] == "616001905"
        assert actual_data["cusSungNmS20"] == "김철수"
        assert actual_data["newField"] == "newValue"

        # 6. 배치 프로파일은 유지됨
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is not None
        assert batch_profile["daily"]["CUSNO"] == "616001905"

    async def test_invalid_cusno_does_not_crash_batch_profile_fetch(self, client, agw_headers, ma_headers):
        """유효하지 않은 cusno로 배치 프로파일 조회 시 크래시 없음"""
        # 1. 세션 생성
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"user_id": "invalid_user"},
            headers=agw_headers,
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        global_session_key = session_data["global_session_key"]
        access_token = session_data["access_token"]

        # 2. 유효하지 않은 cusnoN10으로 실시간 프로파일 업데이트
        profile_data = {
            "profile_data": {
                "responseData": {
                    "cusnoN10": "invalid_cusno",
                    "userName": "테스트",
                }
            }
        }

        profile_headers = ma_headers.copy()
        profile_headers["Authorization"] = f"Bearer {access_token}"

        update_resp = await client.post(
            "/api/v1/sessions/realtime-personal-context",
            json={
                "global_session_key": global_session_key,
                "profile_data": profile_data["profile_data"],
            },
            headers=profile_headers,
        )
        assert update_resp.status_code == 200

        # 3. 세션 조회 (크래시 없이 성공해야 함)
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 4. 실시간 프로파일은 저장됨
        realtime_profile = session_data.get("realtime_profile")
        assert realtime_profile is not None

        actual_data = realtime_profile.get("responseData", realtime_profile)

        assert actual_data["cusnoN10"] == "invalid_cusno"

        # 5. 배치 프로파일은 없음 (조회 실패했으므로)
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is None

    async def test_session_creation_does_not_fetch_batch_profile(self, client, agw_headers):
        """세션 생성만으로는 배치 프로파일 조회 안 함"""
        # 1. 세션 생성
        create_resp = await client.post(
            "/api/v1/sessions",
            json={"user_id": "616001905"},
            headers=agw_headers,
        )
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 3. 배치 프로파일이 없어야 함
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is None

        # 4. 실시간 프로파일도 없어야 함
        realtime_profile = session_data.get("realtime_profile")
        assert realtime_profile is None
