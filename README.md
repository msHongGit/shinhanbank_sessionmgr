# Session Manager v4.0 - Sprint 3

은행 AI Agent 시스템의 세션/컨텍스트 관리 서비스

> **Sprint 1**: 설계 및 아키텍처 정의  
> **Sprint 2**: Mock Repository 기반 API 검증  
> **Sprint 3**: Unified Sessions + SOL 연동 결과 메타데이터(Contexts/Turns), Redis 기반 세션/컨텍스트 관리 (현재 / MariaDB 미사용)

## 🎯 Sprint 3 목표

- Unified Session API로 호출자별 세션 API 통합 (`/api/v1/sessions`)
- 세션/컨텍스트/턴/프로파일 메타데이터 모델 정리
- 대화 텍스트 미저장 설계 반영 (메타데이터만 저장)
- Redis 기반 세션/컨텍스트 저장소 및 Agent 세션 매핑 구현
- FastAPI + pytest 기반 테스트/문서 정비 (Session_Manager_API_Sprint3.md)

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Session Manager                      │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                        │
│    ├─ Unified Sessions API : 세션 생성/조회/상태변경/종료     │
│    └─ Contexts API        : SOL 실시간 API 연동 결과 메타데이터 저장 │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                               │
│    ├─ SessionService  : 세션/Agent 세션 매핑 비즈니스 로직   │
│    ├─ ContextService  : 컨텍스트/턴 메타데이터 관리          │
│    └─ ProfileService  : 고객 프로파일 조회/연결              │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer                                            │
│    ├─ RedisSessionRepository   : Redis 기반 세션/매핑 저장소  │
│    ├─ RedisContextRepository   : Redis 기반 컨텍스트/턴 저장소│
│    └─ Mock*Repository          : 테스트/개발용 Mock 구현체    │
└─────────────────────────────────────────────────────────────┘
```

## 📁 디렉토리 구조

```
app/
   api/
      v1/
         sessions.py      # Unified Sessions API
         contexts.py      # SOL 실시간 API 결과 저장(turn-results)
         router.py        # v1 라우터 집합
   services/            # 비즈니스 로직
      session_service.py
      context_service.py
      profile_service.py
   repositories/        # Repository 인터페이스 및 구현체
      redis_*_repository.py
      hybrid_*_repository.py
      mock/              # 테스트/개발용 Mock Repository
   schemas/             # Pydantic 스키마 (sessions, contexts 등)
   models/              # SQLAlchemy 모델 (향후 RDB/Context DB용, 현재 미사용)
   core/                # 예외, 인증, 정책
   db/                  # DB/Redis 연결
   main.py              # FastAPI 엔트리포인트
tests/
   test_sessions_api.py
   test_context_api.py
   test_agent_sessions_api.py
   test_integration.py
docs/
   Session_Manager_API_Sprint3.md  # Sprint 3 API 명세
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# uv 환경 구성
uv sync --all-extras

# 서버 실행 (기본 포트 5000, Redis 연결 필요)
uv run uvicorn app.main:app --reload --port 5000
```

### 2. API 문서 확인

```
http://localhost:5000/api/v1/docs
```

### 3. 테스트 실행

```bash
# 전체 테스트
uv run pytest tests/ -v
```
> 주요 테스트는 `tests/test_sessions_api.py`, `tests/test_context_api.py`, `tests/test_agent_sessions_api.py`, `tests/test_integration.py` 로 구성되어 있습니다.


## 🔑 인증/저장소 정책 (Sprint 3 기준)

- 설계 상은 호출자별 API Key 헤더를 사용합니다.
   - 헤더: `X-API-Key: {CALLER_API_KEY}`
   - AGW/MA/Portal/VDB/External 용 키는 환경변수(`AGW_API_KEY`, `MA_API_KEY` 등)로 주입
- 현재 Sprint 3 개발/테스트 환경에서는 `ENABLE_API_KEY_AUTH=false` 설정으로
   - Sessions/Contexts API는 인증 없이 호출 가능
   - 운영 전환 시 `ENABLE_API_KEY_AUTH=true` + `require_api_key` 의존성 복구를 전제로 합니다.

### 저장소/TTL

- 세션/컨텍스트/턴은 Redis 하나만 사용 (MariaDB Context DB는 아직 연동하지 않음)
- 주요 TTL (기본값, `.env` 로 오버라이드 가능)
   - `SESSION_CACHE_TTL=600` 초: 세션 스냅샷(`session:{global_session_key}`) 만료 시간
   - `SESSION_MAP_TTL=600` 초: Global↔Agent 세션 매핑(`session_map:{global_session_key}:{agent_id}`) 만료 시간
   - 세션 종료 API 호출 없이 아무 동작이 없으면 TTL 기준으로 Redis에서 자동 삭제됨

✅ **Repository Pattern**
- 공통 인터페이스 정의 (`repositories/base.py`)
- Redis/Hybrid/Mock 구현체 공존
- DI를 통해 환경별 저장소 구현체 교체 가능

✅ **Service Layer**
- SessionService (v4.0 - Sync)
- ContextService (v4.0 - Sync)
- ProfileService (v4.0 - Sync)
- Repository 의존성 주입

-✅ **API Layer**
- Unified Sessions API (`/api/v1/sessions`)
   - 세션 생성/조회/상태 업데이트/종료, Ping(생존 확인 및 TTL 연장)
   - 멀티턴 컨텍스트 지원: PATCH state에서 reference_information 을 저장하고,
     GET 세션 조회 응답에서 옵션 A 구조로 노출 (active_task, conversation_history, current_intent 등)
- SOL 실시간 API 결과 저장 API (`/api/v1/contexts/turn-results`)
   - SOL RequestParam + DBSTrxResponse 전체를 턴 메타데이터로 저장 (텍스트 미저장)
- Swagger UI (`/api/v1/docs`) 기반 자동 문서화 (필수/주요 필드 설명 포함)

✅ **테스트**
- pytest 기반 단위/통합 테스트
- Sessions/Contexts/Agent 세션 매핑 시나리오 검증
- Redis 기반 저장소를 사용하는 통합 테스트 포함

✅ **시연 준비**
- API 정의서 (docs/DEMO_API_SPEC.md)
- 시나리오 플로우 (docs/DEMO_SCENARIO.md)
- SubAgent 상태 전이 로직

## 🎯 향후 확장 (Sprint 4+ 아이디어)

- MariaDB/PostgreSQL 기반 영구 세션/컨텍스트 저장소 구현
- Task Queue 관리, 세션 만료 처리, 배치/리플레이 기능
- 실시간 이벤트 스트리밍 (SSE/WebSocket 등)
- CI/CD 파이프라인 고도화 및 온프렘/에어갭 배포 자동화

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

## 📚 참고 문서

- `docs/Session_Manager_API_Sprint3.md` – Sprint 3 기준 상세 API 명세
- `docs/SPRINT3_DESIGN_FINAL.md` – 설계/도메인 개념 정리
- `docs/session_manager_onprem_migration.md` – 온프렘/에어갭 배포 가이드

## �📄 라이센스

Proprietary - Shinhan Bank
