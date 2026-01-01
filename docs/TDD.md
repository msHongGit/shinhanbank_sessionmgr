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
| 세션 생성 | `session_service.create_session` | `test_agw_api.py` | ✅ 완료 |
| 세션 조회 | `session_service.resolve_session` | `test_ma_api.py` | ✅ 완료 |
| Local 세션 등록/조회 | `session_service.register_local_session` | `test_ma_api.py` | ✅ 완료 |
| 세션 상태 업데이트 | `session_service.patch_session_state` | `test_ma_api.py` | ✅ 완료 |
| 세션 종료 | `session_service.close_session` | `test_ma_api.py` | ✅ 완료 |
| 대화 이력 조회 | `context_service.get_conversation_history` | `test_ma_api.py` | ✅ 완료 |
| 대화 턴 저장 | `context_service.save_conversation_turn` | `test_ma_api.py` | ✅ 완료 |
| 프로파일 조회 | `profile_service.get_profile` | `test_ma_api.py` | ⚠️ Mock |
| 세션 목록 조회 | Portal API | `test_portal_api.py` | ✅ 완료 |
| Context 삭제 | `context_service.delete_context` | `test_portal_api.py` | ✅ 완료 |
| 프로파일 배치 업로드 | `profile_service.batch_upload` | `test_batch_api.py` | ⚠️ Mock |

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
├── unit/                          # 단위 테스트 (TODO)
│   ├── services/
│   │   ├── test_session_service.py
│   │   ├── test_context_service.py
│   │   └── test_profile_service.py
│   └── utils/
│       └── test_id_generator.py
│
├── integration/                   # 통합 테스트 (TODO)
│   ├── test_redis_integration.py
│   └── test_postgres_integration.py
│
├── api/                           # API 테스트 (현재)
│   ├── test_agw_api.py            # AGW API 테스트
│   ├── test_ma_api.py             # MA API 테스트
│   ├── test_portal_api.py         # Portal API 테스트
│   └── test_batch_api.py          # Batch API 테스트
│
├── e2e/                           # E2E 테스트 (TODO)
│   ├── test_session_lifecycle.py
│   └── test_multiuser_scenario.py
│
├── conftest.py                    # pytest 공통 fixtures
└── test_integration.py            # 통합 테스트
```

---

## 🎭 모킹 전략

### 1. **Redis 모킹**

```python
# conftest.py
@pytest.fixture
def mock_redis():
    """Redis 클라이언트 모킹"""
    from unittest.mock import MagicMock
    
    redis_mock = MagicMock()
    redis_mock.hgetall.return_value = {}
    redis_mock.hset.return_value = True
    redis_mock.delete.return_value = 1
    return redis_mock

# 사용 예시
@patch('app.services.session_service.get_redis_client')
def test_create_session(self, mock_redis, client, agw_headers):
    redis_mock = MagicMock()
    redis_mock.hgetall.return_value = {}  # 기존 세션 없음
    mock_redis.return_value = redis_mock
    
    response = client.post("/api/v1/agw/sessions", ...)
    assert response.status_code == 201
```

### 2. **PostgreSQL 모킹**

```python
@pytest.fixture
def mock_db_session():
    """SQLAlchemy 세션 모킹"""
    from unittest.mock import MagicMock
    
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session
```

### 3. **외부 서비스 모킹**

```python
@pytest.fixture
def mock_profile_client():
    """프로파일 서비스 모킹 (VDB 연동)"""
    from unittest.mock import MagicMock
    
    client = MagicMock()
    client.get_profile.return_value = {
        "user_id": "user_001",
        "segment": "VIP"
    }
    return client
