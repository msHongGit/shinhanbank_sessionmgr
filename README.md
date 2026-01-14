# Session Manager v4.0 - Sprint 4

은행 AI Agent 시스템의 세션/컨텍스트 관리 서비스

> **Sprint 1**: 설계 및 아키텍처 정의  
> **Sprint 2**: Mock Repository 기반 API 검증  
> **Sprint 3**: Unified Sessions + SOL 연동 결과 메타데이터(Contexts/Turns), Redis 기반 세션/컨텍스트 관리  
> **Sprint 4**: MariaDB 영구 저장소 통합, 필드명 통일, Context DB 구축

## 🎯 주요 기능

### 세션 관리
- **세션 생성/조회/업데이트/종료**: Unified Sessions API (`/api/v1/sessions`)
- **세션 상태 관리**: start / talk / end
- **SubAgent 상태**: undefined / continue / end
- **TTL 연장**: Ping API로 세션 생존 확인 및 자동 연장

### 멀티턴 컨텍스트
- **PATCH 업데이트**: `state_patch.reference_information` 으로 대화 이력 저장
- **GET 조회**: conversation_history, current_intent, turn_count 등 자동 파싱
- **타입 검증**: PATCH 시점에 타입을 검증해 GET 에러 방지
- **round-trip 보장**: MA가 보낸 구조를 그대로 저장하고 조회 시 동일하게 반환

### 개인화 프로파일
- **자동 조회**: 세션 생성 시 user_id 기반으로 프로파일 Repository에서 자동 조회
- **스냅샷 저장**: Redis에 customer_profile 스냅샷 저장
- **조회 시 반환**: GET /sessions/{key} 응답에 customer_profile 필드 포함

### SOL API 연동 로그
- **턴 메타데이터 저장**: `POST /contexts/turn-results` 로 SOL API 호출 결과 저장
- **세션 전체 조회**: `GET /contexts/sessions/{key}/full` 로 세션 + 턴 목록 한 번에 확인

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
│    └─ ProfileService  : (향후) 고객 프로파일 조회/연결        │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer                                            │
│    ├─ RedisSessionRepository   : Redis 기반 세션/매핑 저장소 (동기) │
│    ├─ RedisContextRepository   : Redis 기반 컨텍스트/턴 저장소 (동기) │
│    ├─ MariaDBSessionRepository : MariaDB 기반 세션 저장소 (비동기) │
│    ├─ MariaDBContextRepository : MariaDB 기반 컨텍스트/턴 저장소 (비동기) │
│    └─ Mock*Repository          : 테스트/개발용 Mock 구현체    │
└─────────────────────────────────────────────────────────────┘
```

## 📁 디렉토리 구조

```
app/
   api/
      v1/
         sessions.py      # Unified Sessions API (생성/조회/업데이트/종료/Ping)
         contexts.py      # SOL API 결과 저장 + 세션 전체 정보 조회
         router.py        # v1 라우터 집합
   services/            # 비즈니스 로직
      session_service.py   # 세션 관리 핵심 로직 (멀티턴 컨텍스트 포함)
      profile_service.py   # 프로파일 조회 (향후 확장용)
   repositories/        # Repository 구현체 (Duck Typing 방식)
      redis_session_repository.py     # Redis 기반 세션 저장소
      redis_context_repository.py     # Redis 기반 컨텍스트/턴 저장소
      mariadb_session_repository.py    # MariaDB 기반 세션 저장소
      mariadb_context_repository.py    # MariaDB 기반 컨텍스트/턴 저장소
      hybrid_context_repository.py     # Hybrid 저장소 (미사용)
      mock/                            # 테스트/개발용 Mock Repository
   schemas/             # Pydantic 스키마
      common.py         # 세션 요청/응답 스키마
      contexts.py       # 컨텍스트/턴 스키마
   models/              # SQLAlchemy 모델 (MariaDB용)
   core/                # 예외, 인증, 정책, 유틸리티
      exceptions.py     # 커스텀 예외
      utils.py          # 공통 유틸리티 함수 (JSON 파싱, datetime 변환)
   db/                  # DB/Redis 연결
   config.py            # 환경 설정
   main.py              # FastAPI 엔트리포인트
tests/
   test_sessions_api.py    # Sessions API 통합 테스트
   test_context_api.py     # Contexts API 테스트
   test_integration.py     # E2E 통합 테스트
docs/
   Session_Manager_API_Sprint3.md  # Sprint 3 API 명세
   mulititurn.md                    # 멀티턴 컨텍스트 명세
```

## 🚀 시작하기

### 1. 환경 설정

```bash
# Python 3.11+ 필요
# uv 설치 (https://github.com/astral-sh/uv)

