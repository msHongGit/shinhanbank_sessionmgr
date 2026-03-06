"""배치 프로파일 통합 테스트"""

import pytest

from app import config as app_config

# 애플리케이션과 동일한 설정 로직(app.config)을 사용해 MinIO 설정 여부를 판단한다.
MINIO_CONFIGURED = bool(app_config.MINIO_ENDPOINT)
try:  # pragma: no cover - 테스트 환경에 따라 달라질 수 있음
    # 실제 MinIO 단건 조회 헬퍼 모듈이 프로젝트 내에 존재하는지 확인
    from app.services import batch_profile_minio_retrieve  # type: ignore[import,unused-import]  # noqa: F401

    MINIO_MODULE_AVAILABLE = True
except Exception:  # pragma: no cover - MinIO 연동 모듈이 없을 수 있음
    MINIO_MODULE_AVAILABLE = False


@pytest.mark.asyncio
class TestBatchProfileIntegration:
    """배치 프로파일 통합 테스트"""

    @pytest.mark.skipif(
        not (MINIO_CONFIGURED and MINIO_MODULE_AVAILABLE),
        reason="MinIO batch profile backend is not configured",
    )
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
                    "cusnoN10": "700000001",
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

        # 디버그: 실시간 프로파일 업데이트 응답
        print("[DEBUG][realtime_update] response:", update_resp.json())

        # 3. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 디버그: 세션 전체 데이터
        print("[DEBUG][session_after_realtime] session_data keys:", list(session_data.keys()))
        print("[DEBUG][session_after_realtime] session_data.realtime_profile:", session_data.get("realtime_profile"))
        print("[DEBUG][session_after_realtime] session_data.batch_profile:", session_data.get("batch_profile"))

        # 4. 실시간 프로파일 검증
        realtime_profile = session_data.get("realtime_profile")
        assert realtime_profile is not None

        actual_data = realtime_profile.get("responseData", realtime_profile)

        assert actual_data["cusnoN10"] == "700000001"
        assert actual_data["cusSungNmS20"] == "홍길동"

        # 5. 배치 프로파일 검증
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is not None
        print("[DEBUG][batch_profile] full batch_profile:", batch_profile)
        assert "daily" in batch_profile
        assert str(batch_profile["daily"]["CUSNO"]) == "700000001"

        # 월별 배치 프로파일은 MinIO 적재 여부에 따라 없을 수 있으므로
        # 존재하는 경우에만 CUSNO를 검증한다.
        monthly_profile = batch_profile.get("monthly")
        if monthly_profile is not None:
            assert str(monthly_profile["CUSNO"]) == "700000001"

    @pytest.mark.skipif(
        not (MINIO_CONFIGURED and MINIO_MODULE_AVAILABLE),
        reason="MinIO batch profile backend is not configured",
    )
    async def test_fetch_batch_profile_from_minio(self, client, agw_headers, ma_headers):
        """MinIO에서 배치 프로파일 조회 및 Redis 저장"""
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
                    "cusnoN10": "700000001",
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

        # 디버그: 실시간 프로파일 업데이트 응답
        print("[DEBUG][realtime_update] response:", update_resp.json())

        # 3. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 디버그: 세션 전체 데이터
        print("[DEBUG][session_after_realtime] session_data keys:", list(session_data.keys()))
        print("[DEBUG][session_after_realtime] session_data.realtime_profile:", session_data.get("realtime_profile"))
        print("[DEBUG][session_after_realtime] session_data.batch_profile:", session_data.get("batch_profile"))

        # 4. 배치 프로파일 검증
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is not None
        print("[DEBUG][batch_profile] full batch_profile:", batch_profile)
        assert "daily" in batch_profile
        daily_profile = batch_profile["daily"]
        assert str(daily_profile["CUSNO"]) == "700000001"

        # MinIO 배치 문서 스키마에 맞게, data 필드 구조만 검증한다.
        assert "data" in daily_profile
        assert isinstance(daily_profile["data"], dict)

        # 월별 배치 프로파일은 선택적이다.
        # monthly 데이터는 flat 구조(data 래핑 없음)이므로 CUSNO 존재 여부만 확인한다.
        monthly_profile = batch_profile.get("monthly")
        if monthly_profile is not None:
            assert "CUSNO" in monthly_profile

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

    @pytest.mark.skipif(
        not (MINIO_CONFIGURED and MINIO_MODULE_AVAILABLE),
        reason="MinIO batch profile backend is not configured",
    )
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
                    "cusnoN10": "700000001",
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

        # 디버그: 첫 번째 실시간 프로파일 업데이트 응답
        print("[DEBUG][realtime_update_1] response:", update_resp_1.json())

        # 3. 두 번째 실시간 프로파일 업데이트
        profile_data_2 = {
            "profile_data": {
                "responseData": {
                    "cusnoN10": "700000001",
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

        # 디버그: 두 번째 실시간 프로파일 업데이트 응답
        print("[DEBUG][realtime_update_2] response:", update_resp_2.json())

        # 4. 세션 조회
        get_resp = await client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=agw_headers,
        )
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 디버그: 두 번의 업데이트 이후 세션 전체 데이터
        print("[DEBUG][session_after_two_updates] session_data keys:", list(session_data.keys()))
        print("[DEBUG][session_after_two_updates] session_data.realtime_profile:", session_data.get("realtime_profile"))
        print("[DEBUG][session_after_two_updates] session_data.batch_profile:", session_data.get("batch_profile"))

        # 5. 실시간 프로파일 검증 (최신 데이터)
        realtime_profile = session_data.get("realtime_profile")
        assert realtime_profile is not None

        actual_data = realtime_profile.get("responseData", realtime_profile)

        assert actual_data["cusnoN10"] == "700000001"
        assert actual_data["cusSungNmS20"] == "김철수"
        assert actual_data["newField"] == "newValue"

        # 6. 배치 프로파일은 유지됨
        batch_profile = session_data.get("batch_profile")
        assert batch_profile is not None
        assert str(batch_profile["daily"]["CUSNO"]) == "700000001"

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
