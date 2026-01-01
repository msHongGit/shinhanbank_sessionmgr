"""
Session Manager - Demo Scenario Test (Sprint 2)

데모 시나리오에서 사용되는 7개 API만 테스트합니다.

## 테스트 실행 방법

전체 테스트:
```bash
uv run pytest tests/test_demo_scenario.py -v
```

개별 테스트:
```bash
# 데모 시나리오 순차 실행 테스트
uv run pytest tests/test_demo_scenario.py::TestDemoScenarioSimple::test_demo_apis_sequential -v -s

# API 목록 출력 테스트
uv run pytest tests/test_demo_scenario.py::TestDemoAPISummary::test_list_demo_apis -v -s
```

## 테스트 포함 API (총 7개)

1. POST   /api/v1/agw/sessions          - 세션 생성
2. GET    /api/v1/ma/sessions/resolve   - 세션 조회
3. GET    /api/v1/ma/profiles/{user_id} - 프로파일 조회
4. POST   /api/v1/ma/context/turn       - 대화 턴 저장
5. GET    /api/v1/ma/context/history    - 대화 이력 조회
6. PATCH  /api/v1/ma/sessions/state     - 세션 상태 업데이트
7. POST   /api/v1/ma/sessions/close     - 세션 종료

## 참고 문서

- DEMO_SCENARIO_V2.md: 데모 시나리오 전체 흐름
- Session_Manager_API_Sprint2.md: Sprint 2 전체 API 명세 (13개)
"""

from datetime import UTC, datetime

from fastapi.testclient import TestClient