# 의존성 설치
uv sync --all-extras

# 환경변수 설정 (app/config.env 참고)
# - REDIS_URL: Redis 연결 URL (필수)
# - USE_MOCK_REDIS: Redis 대신 Mock Repository 사용 (테스트용, 기본 false)
```

### 2. 서버 실행

```bash
# 로컬 개발 (포트 5000)
uv run uvicorn app.main:app --reload --port 5000

# 또는
uv run python -m app.main
```

### 3. API 문서 확인

- Swagger UI: `http://localhost:5000/api/v1/docs`
- ReDoc: `http://localhost:5000/api/v1/redoc`

### 4. 테스트 실행

```bash
# 전체 테스트
uv run pytest -v

# 특정 테스트만 실행
uv run pytest tests/test_sessions_api.py -v
uv run pytest tests/test_context_api.py -v

# 테스트 커버리지
uv run pytest --cov=app tests/
```

### 5. 코드 품질 검사

```bash
# Linting
uv run ruff check .

# 자동 수정
uv run ruff check --fix .
```


## 🔑 인증/저장소 정책

### 인증

- 설계상 호출자별 API Key 헤더 사용 (`X-API-Key: {CALLER_API_KEY}`)
- 환경변수: `AGW_API_KEY`, `MA_API_KEY`, `PORTAL_API_KEY` 등
- 현재 개발/테스트 환경: `ENABLE_API_KEY_AUTH=false` (인증 비활성화)
- 운영 전환 시: `ENABLE_API_KEY_AUTH=true` 로 활성화

### 저장소

**Redis** (동기 캐시 저장소)
- 세션/컨텍스트/턴 메타데이터 즉시 저장 (동기)
- 기본 TTL 설정 (환경변수로 조정 가능):
  - `SESSION_CACHE_TTL=600` (세션 스냅샷)
  - `SESSION_MAP_TTL=600` (Agent 세션 매핑)
- Redis 키 구조:
  - `session:{global_session_key}` - 세션 해시
  - `session_map:{global_session_key}:{agent_id}` - Agent 세션 매핑
  - `context:{context_id}` - 컨텍스트 메타데이터
  - `context_turns:{context_id}` - 턴 목록 (리스트)

**MariaDB** (비동기 영구 저장소)
- 세션/컨텍스트/턴 메타데이터 영구 저장 (비동기)
- BackgroundTasks를 통해 API 응답 후 저장
- 저장 내용:
  - `sessions` 테이블: 세션 메타데이터
  - `agent_sessions` 테이블: Agent 세션 매핑
  - `contexts` 테이블: 컨텍스트 메타데이터
  - `conversation_turns` 테이블: 턴 메타데이터

### 환경변수 설정

주요 환경변수는 `app/config.env` (로컬 개발용) 또는 환경변수로 설정:

```bash
# Redis 연결 (필수)
REDIS_URL=rediss://default:password@host:port/0

# MariaDB 연결 (필수, Sprint 4+)
MARIADB_HOST=my-mariadb.mariadb.svc.cluster.local
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=ChangeMe!
MARIADB_DATABASE=session_manager

# Mock 모드 (테스트/로컬용, 기본 false)
USE_MOCK_REDIS=false

# MariaDB 사용 여부 (기본 true)
USE_MARIADB=true

# MariaDB 연결 풀 설정
MARIADB_POOL_SIZE=10
MARIADB_MAX_OVERFLOW=20
MARIADB_POOL_RECYCLE=3600
MARIADB_ECHO=false

# API Key 인증 (기본 false)
ENABLE_API_KEY_AUTH=false

# TTL 설정 (초 단위, 기본 600)
SESSION_CACHE_TTL=600
SESSION_MAP_TTL=600
```

## 📊 주요 API 사용 예시

### 세션 생성

```bash
curl -X POST "http://localhost:5000/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user_001",
    "channel": {
      "eventType": "ICON_ENTRY",
      "eventChannel": "mobile"
    }
  }'

# 응답: {"global_session_key": "gsess_20260113..."}
```

### 세션 조회

```bash
curl -X GET "http://localhost:5000/api/v1/sessions/gsess_20260113..."

# 응답: 세션 메타데이터 + customer_profile + conversation_history 등
```

### 세션 상태 업데이트 (멀티턴 컨텍스트 포함)

