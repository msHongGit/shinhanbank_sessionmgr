"""실시간 프로파일 업데이트 테스트"""

import pytest


class TestRealtimePersonalContext:
    """실시간 프로파일 업데이트 테스트"""

    def test_update_realtime_personal_context(self, client, agw_headers, ma_headers):
        """실시간 프로파일 업데이트 및 세션 스냅샷 업데이트 테스트"""
        # 1. 세션 생성
        create_req = {
            "userId": "0616001905",
            "channel": {
                "eventType": "ICON_ENTRY",
                "eventChannel": "web",
            },
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. 실시간 프로파일 업데이트
        profile_data = {
            "cusnoS10": "0616001905",
            "cusSungNmS20": "홍길동",
            "hpNoS12": "01031286270",
            "biryrMmddS6": "710115",
            "onlyAgeN3": 55,
            "membGdS2": "02",
            "loginDt": "2026.01.21",
            "loginTimesS6": "14:23:59",
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
        update_data = update_resp.json()
        assert update_data["status"] == "success"
        assert "updated_at" in update_data
        # user_id는 응답에 포함되지 않음
        assert "user_id" not in update_data

        # 3. 세션 조회하여 실시간 프로파일이 분리되어 전달되는지 확인
        get_resp = client.get(f"/api/v1/sessions/{global_session_key}", headers=ma_headers)
        assert get_resp.status_code == 200
        session_data = get_resp.json()

        # 통합 프로파일은 제거되었으므로 None이어야 함
        assert "customer_profile" in session_data
        assert session_data["customer_profile"] is None

        # 실시간 프로파일이 분리되어 전달되는지 확인
        assert "realtime_profile" in session_data
        realtime_profile = session_data["realtime_profile"]
        assert realtime_profile is not None
        assert realtime_profile["cusnoS10"] == "0616001905"
        assert realtime_profile["cusSungNmS20"] == "홍길동"
        assert realtime_profile["membGdS2"] == "02"

        # 배치 프로파일도 함께 저장되었는지 확인 (실시간 프로파일 저장 시 자동 조회 및 저장)
        assert "batch_profile" in session_data
        batch_profile = session_data["batch_profile"]
        assert batch_profile is not None
        assert "daily" in batch_profile
        assert "monthly" in batch_profile
        assert batch_profile["daily"]["CUSNO"] == "0616001905"
        assert batch_profile["monthly"]["CUSNO"] == "0616001905"

    def test_update_realtime_personal_context_session_not_found(self, client, ma_headers):
        """존재하지 않는 세션에 대한 실시간 프로파일 업데이트 테스트"""
        profile_data = {
            "cusnoS10": "0616001905",
            "cusSungNmS20": "홍길동",
        }
        update_req = {
            "global_session_key": "nonexistent_session_key",
            "profile_data": profile_data,
        }
        update_resp = client.post(
            "/api/v1/sessions/nonexistent_session_key/realtime-personal-context",
            json=update_req,
            headers=ma_headers,
        )
        assert update_resp.status_code == 404

    def test_update_realtime_personal_context_key_mismatch(self, client, agw_headers, ma_headers):
        """경로 변수와 요청 body의 global_session_key 불일치 테스트"""
        # 1. 세션 생성
        create_req = {
            "userId": "0616001905",
        }
        create_resp = client.post("/api/v1/sessions", json=create_req, headers=agw_headers)
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]

        # 2. 경로 변수와 다른 global_session_key를 body에 포함하여 요청
        profile_data = {
            "cusnoS10": "0616001905",
            "cusSungNmS20": "홍길동",
        }
        update_req = {
            "global_session_key": "different_session_key",
            "profile_data": profile_data,
        }
        update_resp = client.post(
            f"/api/v1/sessions/{global_session_key}/realtime-personal-context",
            json=update_req,
            headers=ma_headers,
        )
        assert update_resp.status_code == 400
        assert "global_session_key mismatch" in update_resp.json()["detail"]
