# Session Manager v4.0 - Sprint 2

은행 AI Agent 시스템의 세션 관리 서비스

> **Sprint 1**: 설계 및 아키텍처 정의  
> **Sprint 2**: Mock Repository 기반 구현 (현재)

## 🎯 Sprint 2 목표

- Mock Repository 기반 In-Memory 세션 관리 구현
- Repository Pattern + Dependency Injection 구조 확립
- FastAPI 기반 REST API 제공
- TDD 기반 개발 (pytest)
- 향후 확장 가능한 구조 설계

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Session Manager                       │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                        │
│    ├─ AGW API     : 초기 세션 생성                           │
│    ├─ MA API      : 세션 조회/업데이트, Context, Profile      │
│    ├─ Portal API  : 세션 목록 조회 (읽기전용)                │
│    └─ Batch API   : VDB 프로파일 배치 업로드                 │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                              │
│    ├─ SessionService  : 세션 관리 비즈니스 로직              │
│    ├─ ContextService  : 대화 이력 관리                       │
│    └─ ProfileService  : 고객 프로파일 관리                   │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer (Sprint 2: Mock / 향후: PostgreSQL+Redis)│
│    ├─ MockSessionRepository  : Dict 기반 세션 저장소        │
│    ├─ MockContextRepository  : Dict 기반 Context 저장소     │
│    └─ MockProfileRepository  : Dict 기반 Profile 저장소     │
│  📌 확장 가능: PostgreSQL/Redis Repository로 교체 가능      │
└─────────────────────────────────────────────────────────────┘
```

## 📁 디렉토리 구조

```
app/
  api/v1/
    agw/        # Agent GW API
    batch/      # Batch API (VDB)
  services/     # 비즈니스 로직
  repositories/ # Repository 인터페이스 및 구현체
    mock/       # Mock Repository (Sprint 2)
    postgres/   # PostgreSQL Repository (Sprint 3+)
    redis/      # Redis Repository (Sprint 3+)
  schemas/      # Pydantic 스키마
  models/       # SQLAlchemy 모델 (Sprint 3+)
  core/         # 예외 처리
  db/           # DB 연결 (Sprint 3
  db/           # DB 연결 (Sprint 2+)
tests/          # pytest 테스트
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# uv 환경 구성
uv sync --all-extras

# 서버 실행
uv run uvicorn app.main:app --port 8080 --reload
```

### 2. API 문서 확인

```
http://localhost:8080/api/v1/docs
```

### 3. 테스트 실행

```bash
# 전체 테스트
uv run pytest tests/ -v

# 데모 시나리오 테스트 (Sprint 2 데모용)
uv run pytest tests/test_demo_scenario.py -v -s

# API별 테스트
uv run pytest tests/test_agw_api.py -v
uv run pytest tests/test_ma_api.py -v
uv run pytest tests/test_batch_api.py -v

