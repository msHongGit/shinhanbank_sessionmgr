# Session Manager v5.0 - Sprint 5

은행 AI Agent 시스템의 세션/컨텍스트 관리 서비스

> **Sprint 1**: 설계 및 아키텍처 정의  
> **Sprint 2**: Mock Repository 기반 API 검증  
> **Sprint 3**: Unified Sessions + SOL 연동 결과 메타데이터(Contexts/Turns), Redis 기반 세션/컨텍스트 관리  
> **Sprint 4**: MariaDB 영구 저장소 통합, 필드명 통일, Context DB 구축  
> **Sprint 5**: Redis 전용 전환 (MariaDB 제거, Mock 제거, Profile만 Mock 유지)

## 🎯 주요 기능

### 세션 관리
- **세션 생성/조회/업데이트/종료**: Unified Sessions API (`/api/v1/sessions`)
- **세션 상태 관리**: start / talk / end
- **SubAgent 상태**: undefined / continue / end
- **JWT 토큰 인증**: Access Token (5분), Refresh Token (1시간), Refresh Token Rotation
- **세션 생존 확인**: Ping API로 세션 생존 확인 (TTL 연장은 Refresh Token으로)

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
- **턴 메타데이터 저장**: `POST /api/v1/sessions/{global_session_key}/api-results` 로 SOL API 호출 결과 저장
- **세션 전체 조회**: `GET /api/v1/sessions/{global_session_key}/full` 로 세션 + 턴 목록 한 번에 확인

## 🏗️ 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        Session Manager                      │
├─────────────────────────────────────────────────────────────┤
│  API Layer (FastAPI)                                        │
│    └─ Unified Sessions API : 세션 생성/조회/상태변경/종료/SOL API 결과 저장/전체 조회 │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                               │
│    ├─ SessionService  : 세션/Agent 세션 매핑 비즈니스 로직   │
│    └─ ProfileService  : (향후) 고객 프로파일 조회/연결        │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer                                            │
│    ├─ RedisSessionRepository   : Redis 기반 세션/매핑/턴 저장소 │
│    └─ MockProfileRepository    : 프로파일 Mock 구현체 (개발/테스트용) │
└─────────────────────────────────────────────────────────────┘
```

## 📁 디렉토리 구조

```
app/
   api/
      v1/
         sessions.py      # Unified Sessions API (생성/조회/업데이트/종료/Ping/SOL API 결과 저장/전체 조회)
         router.py        # v1 라우터 집합
   services/            # 비즈니스 로직
      session_service.py   # 세션 관리 핵심 로직 (멀티턴 컨텍스트 포함)
      profile_service.py   # 프로파일 조회 (향후 확장용)
   repositories/        # Repository 구현체 (Duck Typing 방식)
      redis_session_repository.py     # Redis 기반 세션/턴 저장소
      mock/                            # Mock Repository
         mock_profile_repository.py   # 프로파일 Mock 구현체 (개발/테스트용)
   schemas/             # Pydantic 스키마
      common.py         # 세션/턴 요청/응답 스키마 (통합)
   core/                # 예외, 인증, 정책, 유틸리티
      exceptions.py     # 커스텀 예외
      jwt.py            # JWT 토큰 생성/검증 유틸리티
      jwt_auth.py       # JWT 인증 의존성
      utils.py          # 공통 유틸리티 함수 (JSON 파싱, datetime 변환)
   db/                  # DB/Redis 연결
   config.py            # 환경 설정
   main.py              # FastAPI 엔트리포인트
tests/
   test_sessions_api.py    # Sessions API 통합 테스트 (JWT 인증 포함)
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

### 인증 (JWT 토큰 기반)

Session Manager는 JWT 토큰 기반 인증을 사용합니다.

- **토큰 발급**: 세션 생성 시 `access_token`과 `refresh_token` 자동 발급
- **Access Token**: 만료 시간 5분, 세션 정보 조회 및 Ping에 사용
- **Refresh Token**: 만료 시간 1시간, 토큰 갱신에 사용
- **Refresh Token Rotation**: 토큰 갱신 시 새 토큰 발급, 기존 토큰 무효화
- **사용 방법**: 
  - 헤더: `Authorization: Bearer {access_token}` 또는 `Authorization: Bearer {refresh_token}`
  - 쿠키: `access_token={access_token}` 또는 `refresh_token={refresh_token}`

### 저장소

**Redis** (세션/컨텍스트 저장소)
- 세션/턴 메타데이터 저장
- 기본 TTL 설정 (환경변수로 조정 가능):
  - `SESSION_CACHE_TTL=300` (세션 스냅샷, 기본값 300초)
- Redis 키 구조:
  - `session:{global_session_key}` - 세션 해시 (Agent 매핑 포함)
  - `turns:{global_session_key}` - 턴 목록 (리스트)
  - `jti:{jti}` - JWT ID → global_session_key 매핑

### 환경변수 설정

주요 환경변수는 `app/config.env` (로컬 개발용) 또는 환경변수로 설정:

```bash
# Redis 연결 (필수)
REDIS_URL=rediss://default:password@host:port/0

# TTL 설정 (초 단위, 기본 300)
SESSION_CACHE_TTL=300

# JWT 설정 (필수)
JWT_SECRET_KEY=your-secret-key-here  # 암호학적으로 안전한 랜덤 문자열 (예: openssl rand -hex 32)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=5    # Access Token 만료 시간 (분)
JWT_REFRESH_TOKEN_EXPIRE_HOURS=1    # Refresh Token 만료 시간 (시간)
```

## 📊 주요 API 사용 예시

### 세션 생성

