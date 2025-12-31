# Session Manager

은행 AI Agent 시스템의 세션 생명주기, Task Queue, 고객 프로파일을 관리하는 API 서비스입니다.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Clients                                   │
│  ┌─────────┐  ┌─────────────┐  ┌────────┐  ┌─────────────────┐  │
│  │Agent GW │  │Master Agent │  │ Portal │  │  Vertical DB    │  │
│  └────┬────┘  └──────┬──────┘  └───┬────┘  └────────┬────────┘  │
└───────┼──────────────┼─────────────┼────────────────┼───────────┘
        │              │             │                │
        ▼              ▼             ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Session Manager API                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  FastAPI + Pydantic                                      │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │    │
│  │  │ Session  │ │  Task    │ │ Profile  │ │  Portal  │    │    │
│  │  │   API    │ │   API    │ │   API    │ │   API    │    │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          │                                       │
│              ┌───────────┴───────────┐                          │
│              ▼                       ▼                          │
│  ┌─────────────────────┐  ┌─────────────────────┐               │
│  │       Redis         │  │    PostgreSQL       │               │
│  │  (Cache + Queue)    │  │   (Persistence)     │               │
│  └─────────────────────┘  └─────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
session-manager/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── config.py               # 환경 설정
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # 의존성 주입
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # API 라우터 통합
│   │   │   ├── sessions.py     # 세션 API
│   │   │   ├── tasks.py        # Task Queue API
│   │   │   ├── profiles.py     # 고객 프로파일 API
│   │   │   └── portal.py       # Portal 관리 API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # 인증/인가
│   │   └── exceptions.py       # 커스텀 예외
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgres.py         # PostgreSQL 연결
│   │   ├── redis.py            # Redis 연결
│   │   └── repositories/       # 데이터 접근 계층
│   │       ├── __init__.py
│   │       ├── session_repo.py
│   │       ├── task_repo.py
│   │       └── profile_repo.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── session.py          # SQLAlchemy 모델
│   │   ├── task.py
│   │   └── profile.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── session.py          # Pydantic 스키마
│   │   ├── task.py
│   │   ├── profile.py
│   │   └── common.py
│   └── services/
│       ├── __init__.py
│       ├── session_service.py  # 비즈니스 로직
│       ├── task_service.py
│       └── profile_service.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest fixtures
│   ├── test_sessions.py
│   ├── test_tasks.py
│   └── test_profiles.py
├── docs/
│   ├── PRD.md
│   └── TDD.md
├── scripts/
│   ├── init_db.py              # DB 초기화 스크립트
│   └── seed_data.py            # 테스트 데이터
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Redis
- PostgreSQL

### 1. Clone & Setup

```bash
# Clone repository
git clone <repository-url>
cd session-manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
```

### 3. Run with Docker Compose (Recommended)

```bash
# Start all services (API + Redis + PostgreSQL)
docker-compose up -d

# Check logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### 4. Run Locally (Development)

```bash
# Start Redis and PostgreSQL separately
docker-compose up -d redis postgres

# Run FastAPI with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## 📡 API Endpoints

### Session Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | 초기 세션 생성 |
| GET | `/api/v1/sessions/resolve` | 세션 조회/생성 |
| PATCH | `/api/v1/sessions/{session_id}` | 세션 상태 업데이트 |
| POST | `/api/v1/sessions/{session_id}/close` | 세션 종료 |

### Task Queue

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/tasks` | Task 적재 |
| GET | `/api/v1/tasks/{task_id}/status` | Task 상태 조회 |
| GET | `/api/v1/tasks/{task_id}/result` | Task 결과 조회 |

### Customer Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/profiles/{user_id}` | 프로파일 조회 |
| POST | `/api/v1/profiles/batch` | 프로파일 배치 업로드 |

### Portal Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/portal/conversations` | 대화 목록 조회 |
| GET | `/api/v1/portal/conversations/{id}` | 대화 상세 조회 |
| DELETE | `/api/v1/portal/conversations/{id}` | 대화 이력 삭제 |

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_sessions.py -v

# Run with markers
pytest -m "unit"
pytest -m "integration"
```

## 🐳 Docker Commands

```bash
# Build image
docker build -t session-manager:latest .

# Run container
docker run -d -p 8000:8000 --env-file .env session-manager:latest

# View logs
docker logs -f <container_id>

# Enter container
docker exec -it <container_id> /bin/bash
```

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics (Prometheus format)

```bash
curl http://localhost:8000/metrics
```

## 🔧 Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `APP_ENV` | 환경 (dev/staging/prod) | `dev` |
| `DEBUG` | 디버그 모드 | `true` |
| `API_PREFIX` | API prefix | `/api/v1` |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379` |
| `DATABASE_URL` | PostgreSQL 연결 URL | `postgresql+asyncpg://...` |
| `SECRET_KEY` | JWT 시크릿 키 | - |
| `SESSION_TTL` | 세션 TTL (초) | `3600` |

## 📝 Development Guidelines

### Code Style

```bash
# Format code
black app tests
isort app tests

# Lint
ruff check app tests
mypy app
```

### Commit Convention

```
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 변경
style: 코드 포맷팅
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드/설정 변경
```

### Branch Strategy

- `main`: 프로덕션 배포
- `develop`: 개발 통합
- `feature/*`: 기능 개발
- `fix/*`: 버그 수정

## 📚 Documentation

- [PRD (Product Requirements Document)](docs/PRD.md)
- [TDD (Technical Design Document)](docs/TDD.md)
- [API Specification](http://localhost:8000/docs)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary and confidential.

## 👥 Team

- Backend Team - API Development
- Infrastructure Team - Deployment & Monitoring