# 통합 테스트
uv run pytest tests/test_integration.py -v
```

> **데모 시나리오 테스트**: `tests/test_demo_scenario.py`는 Sprint 2 데모에서 사용되는 7개 API만 순차적으로 테스트합니다.
> 상세 내용은 [DEMO_SCENARIO_V2.md](docs/DEMO_SCENARIO_V2.md) 참고


## 🔑 Sprint 2 인증 정책

Sprint 2 dev/demo 환경에서는 **API Key 인증이 비활성화**되어 있습니다.

- `.env`에서 `ENABLE_API_KEY_AUTH=false`로 설정되어 있으면, 모든 API는 인증 없이 호출 가능합니다.
- 운영/보안 환경에서는 `ENABLE_API_KEY_AUTH=true`로 변경 후, 각 호출자별 API Key를 반드시 설정해야 합니다.

| 호출자 | 헤더 | API Key (운영시) |
|--------|------|-----------------|
| AGW    | X-API-Key | agw-api-key    |
| MA     | X-API-Key | ma-api-key     |
| Portal | X-API-Key | portal-api-key |
| VDB    | X-API-Key | vdb-api-key    |

> Sprint 2 dev/demo에서는 X-API-Key 헤더 없이 호출해도 정상 동작합니다. 운영 전환 시에만 인증을 활성화하세요.

✅ **Repository Pattern**
- ABC 인터페이스 정의 (base.py)
- Mock 구현체 (Singleton, Dict 저장소)
- DI를 통한 Mock/Real Repository 전환 가능
- **모든 메서드 Sync 방식** (Sprint 2 기준)

✅ **Service Layer**
- SessionService (v4.0 - Sync)
- ContextService (v4.0 - Sync)
- ProfileService (v4.0 - Sync)
- Repository 의존성 주입

✅ **API Layer**
- 3개 호출자별 API 분리 (AGW, MA, Batch)
- API Key 기반 인증
- **모든 핸들러 Sync 함수**
- FastAPI 예외 처리

✅ **테스트**
- 14개 테스트 전체 통과
- AGW, MA, Batch, Portal API 테스트
- Integration 테스트 (세션 생명주기)
- **데모 시나리오 테스트** (`test_demo_scenario.py` - 7개 API 순차 실행)
- Mock Repository 기반 격리 테스트

✅ **시연 준비**
- API 정의서 (docs/DEMO_API_SPEC.md)
- 시나리오 플로우 (docs/DEMO_SCENARIO.md)
- SubAgent 상태 전이 로직

## 🎯 Sprint 3 계획 (향후 확장)

### 1. PostgreSQL Repository 구현
- SessionRepository (SQLAlchemy Sync)
- ContextRepository (SQLAlchemy Sync)
- ProfileRepository (SQLAlchemy Sync)
- Alembic 마이그레이션

### 2. Redis Repository 구현
- 세션 캐싱 (Sync - redis-py)
- Local 세션 매핑 (Global ↔ Local)
- Hybrid Repository (Redis + PostgreSQL)

### 3. 고급 기능
- Task Queue 관리 (Redis Sorted Set)
- 세션 만료 처리 (스케줄러)
- 실시간 이벤트 스트리밍 (SSE/WebSocket)

### 4. CI/CD 파이프라인
- GitHub Actions
- Az확장 가능한 아키텍처
- **Sprint 2**: Mock Repository로 빠른 검증
- **Sprint 3+**: PostgreSQL/Redis로 확장 가능
- Repository Pattern 덕분에 구현체 교체 용이

### Sync vs Async
- **현재 (Sprint 2)**: 외부 연동이 모두 Sync이므로 Sync로 구현
- **향후 확장**: 필요시 Async로 전환 가능 (Repository Pattern 덕분에 쉽게 교체)
- FastAPI는 Sync/Async 모두 완벽 지원

### Repository Pattern
- ABC 인터페이스로 Mock/Real 전환 용이
- Sprint 2: Mock Repository (In-Memory)
- Sprint 3+: PostgreSQL/Redis Repository (Sync)
- 구현체만 교체하면 되므로 Service/API Layer는 변경 없음
### Sync vs Async
- **Sprint 1**: 외부 연동이 모두 Sync이므로 Sync로 구현
- **향후 확장**: 필요시 Async로 전환 가능 (Repository Pattern 덕분에 쉽게 교체 가능)
- FastAPI는 Sync/Async 모두 완벽 지원

### Repository Pattern
- ABC 인터페이스로 Mock/Real 전환 용이
- Sprint 1: Mock Repository (In-Memory)
- Sprint 2: PostgreSQL/Redis Repository (Sync)

## 🛠️ 기술 스택

- **Web Framework**: FastAPI 0.109.0
- **Package Manager**: uv
- **ORM**: SQLAlchemy 2.0.25 (Sprint 2+)
- **Cache**: Redis 5.0.1 (Sprint 2+)
- **Testing**: pytest 9.0.2
- **Linting**: Ruff 0.14.10
- **Python**: 3.11+

## 📝 Coding Conventions

- 파일명: snake_case
- 클래스명: PascalCase
- 함수명: snake_case
- 상수명: UPPER_CASE
- 코드 라인 길이: 140자 이하
- PEP8 준수 (Ruff로 강제)

## � Sprint 2 API 필수값 정리

### 데모에서 사용하는 6개 API 필수/옵션 필드

1. **POST /api/v1/agw/sessions** (세션 생성)
   - 필수: `user_id`, `channel`
   - 옵션: `request_id`, `device_info`, `customer_profile`
   - 참고: `global_session_key`는 Session Manager가 자동 생성하여 응답에 포함

2. **GET /api/v1/ma/sessions/resolve** (세션 조회)
   - 필수: `global_session_key` (query)
   - 옵션: `channel`, `agent_type`, `agent_id`

3. **GET /api/v1/ma/profiles/{user_id}** (프로파일 조회)
   - 필수: `user_id` (path)

4. **POST /api/v1/ma/context/turn** (대화 턴 저장)
   - 필수: `global_session_key`, `context_id`, `turn`
   - turn 필수 필드: `turn_id`, `role`, `content`, `timestamp`

5. **GET /api/v1/ma/context/history** (대화 이력 조회)
   - 필수: `global_session_key`, `context_id` (query)

6. **PATCH /api/v1/ma/sessions/state** (세션 상태 업데이트)
   - 필수: `global_session_key`, `conversation_id`, `turn_id`, `session_state`, `state_patch`
   - state_patch: 객체는 필수, 내부 필드는 모두 옵션

7. **POST /api/v1/ma/sessions/close** (세션 종료)
   - 필수: `global_session_key`, `conversation_id`, `close_reason`
   - 옵션: `final_summary`

> 상세 API 명세는 `/api/v1/docs` (Swagger UI) 참고

## �📄 라이센스

Proprietary - Shinhan Bank