```bash
curl -X POST "http://localhost:5000/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "0616001905",
    "channel": {
      "eventType": "ICON_ENTRY",
      "eventChannel": "mobile"
    }
  }'

# 응답: {
#   "global_session_key": "gsess_20260113...",
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "jti": "550e8400-e29b-41d4-a716-446655440000"
# }
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
curl -X GET "http://localhost:5000/api/v1/sessions/gsess_20260113.../full"

# 응답: {session: {...}, turns: [...], total_turns: 3}
```

### SOL API 결과 저장

```bash
curl -X POST "http://localhost:5000/api/v1/sessions/gsess_20260113.../api-results" \
  -H "Content-Type: application/json" \
  -d '{
    "global_session_key": "gsess_20260113...",
    "turn_id": "turn_001",
    "agent": "balance_agent",
    "result": "SUCCESS",
    "transactionResult": [
      {"trxCd": "BAL001", "responseData": {"balance": 1500000}}
    ]
  }'
```

### 토큰 검증 및 세션 정보 조회

```bash
curl -X GET "http://localhost:5000/api/v1/sessions/verify" \
  -H "Authorization: Bearer {access_token}"

# 응답: {
#   "global_session_key": "gsess_20260113...",
#   "user_id": "0616001905",
#   "session_state": "talk",
#   "is_alive": true,
#   "expires_at": "2026-01-14T10:45:00Z"
# }
```

### 토큰 갱신

```bash
curl -X POST "http://localhost:5000/api/v1/sessions/refresh" \
  -H "Authorization: Bearer {refresh_token}"

# 응답: {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "global_session_key": "gsess_20260113...",
#   "jti": "de8a2b69-48b5-4f72-bbae-09903954f5fe"
# }
```

### 세션 생존 확인 (Ping)

```bash
curl -X GET "http://localhost:5000/api/v1/sessions/ping" \
  -H "Authorization: Bearer {access_token}"

# 응답: {
#   "is_alive": true,
#   "expires_at": "2026-01-14T10:45:00Z"
# }
```

### 세션 종료 (토큰 기반)

```bash
curl -X DELETE "http://localhost:5000/api/v1/sessions" \
  -H "Authorization: Bearer {access_token}" \
  -G --data-urlencode "close_reason=user_exit"

# 응답: {
#   "status": "success",
#   "closed_at": "2026-01-14T10:35:00Z",
#   "archived_conversation_id": "arch_gsess_20260113..."
# }
```

## 🎯 Sprint 5 주요 변경사항

### Redis 전용 전환
- MariaDB 제거: Redis만 사용하여 단순화
- Mock Repository 제거: Session/Context Mock 제거 (Profile Mock만 유지)
- BackgroundTasks 제거: 비동기 저장 로직 제거

### 저장소 단순화
- Redis만 사용: 세션/컨텍스트/턴 메타데이터 모두 Redis에 저장
- TTL 기반 관리: 세션 생존 시간 자동 관리 (기본 300초)
- Profile Mock 유지: 개발/테스트용 프로파일 Mock Repository 유지

### JWT 토큰 기반 인증 추가
- API Key 인증 제거: `app/core/auth.py` 삭제, 모든 API Key 관련 설정 제거
- JWT 토큰 발급: 세션 생성 시 `access_token`, `refresh_token`, `jti` 자동 발급
- 토큰 검증 API: `GET /api/v1/sessions/verify` 추가
- 토큰 갱신 API: `POST /api/v1/sessions/refresh` 추가 (Refresh Token Rotation)
- Ping API 변경: `/{global_session_key}/ping` → `/ping` (토큰 기반, TTL 연장 없음)
- 세션 종료 API 변경: `/{global_session_key}` → `/` (토큰 기반 엔드포인트 추가)

### 코드 정리
- MariaDB 관련 코드 제거: `app/db/mariadb.py`, `app/models/mariadb_models.py`, `scripts/init_db.sql` 등
- Mock 관련 코드 제거: `MockSessionRepository`, `MockContextRepository` 제거
- API 통합: `app/api/v1/contexts.py` 삭제, `app/api/v1/sessions.py`로 통합
- Repository 통합: `app/repositories/redis_context_repository.py` 삭제, `app/repositories/redis_session_repository.py`로 통합
- 스키마 통합: `app/schemas/contexts.py` 삭제, `app/schemas/common.py`로 통합
- JWT 인증 추가: `app/core/jwt.py`, `app/core/jwt_auth.py` 추가
- 불필요한 import 제거: 사용하지 않는 import 정리

## 🎯 향후 확장 (Sprint 6+)

- 개인화 프로파일 연동 (VDB/CRM 연동)
  - 배치 프로파일: MariaDB에서 조회 (설정 가능한 테이블/컬럼 구조)
  - 실시간 프로파일: Redis에 저장 및 통합
- 여러 Agent 매핑 한 번에 처리 (`state_patch.agent_mappings` 배열 지원)

## 🛠️ 기술 스택

- **Web Framework**: FastAPI 0.109.0
- **Package Manager**: uv
- **ORM**: SQLAlchemy 2.0.25 (향후 RDB 연동용)
- **Cache**: Redis 5.0.1
- **JWT**: PyJWT[cryptography]>=2.8.0
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

- `docs/Session_Manager_API_Sprint5.md` – Sprint 5 API 명세서 (최신)
- `docs/Session_Manager_API_Sprint4.md` – Sprint 4 API 명세서
- `docs/Session_Manager_API_Sprint3.md` – Sprint 3 API 명세서
- `docs/redis_data.md` – Redis 데이터 구조 정의서
- `docs/redis.md` – Redis 운영 가이드


