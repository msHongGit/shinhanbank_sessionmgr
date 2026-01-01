# Session Manager v3.0

은행 AI Agent 시스템의 세션 관리 API 서비스

## 📚 문서

| 문서 | 설명 |
|------|------|
| [PRD.md](docs/PRD.md) | 제품 요구사항 문서 |
| [TDD.md](docs/TDD.md) | 기술 설계 문서 |
| [TODO.md](docs/TODO.md) | 남은 작업 목록 |

---

## 🚨 현재 상태

> **MVP (Redis 기반 80~90% 완성)**

| 구분 | 상태 | 비고 |
|------|------|------|
| API 엔드포인트 | ✅ 완료 | 12개 API |
| Redis 캐시 | ✅ 완료 | 세션, 매핑, Context |
| PostgreSQL 영속화 | ⚠️ TODO | 스키마만 있음 |
| SQLAlchemy 모델 | ⚠️ TODO | 미구현 |
| 프로파일 조회 | ⚠️ TODO | Mock 반환 |
| 테스트 | ✅ 완료 | 30개 통과 |

자세한 TODO는 [docs/TODO.md](docs/TODO.md) 참조

---

## 🏗️ 연동 구조

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   [Client] ─── Global Session Key 발급 ───┐                     │
│                                           │                      │
│                                           ▼                      │
│   [Agent GW] ─────────────────────────> [SM]                    │
│       • 초기 세션 생성                      │                    │
│         (Client가 발급한 Global Key 전달)   │                    │
│                                           │                      │
│   [MA] ───────────────────────────────> [SM]                    │
│       • 세션 조회 (ResolveSession)         │                    │
│       • Local 세션 등록/조회               │                    │
│       • 세션 상태 업데이트                  │                    │
│       • 대화 이력 조회/저장                 │                    │
│       • 고객 프로파일 조회                  │                    │
│       • 세션 종료                          │                    │
│                                           │                      │
│   [Portal] ────────────────────────────> [SM]                   │
│       • 세션 목록 조회 (읽기 전용)          │                    │
│       • Context 삭제 (context_id 기준)     │                    │
│                                           │                      │
│   [VDB] ───────────────────────────────> [SM]                   │
│       • 프로파일 배치 업로드               │                    │
│                                           │                      │
│                               ┌───────────┴───────────┐          │
│                               │       SM              │          │
│                               │   ┌───────┐ ┌──────┐ │          │
│                               │   │ Redis │ │  DB  │ │          │
│                               │   └───────┘ └──────┘ │          │
│                               └───────────────────────┘          │
│                                                                  │
│   ❌ SM ↔ SA: 직접 연동 없음 (MA가 담당)                         │
│   ❌ SM ↔ Client: 직접 연동 없음                                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📡 API Endpoints

### AGW API (`/api/v1/agw`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sessions` | 초기 세션 생성 (Global Key 전달) |

### MA API (`/api/v1/ma`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions/resolve` | 세션 조회 |
| POST | `/sessions/local` | Local 세션 등록 |
| GET | `/sessions/local` | Local 세션 조회 |
| PATCH | `/sessions/state` | 세션 상태 업데이트 |
| POST | `/sessions/close` | 세션 종료 |
| GET | `/context/history` | 대화 이력 조회 |
| POST | `/context/turn` | 대화 턴 저장 |
| GET | `/profiles/{user_id}` | 프로파일 조회 |

### Portal API (`/api/v1/portal`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/sessions` | 세션 목록 조회 (읽기 전용) |
| GET | `/context/{context_id}` | Context 정보 조회 |
| DELETE | `/context/{context_id}` | Context 삭제 (context_id 기준) |

### Batch API (`/api/v1/batch`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/profiles` | 프로파일 배치 업로드 |

---

## 🔐 API Key 격리

각 호출자는 자신의 API만 접근 가능합니다.

| 호출자 | API Key 환경변수 | 접근 가능 |
|--------|-----------------|----------|
| Agent GW | `AGW_API_KEY` | `/agw/*` |
| MA | `MA_API_KEY` | `/ma/*` |
| Portal | `PORTAL_API_KEY` | `/portal/*` |
| VDB | `VDB_API_KEY` | `/batch/*` |

---

## 🚀 Quick Start

### 로컬 개발

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
cp .env.example .env

# 3. 테스트 실행
pytest tests/ -v

# 4. 서버 실행 (Redis 필요)
uvicorn app.main:app --reload
```

### Docker

```bash
# 전체 스택 실행
docker-compose up -d

# API 문서 확인
open http://localhost:8000/api/v1/docs

# 로그 확인
docker-compose logs -f api
```

---

## 📁 Project Structure

```
session-manager/
├── app/
│   ├── main.py                 # FastAPI 앱
│   ├── config.py               # 환경 설정
│   ├── api/
│   │   ├── deps.py             # 의존성 (API Key 검증)
│   │   └── v1/
│   │       ├── agw/            # AGW API
│   │       │   └── sessions.py
│   │       ├── ma/             # MA API
│   │       │   ├── sessions.py
│   │       │   ├── context.py
│   │       │   └── profiles.py
│   │       ├── portal/         # Portal API
│   │       │   └── admin.py
│   │       └── batch/          # VDB API
│   │           └── profiles.py
│   ├── schemas/                # 호출자별 스키마
│   │   ├── common.py
│   │   ├── agw.py
│   │   ├── ma.py
│   │   ├── portal.py
│   │   └── batch.py
│   ├── services/               # 비즈니스 로직
│   │   ├── session_service.py
│   │   ├── context_service.py
│   │   └── profile_service.py
│   ├── db/                     # 데이터 레이어
│   │   ├── redis.py
│   │   └── postgres.py
│   └── core/
│       └── exceptions.py
├── tests/                      # 30개 테스트
├── docs/                       # 문서
│   ├── PRD.md
│   ├── TDD.md
│   └── TODO.md
├── scripts/
│   └── init_db.sql
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🔑 세션 구조

| 세션 키 | 발급 주체 | 용도 |
|--------|----------|------|
| **Global Session** | Client | 전체 대화 식별 |
| **Local Session** | 업무 Agent | 멀티턴 대화 관리 |
| **Context ID** | SM | 대화 이력 식별 |
| **Conversation ID** | SM | 대화 인스턴스 식별 |

---

## 🧪 테스트

```bash
# 전체 테스트
pytest tests/ -v

# 커버리지
pytest tests/ --cov=app --cov-report=html

# 특정 파일
pytest tests/test_ma_api.py -v
```

---

## 📝 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 3.0 | 2025-03-16 | 호출자별 API 분리, MA-SA 인터페이스 제거 |
| 2.0 | - | Global/Local 세션 매핑 추가 |
| 1.0 | - | 초기 버전 |