```

---

## 🔬 레이어별 테스트 전략

### 1. **API Layer Tests**

#### A. AGW API 테스트

```python
# tests/test_agw_api.py
class TestAGWSessionCreate:
    """AGW 세션 생성 테스트"""
    
    @patch('app.services.session_service.get_redis_client')
    def test_create_new_session(self, mock_redis, client, agw_headers):
        """새 세션 생성 성공"""
        redis_mock = MagicMock()
        redis_mock.hgetall.return_value = {}
        mock_redis.return_value = redis_mock
        
        response = client.post(
            "/api/v1/agw/sessions",
            json={
                "global_session_key": "gsess_001",
                "user_id": "user_001",
                "channel": "mobile"
            },
            headers=agw_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["is_new"] is True
        assert "conversation_id" in data
        assert "context_id" in data
    
    @patch('app.services.session_service.get_redis_client')
    def test_return_existing_session(self, mock_redis, client, agw_headers):
        """기존 유효 세션 반환"""
        redis_mock = MagicMock()
        redis_mock.hgetall.return_value = {
            "global_session_key": "gsess_001",
            "conversation_id": "conv_001",
            "context_id": "ctx_001",
            "session_state": "talk",
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        mock_redis.return_value = redis_mock
        
        response = client.post("/api/v1/agw/sessions", ...)
        
        assert response.status_code == 201
        assert response.json()["is_new"] is False
    
    def test_unauthorized_without_api_key(self, client):
        """API Key 없이 호출 시 401"""
        response = client.post("/api/v1/agw/sessions", json={...})
        assert response.status_code == 401
    
    def test_forbidden_with_wrong_api_key(self, client, ma_headers):
        """다른 호출자 API Key로 호출 시 403"""
        response = client.post("/api/v1/agw/sessions", json={...}, headers=ma_headers)
        assert response.status_code == 403
```

#### B. MA API 테스트

```python
# tests/test_ma_api.py
class TestMASessionResolve:
    """MA 세션 조회 테스트"""
    
    @patch('app.services.session_service.get_redis_client')
    def test_resolve_session_success(self, mock_redis, client, ma_headers):
        """세션 조회 성공"""
        # Given
        redis_mock = MagicMock()
        redis_mock.hgetall.return_value = {
            "global_session_key": "gsess_001",
            "session_state": "talk",
            "subagent_status": "continue"
        }
        redis_mock.zcard.return_value = 2  # Task Queue 있음
        mock_redis.return_value = redis_mock
        
        # When
        response = client.get(
            "/api/v1/ma/sessions/resolve",
            params={"global_session_key": "gsess_001"},
            headers=ma_headers
        )
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["task_queue_status"] == "notnull"
        assert data["subagent_status"] == "continue"
    
    @patch('app.services.session_service.get_redis_client')
    def test_resolve_session_not_found(self, mock_redis, client, ma_headers):
        """세션 없음 → 404"""
        redis_mock = MagicMock()
        redis_mock.hgetall.return_value = {}
        mock_redis.return_value = redis_mock
        
        response = client.get(
            "/api/v1/ma/sessions/resolve",
            params={"global_session_key": "gsess_invalid"},
            headers=ma_headers
        )
        
        assert response.status_code == 404


class TestMALocalSession:
    """MA Local 세션 테스트"""
    
    def test_register_local_session(self, ...):
        """Local 세션 등록"""
        pass
    
    def test_get_local_session_exists(self, ...):
        """Local 세션 조회 - 존재"""
        pass
    
    def test_get_local_session_not_exists(self, ...):
        """Local 세션 조회 - 없음"""
        pass


class TestMASessionState:
    """MA 세션 상태 업데이트 테스트"""
    
    def test_patch_session_state(self, ...):
        """세션 상태 업데이트 성공"""
        pass
    
    def test_patch_session_not_found(self, ...):
        """없는 세션 업데이트 → 404"""
        pass


class TestMAContext:
    """MA 대화 이력 테스트"""
    
    def test_get_conversation_history(self, ...):
        """대화 이력 조회"""
        pass
    
    def test_save_conversation_turn(self, ...):
        """대화 턴 저장"""
        pass
```

### 2. **Service Layer Tests**

```python
# tests/unit/services/test_session_service.py
class TestSessionService:
    """SessionService 단위 테스트"""
    
    def test_generate_id_format(self):
        """ID 생성 포맷 검증"""
        service = SessionService()
        
        conv_id = service._generate_id("conv")
        ctx_id = service._generate_id("ctx")
        
        assert conv_id.startswith("conv_")
        assert ctx_id.startswith("ctx_")
        assert len(conv_id) > 20  # timestamp + uuid
    
    def test_session_state_transition(self):
        """세션 상태 전이 검증"""
        # START → TALK → END 전이 가능
        # START → END 직접 전이 가능
        pass
    
    def test_subagent_status_values(self):
        """SubAgent 상태값 검증"""
        valid_statuses = ["undefined", "continue", "complete", "error"]
        # 각 상태값이 올바르게 처리되는지 검증
        pass
```

### 3. **Integration Tests**

```python
# tests/integration/test_redis_integration.py
class TestRedisIntegration:
    """Redis 연동 테스트"""
    
    @pytest.fixture
    def redis_client(self):
        """실제 Redis 연결 (테스트 DB)"""
        import redis
        client = redis.Redis(host='localhost', port=6379, db=15)
        yield client
        client.flushdb()  # 테스트 후 정리
    
    def test_session_crud(self, redis_client):
        """세션 CRUD 통합 테스트"""
        helper = RedisHelper(redis_client)
        
        # Create
        helper.set_session("gsess_001", {"user_id": "user_001"})
        
        # Read
        session = helper.get_session("gsess_001")
        assert session["user_id"] == "user_001"
        
        # Delete
        helper.delete_session("gsess_001")
        assert helper.get_session("gsess_001") == {}
```

### 4. **E2E Tests**

```python
# tests/e2e/test_session_lifecycle.py
class TestSessionLifecycle:
    """세션 전체 라이프사이클 테스트"""
    
    @patch('app.db.redis.get_redis_client')
    def test_complete_session_flow(self, mock_redis, client, agw_headers, ma_headers):
        """
        전체 세션 플로우:
        1. AGW: 세션 생성
        2. MA: 세션 조회
        3. MA: Local 세션 등록
        4. MA: 대화 턴 저장
        5. MA: 세션 상태 업데이트
        6. MA: 세션 종료
        """
        # 1. AGW: 세션 생성
        create_resp = client.post(
            "/api/v1/agw/sessions",
            json={"global_session_key": "gsess_e2e", "user_id": "user_001"},
            headers=agw_headers
        )
        assert create_resp.status_code == 201
        session_data = create_resp.json()
        
        # 2. MA: 세션 조회
        resolve_resp = client.get(
            "/api/v1/ma/sessions/resolve",
            params={"global_session_key": "gsess_e2e"},
            headers=ma_headers
        )
        assert resolve_resp.status_code == 200
        
        # 3. MA: Local 세션 등록
        local_resp = client.post(
            "/api/v1/ma/sessions/local",
            json={
                "global_session_key": "gsess_e2e",
                "local_session_key": "lsess_001",
                "agent_id": "agent-transfer"
            },
            headers=ma_headers
        )
        assert local_resp.status_code == 201
        
        # ... 나머지 플로우
    
    def test_multiuser_isolation(self, client, ...):
        """멀티유저 세션 격리 테스트"""
        # 사용자 A, B의 세션이 독립적으로 관리되는지 검증
        pass
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
# tests/test_ma_api.py
def test_01_red_get_session_metadata():
    """
    요구사항: 세션 메타데이터 조회 API
    
    RED 단계: 이 테스트는 실패해야 함 (API 미구현)
    """
    response = client.get(
        "/api/v1/ma/sessions/metadata",
        params={"global_session_key": "gsess_001"},
        headers=ma_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "created_at" in data
    assert "updated_at" in data
```

**테스트 실행**: ❌ 실패 (404 Not Found)

#### Step 2: GREEN - 최소한의 코드로 통과

```python
# app/api/v1/ma/sessions.py
@router.get("/metadata")
async def get_session_metadata(
    global_session_key: str,
    api_key: str = Depends(verify_ma_api_key)
):
    return {
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
```

**테스트 실행**: ✅ 통과

#### Step 3: REFACTOR - 코드 개선

```python
# app/api/v1/ma/sessions.py
@router.get("/metadata", response_model=SessionMetadataResponse)
async def get_session_metadata(
    global_session_key: str,
    api_key: str = Depends(verify_ma_api_key),
    session_service: SessionService = Depends(get_session_service)
):
    """세션 메타데이터 조회"""
    return session_service.get_session_metadata(global_session_key)
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
| Integration Tests | 60%+ | ⚠️ TODO |
| API Tests | 90%+ | ✅ ~85% |
| E2E Tests | 주요 시나리오 100% | ⚠️ TODO |

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
        "conversation_id": "conv_001",
        "context_id": "ctx_001"
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
