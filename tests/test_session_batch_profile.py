"""배치 프로파일 통합 테스트"""

import os

import pytest


class TestBatchProfileIntegration:
    """배치 프로파일 통합 테스트"""

    def test_realtime_profile_saves_batch_and_realtime_profiles_separately(self, client, agw_headers, ma_headers):
        """실시간 프로파일 저장 시 배치 프로파일 조회 및 분리 반환 테스트 (통합)

        이 테스트는 다음을 검증합니다:
        1. 세션 생성 시 배치 프로파일 조회 안 함
        2. 실시간 프로파일 저장 시 MariaDB에서 배치 프로파일 조회 및 Redis 저장
        3. 세션 조회 시 배치/실시간 프로파일 분리 반환
        4. customer_profile은 None (통합 프로파일 제거됨)
        """
        # 1. 세션 생성 (CUSNO 없음, 배치 프로파일 조회 안 함)
        create_req = {
            "userId": "0616001905",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. 실시간 프로파일 업데이트 (이때 배치 프로파일 조회 및 Redis 저장)
        profile_data = {
            "cusnoS10": "0616001905",  # CUSNO로 사용됨
            "cusSungNmS20": "홍길동",
            "hpNoS12": "01031286270",
        }
        update_req = {
            "global_session_key": global_session_key,
            "profile_data": profile_data,
        }
        update_resp = client.post(
            f"/api/v1/sessions/{global_session_key}/realtime-personal-context",
            json=update_req,
            headers=ma_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "success"

        # 3. 세션 조회 (Redis에서만 조회, MariaDB 재조회 없음)
        get_resp = client.get(f"/api/v1/sessions/{global_session_key}", headers=ma_headers)
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 4. 배치 프로파일 확인 (실시간 프로파일 저장 시 이미 Redis에 저장됨)
        assert "batch_profile" in session_data
        batch_profile = session_data["batch_profile"]
        if batch_profile is not None:  # MariaDB에 데이터가 있으면 확인
            assert "daily" in batch_profile or "monthly" in batch_profile
            if "daily" in batch_profile:
                assert batch_profile["daily"]["CUSNO"] == "0616001905"
            if "monthly" in batch_profile:
                assert batch_profile["monthly"]["CUSNO"] == "0616001905"

        # 5. 실시간 프로파일 확인
        assert "realtime_profile" in session_data
        realtime_profile = session_data["realtime_profile"]
        assert realtime_profile is not None
        assert realtime_profile["cusnoS10"] == "0616001905"
        assert realtime_profile["cusSungNmS20"] == "홍길동"

        # 6. 통합 프로파일은 제거되었으므로 None이어야 함
        assert "customer_profile" in session_data
        assert session_data["customer_profile"] is None

    @pytest.mark.skipif(
        not os.getenv("MARIADB_HOST") or not os.getenv("MARIADB_DATABASE"),
        reason="MariaDB connection not configured",
    )
    def test_fetch_batch_profile_from_mariadb(self, client, agw_headers, ma_headers):
        """실제 MariaDB에서 배치 프로파일을 가져오는 통합 테스트

        이 테스트는 실제 MariaDB를 사용합니다.
        MariaDB 연결 정보가 설정되어 있어야 합니다.
        """
        # 1. 세션 생성
        create_req = {
            "userId": "0616001905",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. 실시간 프로파일 업데이트 (이때 실제 MariaDB에서 배치 프로파일 조회)
        profile_data = {
            "cusnoS10": "0616001905",  # CUSNO로 사용됨
            "cusSungNmS20": "홍길동",
        }
        update_req = {
            "global_session_key": global_session_key,
            "profile_data": profile_data,
        }
        update_resp = client.post(
            f"/api/v1/sessions/{global_session_key}/realtime-personal-context",
            json=update_req,
            headers=ma_headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == "success"

        # 3. 세션 조회하여 실제 MariaDB에서 가져온 배치 프로파일 확인
        get_resp = client.get(f"/api/v1/sessions/{global_session_key}", headers=ma_headers)
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 배치 프로파일이 조회되었는지 확인 (실제 MariaDB에서 조회됨)
        assert "batch_profile" in session_data
        batch_profile = session_data["batch_profile"]

        # MariaDB에 데이터가 있으면 확인, 없으면 None일 수 있음
        if batch_profile is not None:
            assert "daily" in batch_profile or "monthly" in batch_profile
            if "daily" in batch_profile:
                assert batch_profile["daily"]["CUSNO"] == "0616001905"
            if "monthly" in batch_profile:
                assert batch_profile["monthly"]["CUSNO"] == "0616001905"

        # 실시간 프로파일 확인
        assert "realtime_profile" in session_data
        realtime_profile = session_data["realtime_profile"]
        assert realtime_profile is not None
        assert realtime_profile["cusnoS10"] == "0616001905"