```bash
curl -X PATCH "http://localhost:5000/api/v1/sessions/gsess_20260113.../state" \
  -H "Content-Type: application/json" \
  -d '{
    "global_session_key": "gsess_20260113...",
    "turn_id": "turn_001",
    "session_state": "talk",
    "state_patch": {
      "subagent_status": "continue",
      "reference_information": {
        "conversation_history": [
          {"role": "user", "content": "계좌 조회"},
          {"role": "assistant", "content": "계좌번호를 알려주세요"}
        ],
        "current_intent": "계좌조회",
        "turn_count": 1
      }
    }
  }'
```

### 세션 전체 정보 조회 (세션 + 턴 목록)

```bash
curl -X GET "http://localhost:5000/api/v1/contexts/sessions/gsess_20260113.../full"

# 응답: {session: {...}, turns: [...], total_turns: 3}
```

### SOL API 결과 저장

```bash
curl -X POST "http://localhost:5000/api/v1/contexts/turn-results" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "gsess_20260113...",
    "turnId": "turn_001",
    "agent": "balance_agent",
    "result": "SUCCESS",
    "transactionResult": [
      {"trxCd": "BAL001", "responseData": {"balance": 500000}}
    ]
  }'
```

## 🎯 Sprint 4 주요 변경사항

### MariaDB 영구 저장소 통합
- Redis (동기) + MariaDB (비동기) 하이브리드 저장소
- 세션 생성/업데이트/종료 시 자동으로 MariaDB에 비동기 저장
- Agent 세션 매핑도 MariaDB에 영구 저장

### 필드명 통일
- `session_id` 제거: Redis에서 중복 필드 제거
- `local_session_key` → `agent_session_key`: 모든 코드에서 통일
- `current_subagent_id` → `action_owner`: MariaDB 필드명 통일
- `last_updated_at` → `updated_at`: MariaDB 필드명 통일

### Context DB 구축
- MariaDB에 Context/Turn 메타데이터 저장
- SOL API 연동 결과도 MariaDB에 비동기 저장
- 세션 전체 정보 조회 API에서 MariaDB 데이터 포함

### 코드 품질 개선 (리팩토링)
- **공통 유틸리티 함수 추가** (`app/core/utils.py`):
  - `safe_json_parse()`: JSON 파싱 통일 및 안전한 에러 처리
  - `safe_json_dumps()`: JSON 직렬화 통일
  - `datetime_to_iso()`, `iso_to_datetime()`: Datetime 변환 통일
  - `safe_datetime_parse()`: Datetime 파싱 통일
- **코드 중복 제거**: JSON 파싱 로직을 유틸리티 함수로 통일
- **타입 힌팅 개선**: 함수 반환 타입 명시 및 타입 안정성 향상
- **에러 처리 일관성 향상**: 안전한 파싱 및 변환으로 런타임 에러 방지
- **필드명 통일**: Context Repository에서 `last_updated_at` → `updated_at` 통일
- **인터페이스 제거**: `app/repositories/base.py` 삭제, Duck Typing 방식으로 전환
  - ABC 패턴 인터페이스 제거로 코드 단순화
  - 실제 구현과 맞지 않는 인터페이스 제거
  - Duck Typing을 통한 런타임 유연성 확보
- **사용되지 않는 스키마 제거**: `app/schemas/contexts.py` 정리
  - `ContextCreate`, `ContextUpdate`, `ContextResponse` 제거
  - `TurnCreate`, `TurnCreateWithAPI` 제거
  - 실제 사용 중인 스키마만 유지

## 🎯 향후 확장 (Sprint 5+)

- 개인화 프로파일 연동 (VDB/CRM 연동)
- 인증 정책 반영 (API Key 인증 활성화)
- Session API로 통일 (Contexts API를 Sessions API 하위로 통합)

## 🛠️ 기술 스택

- **Web Framework**: FastAPI 0.109.0
- **Package Manager**: uv
- **ORM**: SQLAlchemy 2.0.25 (향후 RDB 연동용)
- **Cache**: Redis 5.0.1
- **Testing**: pytest 9.0.2
- **Linting**: Ruff 0.14.10
- **Python**: 3.11+

## 📝 코딩 컨벤션

- 파일명: `snake_case`
- 클래스명: `PascalCase`
- 함수명: `snake_case`
- 상수명: `UPPER_CASE`
- 라인 길이: 140자 이하
- PEP8 준수 (Ruff로 자동 검사)

## 📚 참고 문서

- `docs/Session_Manager_API_Sprint4.md` – Sprint 4 API 명세서 (최신)
- `docs/Session_Manager_API_Sprint3.md` – Sprint 3 API 명세서
- `docs/SPRINT3_DESIGN_FINAL.md` – 설계 문서
- `docs/session_manager_onprem_migration.md` – 배포 가이드
- `scripts/init_db.sql` – MariaDB 스키마 초기화 스크립트


