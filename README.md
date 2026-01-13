# Session Manager v4.0 - Sprint 3+

은행 AI Agent 시스템의 세션/컨텍스트 관리 서비스

> **Sprint 1**: 설계 및 아키텍처 정의  
> **Sprint 2**: Mock Repository 기반 API 검증  
> **Sprint 3**: Unified Sessions + SOL 연동 결과 메타데이터(Contexts/Turns), Redis 기반 세션/컨텍스트 관리  
> **Sprint 3+**: 멀티턴 컨텍스트 round-trip 보장, 세션 전체 정보 조회 API 추가

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
│    ├─ ContextService  : (향후) 컨텍스트/턴 메타데이터 관리    │
│    └─ ProfileService  : (향후) 고객 프로파일 조회/연결        │
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
         sessions.py      # Unified Sessions API (생성/조회/업데이트/종료/Ping)
         contexts.py      # SOL API 결과 저장 + 세션 전체 정보 조회
         router.py        # v1 라우터 집합
   services/            # 비즈니스 로직
      session_service.py   # 세션 관리 핵심 로직 (멀티턴 컨텍스트 포함)
      context_service.py   # 컨텍스트/턴 관리 (향후 확장용)
      profile_service.py   # 프로파일 조회 (향후 확장용)
   repositories/        # Repository 인터페이스 및 구현체
      redis_session_repository.py     # Redis 기반 세션 저장소
      redis_context_repository.py     # Redis 기반 컨텍스트/턴 저장소
      mock/                            # 테스트/개발용 Mock Repository
   schemas/             # Pydantic 스키마
      common.py         # 세션 요청/응답 스키마
      contexts.py       # 컨텍스트/턴 스키마
   models/              # SQLAlchemy 모델 (향후 RDB용, 현재 미사용)
   core/                # 예외, 인증, 정책
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

**Redis** (현재 메인 저장소)
- 세션/컨텍스트/턴 메타데이터 캐시
- 기본 TTL 설정 (환경변수로 조정 가능):
  - `SESSION_CACHE_TTL=600` (세션 스냅샷)
  - `SESSION_MAP_TTL=600` (Agent 세션 매핑)
- Redis 키 구조:
  - `session:{global_session_key}` - 세션 해시
  - `session_map:{global_session_key}:{agent_id}` - Agent 세션 매핑
  - `context:{context_id}` - 컨텍스트 메타데이터
  - `context_turns:{context_id}` - 턴 목록 (리스트)

**MariaDB** (향후 영구 저장용)
- 현재 미사용, Sprint 4+ 연동 예정

### 환경변수 설정

주요 환경변수는 `app/config.env` (로컬 개발용) 또는 환경변수로 설정:

```bash
# Redis 연결 (필수)
REDIS_URL=rediss://default:password@host:port/0

# Mock 모드 (테스트/로컬용, 기본 false)
USE_MOCK_REDIS=false

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

## 🎯 향후 확장 (Sprint 4+)

- MariaDB 기반 영구 세션/컨텍스트 저장소 구현
- Task Queue 관리 및 비동기 작업 처리
- 세션 만료 처리 및 배치 정리 작업
- 실시간 이벤트 스트리밍 (SSE/WebSocket)
- 관리자용 대시보드 및 모니터링 API
- CI/CD 파이프라인 고도화

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

- `docs/Session_Manager_API_Sprint3.md` – API 명세서
- `docs/mulititurn.md` – 멀티턴 컨텍스트 명세
- `docs/SPRINT3_DESIGN_FINAL.md` – 설계 문서
- `docs/session_manager_onprem_migration.md` – 배포 가이드

## �📄 라이센스

Proprietary - Shinhan Bank
