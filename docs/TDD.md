# Session Manager - TDD 전략 / Test-Driven Development Strategy

> **🎯 핵심 원칙: Session Manager는 TDD(Test-Driven Development) 방식으로 개발됩니다.**

모든 핵심 기능은 **Red-Green-Refactor 사이클**을 따라 개발되며, 테스트 코드가 설계와 문서 역할을 동시에 수행합니다.

---

## 📋 목차
1. [TDD 적용 현황](#tdd-적용-현황)
2. [테스트 피라미드](#테스트-피라미드)
3. [테스트 구조](#테스트-구조)
4. [모킹 전략](#모킹-전략)
5. [레이어별 테스트 전략](#레이어별-테스트-전략)
6. [테스트 실행 전략](#테스트-실행-전략)
7. [CI/CD 통합](#cicd-통합)

---

## 🚀 TDD 적용 현황

### ✅ TDD로 개발된 주요 기능들

Session Manager의 **핵심 기능들은 TDD 방식으로 개발**됩니다:

| 기능 | 서비스 | 테스트 파일 | 상태 |
|------|--------|------------|------|
| 세션 생성 | `session_service.create_session` | `test_sessions_api.py` | ✅ 완료 |
| 세션 조회 | `session_service.resolve_session` | `test_sessions_api.py` | ✅ 완료 |
| 세션 상태 업데이트 | `session_service.patch_session_state` | `test_sessions_api.py` | ✅ 완료 |
| 세션 종료 | `session_service.close_session` | `test_sessions_api.py` | ✅ 완료 |
| 멀티턴 컨텍스트 저장/조회 | `session_service.patch_session_state` / `resolve_session` | `test_sessions_api.py` | ✅ 완료 |
| SOL API 결과 저장 | `contexts.save_sol_api_result` | `test_context_api.py` | ✅ 완료 |
| 세션 전체 정보 조회 | `contexts.get_session_full` | `test_context_api.py` | ✅ 완료 |
| E2E 세션 라이프사이클 | 전체 플로우 | `test_integration.py` | ✅ 완료 |
| 프로파일 조회 | `profile_service.get_profile` | Mock 사용 | ⚠️ Mock |

---

## 🎯 테스트 피라미드

```
           /\
          /  \
         / E2E \        ← 소수 (10-20%)
        /--------\         전체 API 플로우
       / Integration \  ← 중간 (30-40%)
      /--------------\     Redis + Service 연동
     /   Unit Tests    \ ← 다수 (40-60%)
    /------------------\   순수 비즈니스 로직
```

### 1. **Unit Tests (40-60%)**
- **대상**: Service 클래스의 순수 로직, 유틸리티 함수
- **목표**: 빠른 피드백 (< 1초)
- **예시**: ID 생성, 상태 전이 로직, 유효성 검증

### 2. **Integration Tests (30-40%)**
- **대상**: Service + Redis, API 엔드포인트
- **목표**: 컴포넌트 간 통합 검증
- **예시**: 세션 생성 → Redis 저장 → 조회 플로우

### 3. **E2E Tests (10-20%)**
- **대상**: 전체 세션 라이프사이클
- **목표**: 실제 사용 시나리오 검증
- **예시**: AGW 세션 생성 → MA 조회 → 상태 업데이트 → 종료

---

## 📁 테스트 구조

```
tests/
├── test_sessions_api.py            # Unified Sessions API 테스트 (현재)
│   ├── TestMultiTurnConversationHistory
│   ├── TestHealthCheck
│   ├── TestSessionCreate
│   ├── TestSessionResolve
│   ├── TestSessionStatePatch
│   └── TestSessionClose
│
├── test_context_api.py             # Contexts API 테스트 (현재)
│   ├── test_save_sol_api_result_as_turn_metadata
│   └── test_get_session_full_info
│
├── test_integration.py             # E2E 통합 테스트 (현재)
│   └── TestSessionLifecycle
│
├── conftest.py                     # pytest 공통 fixtures
│
└── unit/                           # 단위 테스트 (향후)
    ├── services/
    │   ├── test_session_service.py
    │   └── test_profile_service.py
    └── utils/
        └── test_utils.py
```

---

## 🎭 모킹 전략

### 1. **Mock Repository 사용**

```python
# conftest.py
@pytest.fixture
def client():
    """FastAPI TestClient using real Redis for sessions/contexts and Mock profile data."""
    from app.repositories.mock import MockProfileRepository
    from app.services.session_service import SessionService
    
    profile_repo = MockProfileRepository()
    
    def override_session_service():
        return SessionService(profile_repo=profile_repo)
    
    app.dependency_overrides[get_session_service] = override_session_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

**현재 모킹 전략**:
- **Redis**: 실제 Redis 사용 (로컬/CI 환경)
- **Profile Repository**: MockProfileRepository 사용 (테스트용 고정 데이터)

---

## 🔬 레이어별 테스트 전략

### 1. **API Layer Tests**

#### A. Unified Sessions API 테스트

```python
# tests/test_sessions_api.py
class TestSessionCreate:
    """세션 생성 테스트"""
    
    def test_create_session_success_with_agw(self, client, agw_headers):
        """AGW 헤더로 세션 생성 성공"""
        response = client.post(
            "/api/v1/sessions",
            json={"userId": "user_001"},
            headers=agw_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "global_session_key" in data
        assert data["global_session_key"].startswith("gsess_")
    
    def test_create_session_without_profile(self, client, agw_headers):
        """프로파일 없이 세션 생성"""
        response = client.post(
            "/api/v1/sessions",
            json={"userId": "user_no_profile"},
            headers=agw_headers
        )
        assert response.status_code == 201


class TestSessionResolve:
    """세션 조회 테스트"""
    
    def test_resolve_session_success(self, client, agw_headers, ma_headers):
        """세션 조회 성공"""
        # Given: 세션 생성
        create_resp = client.post("/api/v1/sessions", json={"userId": "user_001"}, headers=agw_headers)
        global_session_key = create_resp.json()["global_session_key"]
        
        # When: 세션 조회
        response = client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=ma_headers
        )
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["global_session_key"] == global_session_key
        assert data["session_state"] == "start"
    
    def test_resolve_session_not_found(self, client, ma_headers):
        """세션 없음 → 404"""
        response = client.get(
            "/api/v1/sessions/gsess_invalid",
            headers=ma_headers
        )
        assert response.status_code == 404


class TestSessionStatePatch:
    """세션 상태 업데이트 테스트"""
    
    def test_patch_session_state(self, client, agw_headers, ma_headers):
        """세션 상태 업데이트 성공"""
        # Given: 세션 생성
        create_resp = client.post("/api/v1/sessions", json={"userId": "user_001"}, headers=agw_headers)
        global_session_key = create_resp.json()["global_session_key"]
        
        # When: 상태 업데이트
        patch_req = {
            "global_session_key": global_session_key,
            "turn_id": "turn_001",
            "session_state": "talk",
            "state_patch": {
                "subagent_status": "continue",
                "reference_information": {
                    "conversation_history": [{"role": "user", "content": "안녕"}],
                    "current_intent": "인사"
                }
            }
        }
        response = client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json=patch_req,
            headers=ma_headers
        )
        
        # Then
        assert response.status_code == 200
        assert response.json()["status"] == "success"


class TestMultiTurnConversationHistory:
    """멀티턴 대화 이력 테스트"""
    
    def test_multiturn_conversation_history_patch_and_get(self, client, agw_headers, ma_headers):
        """PATCH로 conversation_history 저장 후 GET에서 조회"""
        # 세션 생성 → PATCH로 대화 이력 저장 → GET으로 조회 검증
        pass
    
    def test_multiturn_turn_ids_accumulate(self, client, agw_headers, ma_headers):
        """turn_ids 누적 검증"""
        pass
```

#### B. Contexts API 테스트

```python
# tests/test_context_api.py
def test_save_sol_api_result_as_turn_metadata(client, agw_headers, ma_headers):
    """SOL API 결과를 턴 메타데이터로 저장"""
    # 1. 세션 생성
    session_resp = client.post("/api/v1/sessions", json={"userId": "user_001"}, headers=agw_headers)
    global_session_key = session_resp.json()["global_session_key"]
    
    # 2. SOL API 결과 저장
    response = client.post(
        "/api/v1/contexts/turn-results",
        json={
            "sessionId": global_session_key,
            "turnId": "turn_001",
            "agent": "dbs_caller",
            "transactionResult": [{"trxCd": "TRX001", "responseData": {}}]
        }
    )
    
    assert response.status_code == 201
    assert response.json()["turn_id"] == "turn_001"


def test_get_session_full_info(client, agw_headers, ma_headers):
    """세션 전체 정보 조회 (세션 + 턴 목록)"""
    # 세션 생성 → 턴 저장 → 전체 정보 조회 검증
        pass
```

### 2. **Service Layer Tests**

```python
# tests/unit/services/test_session_service.py (향후)
class TestSessionService:
    """SessionService 단위 테스트"""
    
    def test_generate_id_format(self):
        """ID 생성 포맷 검증"""
        service = SessionService()
        
        global_key = service._generate_id("gsess")
        ctx_id = service._generate_id("ctx")
        
        assert global_key.startswith("gsess_")
        assert ctx_id.startswith("ctx_")
        assert len(global_key) > 20  # timestamp + uuid
    
    def test_session_state_transition(self):
        """세션 상태 전이 검증"""
        # START → TALK → END 전이 가능
        # START → END 직접 전이 가능
        pass
    
    def test_reference_information_validation(self):
        """reference_information 타입 검증"""
        # conversation_history는 list여야 함
        # turn_count는 int여야 함
        pass
```

### 3. **Integration Tests**

```python
# tests/test_integration.py
class TestSessionLifecycle:
    """세션 전체 라이프사이클 통합 테스트"""
    
    def test_full_session_lifecycle(self, client, agw_headers, ma_headers):
        """세션 생성 → 조회 → 업데이트 → 종료"""
        # 1. 세션 생성
        create_resp = client.post("/api/v1/sessions", json={"userId": "user_001"}, headers=agw_headers)
        global_session_key = create_resp.json()["global_session_key"]
        
        # 2. 세션 조회
        resolve_resp = client.get(f"/api/v1/sessions/{global_session_key}", headers=ma_headers)
        assert resolve_resp.status_code == 200
        
        # 3. 세션 상태 업데이트
        patch_resp = client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json={"global_session_key": global_session_key, "session_state": "talk"},
            headers=ma_headers
        )
        assert patch_resp.status_code == 200
        
        # 4. 세션 종료
        close_resp = client.delete(f"/api/v1/sessions/{global_session_key}", headers=ma_headers)
        assert close_resp.status_code == 200
```

### 4. **E2E Tests**

```python
# tests/test_integration.py
class TestSessionLifecycle:
    """세션 전체 라이프사이클 E2E 테스트"""
    
    def test_full_session_lifecycle(self, client, agw_headers, ma_headers):
        """
        전체 세션 플로우:
        1. 세션 생성 (POST /api/v1/sessions)
        2. 세션 조회 (GET /api/v1/sessions/{key})
        3. 세션 상태 업데이트 (PATCH /api/v1/sessions/{key}/state)
        4. SOL API 결과 저장 (POST /api/v1/contexts/turn-results)
        5. 세션 전체 정보 조회 (GET /api/v1/contexts/sessions/{key}/full)
        6. 세션 종료 (DELETE /api/v1/sessions/{key})
        """
        # 1. 세션 생성
        create_resp = client.post(
            "/api/v1/sessions",
            json={"userId": "user_e2e_001"},
            headers=agw_headers
        )
        assert create_resp.status_code == 201
        global_session_key = create_resp.json()["global_session_key"]
        
        # 2. 세션 조회
        resolve_resp = client.get(
            f"/api/v1/sessions/{global_session_key}",
            headers=ma_headers
        )
        assert resolve_resp.status_code == 200
        
        # 3. 세션 상태 업데이트
        patch_resp = client.patch(
            f"/api/v1/sessions/{global_session_key}/state",
            json={
                "global_session_key": global_session_key,
                "turn_id": "turn_001",
                "session_state": "talk",
                "state_patch": {
                    "reference_information": {
                        "conversation_history": [{"role": "user", "content": "안녕"}]
                    }
                }
            },
            headers=ma_headers
        )
        assert patch_resp.status_code == 200
        
        # 4. SOL API 결과 저장
        sol_resp = client.post(
            "/api/v1/contexts/turn-results",
            json={
                "sessionId": global_session_key,
                "turnId": "turn_001",
                "agent": "dbs_caller"
            }
        )
        assert sol_resp.status_code == 201
        
        # 5. 세션 전체 정보 조회
        full_resp = client.get(
            f"/api/v1/contexts/sessions/{global_session_key}/full"
        )
        assert full_resp.status_code == 200
        assert "session" in full_resp.json()
        assert "turns" in full_resp.json()
        
        # 6. 세션 종료
        close_resp = client.delete(
            f"/api/v1/sessions/{global_session_key}",
            params={"close_reason": "test_completed"},
            headers=ma_headers
        )
        assert close_resp.status_code == 200
```

---

## 🚀 테스트 실행 전략

### 1. **로컬 개발**

```bash
# 전체 테스트 실행
pytest tests/ -v

# 특정 API 테스트만
pytest tests/test_ma_api.py -v

# 특정 클래스만
pytest tests/test_ma_api.py::TestMASessionResolve -v

# 특정 테스트만
pytest tests/test_ma_api.py::TestMASessionResolve::test_resolve_session_success -v

# 커버리지
pytest tests/ --cov=app --cov-report=html
```

### 2. **마커 기반 실행**

```python
# pytest.ini
[pytest]
markers =
    unit: 단위 테스트 (빠름)
    integration: 통합 테스트 (Redis 필요)
    e2e: E2E 테스트 (전체 스택)
    slow: 느린 테스트
```

```bash
# 단위 테스트만
pytest -m unit

# 통합 테스트 제외
pytest -m "not integration"

# 빠른 테스트만
pytest -m "not slow"
```

---

## 🔄 Red-Green-Refactor 사이클

### 실제 적용 예시: 새 API 추가

#### Step 1: RED - 실패하는 테스트 작성

```python
# tests/test_sessions_api.py
def test_01_red_session_ping():
    """
    요구사항: 세션 생존 확인 및 TTL 연장 API
    
    RED 단계: 이 테스트는 실패해야 함 (API 미구현)
    """
    # Given: 세션 생성
    create_resp = client.post("/api/v1/sessions", json={"userId": "user_001"}, headers=agw_headers)
    global_session_key = create_resp.json()["global_session_key"]
    
    # When: Ping 호출
    response = client.get(
        f"/api/v1/sessions/{global_session_key}/ping"
    )
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert "is_alive" in data
    assert data["is_alive"] is True
```

**테스트 실행**: ❌ 실패 (404 Not Found)

#### Step 2: GREEN - 최소한의 코드로 통과

```python
# app/api/v1/sessions.py
@router.get("/{global_session_key}/ping")
async def ping_session(global_session_key: str):
    return {"is_alive": True, "expires_at": datetime.now().isoformat()}
```

**테스트 실행**: ✅ 통과

#### Step 3: REFACTOR - 코드 개선

```python
# app/api/v1/sessions.py
@router.get("/{global_session_key}/ping", response_model=SessionPingResponse)
async def ping_session(
    global_session_key: str,
    service: SessionService = Depends(get_session_service),
):
    """세션 생존 확인 및 TTL 연장"""
    return service.ping_session(global_session_key)
```

**테스트 실행**: ✅ 모든 테스트 통과

---

## 🔧 CI/CD 통합

### GitHub Actions 워크플로우

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Lint with Ruff
        run: |
          pip install ruff
          ruff check .
      
      - name: Run tests
        run: pytest tests/ -v --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### PR Gate 규칙

- ❌ 테스트 실패 시 머지 차단
- ❌ 커버리지 80% 미만 시 경고
- ❌ Lint 실패 시 머지 차단

---

## 📊 테스트 커버리지 목표

| 레이어 | 목표 | 현재 |
|--------|------|------|
| Unit Tests | 80%+ | ⚠️ TODO |
| Integration Tests | 60%+ | ✅ ~70% (test_integration.py) |
| API Tests | 90%+ | ✅ ~90% (test_sessions_api.py, test_context_api.py) |
| E2E Tests | 주요 시나리오 100% | ✅ 완료 (test_integration.py) |

---

## 💡 베스트 프랙티스

### 1. **테스트 명명 규칙**

```python
# 패턴: test_<기능>_<시나리오>
def test_create_session_success():
def test_create_session_already_exists():
def test_resolve_session_not_found():
def test_patch_session_invalid_state():
```

### 2. **Given-When-Then 패턴**

```python
def test_resolve_session_with_local_session(self, mock_redis, client, ma_headers):
    """Local 세션이 있는 경우 함께 반환"""
    # Given: 세션과 Local 매핑이 존재
    redis_mock = MagicMock()
    redis_mock.hgetall.side_effect = [
        {"global_session_key": "gsess_001", "session_state": "talk"},  # 세션
        {"local_session_key": "lsess_001", "agent_id": "agent-transfer"}  # 매핑
    ]
    mock_redis.return_value = redis_mock
    
    # When: MA가 세션 조회
    response = client.get(
        "/api/v1/ma/sessions/resolve",
        params={"global_session_key": "gsess_001", "agent_id": "agent-transfer"},
        headers=ma_headers
    )
    
    # Then: Local 세션 키도 함께 반환
    assert response.status_code == 200
    assert response.json()["local_session_key"] == "lsess_001"
```

### 3. **Fixture 재사용**

```python
# conftest.py에 공통 fixture 정의
@pytest.fixture
def sample_session_data():
    return {
        "global_session_key": "gsess_001",
        "user_id": "user_001",
        "session_state": "talk",
        "conversation_id": "conv_001"
    }

# 테스트에서 재사용
def test_something(sample_session_data):
    assert sample_session_data["session_state"] == "talk"
```

### 4. **테스트 격리**

```python
# 각 테스트는 독립적으로 실행 가능해야 함
@pytest.fixture(autouse=True)
def reset_state():
    """각 테스트 전후로 상태 초기화"""
    yield
    # Cleanup
```

---

## 📝 체크리스트

### 새 기능 개발 시

- [ ] 실패하는 테스트 먼저 작성 (RED)
- [ ] 최소 구현으로 통과 (GREEN)
- [ ] 리팩토링 후 테스트 통과 확인 (REFACTOR)
- [ ] 엣지 케이스 테스트 추가
- [ ] 커버리지 확인 (80% 이상)
- [ ] Ruff 린트 통과

### 버그 수정 시

- [ ] 버그 재현하는 테스트 먼저 작성
- [ ] 테스트 실패 확인
- [ ] 버그 수정
- [ ] 테스트 통과 확인
- [ ] 관련 테스트 모두 통과 확인

---

## 🔗 참고 자료

- [pytest 문서](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Redis 테스트 패턴](https://redis.io/docs/manual/patterns/)

---

## 📝 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-01 | 초기 작성 |