class TestDemoScenarioSimple:
    """데모 시나리오의 모든 API를 간단하게 테스트"""

    def test_demo_apis_sequential(self, client: TestClient, agw_headers, ma_headers):
        """
        데모 시나리오의 모든 API를 순차적으로 호출 테스트

        사용되는 API:
        1. POST /api/v1/agw/sessions - 세션 생성
        2. GET /api/v1/ma/sessions/resolve - 세션 조회
        3. GET /api/v1/ma/profiles/{user_id} - 프로파일 조회
        4. POST /api/v1/ma/context/turn - 대화 턴 저장
        5. GET /api/v1/ma/context/history - 대화 이력 조회
        6. PATCH /api/v1/ma/sessions/state - 세션 상태 업데이트
        7. POST /api/v1/ma/sessions/close - 세션 종료
        """

        print("\n========== 데모 시나리오 API 테스트 시작 ==========")

        # 1. POST /api/v1/agw/sessions - 세션 생성
        print("\n[1] POST /api/v1/agw/sessions - 세션 생성")
        session_resp = client.post(
            "/api/v1/agw/sessions",
            json={"global_session_key": "gsess_demo_test", "user_id": "user_vip_001", "channel": "web", "request_id": "req_demo_test"},
            headers=agw_headers,
        )
        assert session_resp.status_code == 201, f"세션 생성 실패: {session_resp.json()}"
        session_data = session_resp.json()
        global_session_key = session_data["global_session_key"]
        conversation_id = session_data["conversation_id"]
        context_id = session_data["context_id"]
        print(f"   ✅ 세션 생성 성공: {global_session_key}")
        print(f"      - conversation_id: {conversation_id}")
        print(f"      - context_id: {context_id}")
        print(f"      - session_state: {session_data['session_state']}")
        print(f"      - is_new: {session_data['is_new']}")

        # 2. GET /api/v1/ma/sessions/resolve - 세션 조회
        print("\n[2] GET /api/v1/ma/sessions/resolve - 세션 조회")
        resolve_resp = client.get(
            "/api/v1/ma/sessions/resolve", params={"global_session_key": global_session_key, "channel": "web"}, headers=ma_headers
        )
        assert resolve_resp.status_code == 200, f"세션 조회 실패: {resolve_resp.json()}"
        resolve_data = resolve_resp.json()
        print("   ✅ 세션 조회 성공")
        print(f"      응답 데이터: {resolve_data}")
        # print(f"      - user_id: {resolve_data['session']['user_id']}")
        # print(f"      - session_state: {resolve_data['session']['session_state']}")
        # print(f"      - turn_count: {resolve_data['context']['turn_count']}")

        # 3. GET /api/v1/ma/profiles/{user_id} - 프로파일 조회
        print("\n[3] GET /api/v1/ma/profiles/user_vip_001 - 프로파일 조회")
        profile_resp = client.get("/api/v1/ma/profiles/user_vip_001", headers=ma_headers)
        assert profile_resp.status_code == 200, f"프로파일 조회 실패: {profile_resp.json()}"
        profile_data = profile_resp.json()
        print("   ✅ 프로파일 조회 성공")
        print(f"      - user_id: {profile_data['user_id']}")
        print(f"      - segment: {profile_data['profile']['segment']}")
        print(f"      - attributes 수: {len(profile_data['profile']['attributes'])}")

        # 4. POST /api/v1/ma/context/turn - 대화 턴 저장 (사용자)
        print("\n[4] POST /api/v1/ma/context/turn - 대화 턴 저장 (사용자)")
        user_turn_resp = client.post(
            "/api/v1/ma/context/turn",
            json={
                "global_session_key": global_session_key,
                "context_id": context_id,
                "turn": {
                    "turn_id": "turn_001",
                    "role": "user",
                    "content": "환율 1400원 이상일 때 100만원 환전해줘",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            },
            headers=ma_headers,
        )
        assert user_turn_resp.status_code == 201, f"대화 턴 저장 실패: {user_turn_resp.json()}"
        user_turn_data = user_turn_resp.json()
        print("   ✅ 사용자 발화 저장 성공")
        print(f"      - turn_id: {user_turn_data['turn_id']}")
        print(f"      - saved_at: {user_turn_data['saved_at']}")

        # 5. PATCH /api/v1/ma/sessions/state - 세션 상태 업데이트
        print("\n[5] PATCH /api/v1/ma/sessions/state - 세션 상태 업데이트")
        state_resp = client.patch(
            "/api/v1/ma/sessions/state",
            json={
                "global_session_key": global_session_key,
                "conversation_id": conversation_id,
                "turn_id": "turn_001",
                "session_state": "talk",
                "state_patch": {"subagent_status": "continue", "last_agent_id": "sa_exchange", "last_agent_type": "task"},
            },
            headers=ma_headers,
        )
        assert state_resp.status_code == 200, f"세션 상태 업데이트 실패: {state_resp.json()}"
        state_data = state_resp.json()
        print("   ✅ 세션 상태 업데이트 성공")
        print(f"      - status: {state_data['status']}")
        print(f"      - updated_at: {state_data['updated_at']}")

        # 6. POST /api/v1/ma/context/turn - 대화 턴 저장 (어시스턴트)
        print("\n[6] POST /api/v1/ma/context/turn - 대화 턴 저장 (어시스턴트)")
        assistant_turn_resp = client.post(
            "/api/v1/ma/context/turn",
            json={
                "global_session_key": global_session_key,
                "context_id": context_id,
                "turn": {
                    "turn_id": "turn_002",
                    "role": "assistant",
                    "content": "100만원을 환전하였습니다.",
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            },
            headers=ma_headers,
        )
        assert assistant_turn_resp.status_code == 201, f"대화 턴 저장 실패: {assistant_turn_resp.json()}"
        assistant_turn_data = assistant_turn_resp.json()
        print("   ✅ 어시스턴트 응답 저장 성공")
        print(f"      - turn_id: {assistant_turn_data['turn_id']}")
        print(f"      - saved_at: {assistant_turn_data['saved_at']}")

        # 7. GET /api/v1/ma/context/history - 대화 이력 조회
        print("\n[7] GET /api/v1/ma/context/history - 대화 이력 조회")
        history_resp = client.get(
            "/api/v1/ma/context/history", params={"global_session_key": global_session_key, "context_id": context_id}, headers=ma_headers
        )
        assert history_resp.status_code == 200, f"대화 이력 조회 실패: {history_resp.json()}"
        history_data = history_resp.json()
        print("   ✅ 대화 이력 조회 성공")
        print(f"      - total_turns: {history_data['total_turns']}")
        print("      - turns:")
        for turn in history_data["turns"]:
            print(f"        [{turn['turn_id']}] {turn['role']}: {turn['content'][:30]}...")

        # 8. POST /api/v1/ma/sessions/close - 세션 종료
        print("\n[8] POST /api/v1/ma/sessions/close - 세션 종료")
        close_resp = client.post(
            "/api/v1/ma/sessions/close",
            json={
                "global_session_key": global_session_key,
                "conversation_id": conversation_id,
                "close_reason": "task_completed",
                "final_summary": "환율 조건부 환전 완료",
            },
            headers=ma_headers,
        )
        assert close_resp.status_code == 200, f"세션 종료 실패: {close_resp.json()}"
        close_data = close_resp.json()
        print("   ✅ 세션 종료 성공")
        print(f"      - status: {close_data['status']}")

        print("\n========== ✅ 데모 시나리오 API 테스트 완료 ==========\n")


class TestDemoAPISummary:
    """데모에서 사용되는 API 목록만 확인"""

    def test_list_demo_apis(self):
        """데모 시나리오에서 사용되는 API 목록 출력"""
        apis = [
            ("POST", "/api/v1/agw/sessions", "세션 생성"),
            ("GET", "/api/v1/ma/sessions/resolve", "세션 조회"),
            ("GET", "/api/v1/ma/profiles/{user_id}", "프로파일 조회"),
            ("POST", "/api/v1/ma/context/turn", "대화 턴 저장"),
            ("GET", "/api/v1/ma/context/history", "대화 이력 조회"),
            ("PATCH", "/api/v1/ma/sessions/state", "세션 상태 업데이트"),
            ("POST", "/api/v1/ma/sessions/close", "세션 종료"),
        ]

        print("\n========== 데모 시나리오 사용 API 목록 ==========")
        for idx, (method, endpoint, description) in enumerate(apis, 1):
            print(f"{idx}. {method:6} {endpoint:40} - {description}")
        print(f"\n총 {len(apis)}개 API 사용")
        print("=" * 60 + "\n")
