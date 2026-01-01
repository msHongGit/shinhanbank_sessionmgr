# Session Manager - TODO

## 현재 상태: Sprint 1 완료 ✅

> **Sprint 1 완료**: Repository Pattern + Mock Repository 구현 완료 (2026-01-01)
> **다음 스프린트**: PostgreSQL/Redis 실제 연동

---

## 📅 Sprint 1: Mock 기반 구조 완성 ✅ (완료)

### ✅ 완료 항목
- [x] **SQLAlchemy 모델 정의** (2026-01-01)
  - `app/models/session.py` - Session 테이블
  - `app/models/session_status.py` - SessionStatus 테이블 (1:1 분리)
  - `app/models/context.py` - SystemContext 테이블
  - `app/models/profile.py` - CustomerProfile 테이블

- [x] **Repository Pattern 구현** (2026-01-01)
  - `app/repositories/base.py` - ABC 인터페이스 정의 (Sync)
  - `app/repositories/mock/` - Mock Repository 구현 (Singleton, Dict 저장소)
    - `mock_session_repository.py` - 세션 저장소
    - `mock_context_repository.py` - Context 저장소
    - `mock_profile_repository.py` - Profile 저장소 (Mock 데이터 포함)

- [x] **Service Layer** (2026-01-01)
  - `app/services/session_service.py` - Repository DI 적용 (Sync)
  - `app/services/context_service.py` - Repository DI 적용 (Sync)
  - `app/services/profile_service.py` - Repository DI 적용 (Sync)

- [x] **API Layer** (2026-01-01)
  - 호출자별 API 분리 (AGW, MA, Portal, VDB)
  - 호출자별 API Key 검증
  - 모든 핸들러 Sync 함수 (외부 연동이 Sync)

- [x] **테스트** (2026-01-01)
  - 12개 테스트 전체 통과
  - Mock Repository 기반 격리 테스트
  - `conftest.py` 리팩토링 (DB patching 제거)

- [x] **개발 환경**
  - uv 환경 설정 (`pyproject.toml`)
  - Docker/docker-compose 구성
  - Ruff 린팅 설정

- [x] **문서화**
  - `README_SPRINT1.md` - Sprint 1 완료 문서
  - `.github/copilot-instructions.md` - Coding Conventions
  - `docs/TDD.md` - TDD 전략

---

## 📅 Sprint 2: PostgreSQL 연동 (예정)

### 🔴 P0: 필수 구현 (원래 설계 반영)

#### 1. Alembic 마이그레이션 설정
**목표**: DB 스키마 버전 관리

```bash
# 1. Alembic 초기화
alembic init alembic

# 2. alembic/env.py 설정
from app.models import Base
target_metadata = Base.metadata

# 3. 초기 마이그레이션 생성
alembic revision --autogenerate -m "Initial session tables"

# 4. 마이그레이션 실행
alembic upgrade head
```

**필요 파일:**
```
alembic/
├── env.py (설정)
├── script.py.mako
└── versions/
    └── 001_initial_session_tables.py
```

#### 2. PostgreSQL Repository 구현
**목표**: 실제 DB 저장소 구현 (Sync 방식)

```python
# app/repositories/postgres/session_repository.py
from sqlalchemy.orm import Session as DBSession
from app.repositories.base import SessionRepositoryInterface
from app.models import Session

class PostgresSessionRepository(SessionRepositoryInterface):
    """PostgreSQL 기반 세션 저장소 (Sync)"""
    
    def __init__(self, db: DBSession):
        self.db = db
    
    def create(self, global_session_key: str, **kwargs) -> Dict[str, Any]:
        session = Session(
            global_session_key=global_session_key,
            **kwargs
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return self._to_dict(session)
    
    def get(self, global_session_key: str) -> Optional[Dict[str, Any]]:
        session = self.db.query(Session).filter(
            Session.global_session_key == global_session_key
        ).first()
        return self._to_dict(session) if session else None
    
    def update(self, global_session_key: str, **kwargs) -> bool:
        result = self.db.query(Session).filter(
            Session.global_session_key == global_session_key
        ).update(kwargs)
        self.db.commit()
        return result > 0
    
    def delete(self, global_session_key: str) -> bool:
        result = self.db.query(Session).filter(
            Session.global_session_key == global_session_key
        ).delete()
        self.db.commit()
        return result > 0
    
    def _to_dict(self, session: Session) -> Dict[str, Any]:
        """ORM 모델 → Dict 변환"""
        return {
            "session_id": session.session_id,
            "global_session_key": session.global_session_key,
            "user_id": session.user_id,
            "channel": session.channel,
            # ... 나머지 필드
        }
```

**필요 파일:**
```
app/repositories/postgres/
├── __init__.py
├── session_repository.py
├── context_repository.py
└── profile_repository.py
```

#### 3. Dependency Injection 전환
**목표**: Mock → PostgreSQL Repository 전환

```python
# app/api/deps.py (수정)
from app.config import settings

def get_session_service() -> SessionService:
    if settings.APP_ENV == "test" or settings.USE_MOCK:
        # Mock Repository (테스트 환경)
        return SessionService(
            session_repo=MockSessionRepository(),
            context_repo=MockContextRepository(),
        )
    else:
        # PostgreSQL Repository (운영 환경)
        db = next(get_db())
        return SessionService(
            session_repo=PostgresSessionRepository(db),
            context_repo=PostgresContextRepository(db),
        )
```

**config.py 추가:**
```python
class Settings(BaseSettings):
    # ...
    USE_MOCK: bool = False  # 환경변수로 제어
```

#### 4. Redis 캐시 레이어 추가
**목표**: 성능 향상 (캐시 우선, DB는 Fallback)

```python
# app/repositories/redis/session_cache.py
import redis
from app.config import settings

class SessionCache:
    """Redis 기반 세션 캐시 (Sync)"""
    
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """캐시에서 세션 조회"""
        data = self.redis.hgetall(f"session:{key}")
        return data if data else None
    
    def set(self, key: str, session: Dict[str, Any], ttl: int):
        """세션 캐시 저장"""
        pipe = self.redis.pipeline()
        pipe.hset(f"session:{key}", mapping=session)
        pipe.expire(f"session:{key}", ttl)
        pipe.execute()
    
    def delete(self, key: str):
        """세션 캐시 삭제"""
        self.redis.delete(f"session:{key}")
```

#### 5. Hybrid Repository 구현 (Redis + PostgreSQL)
**목표**: 캐시 Hit 시 빠른 응답, Miss 시 DB 조회

```python
# app/repositories/hybrid_session_repository.py
class HybridSessionRepository(SessionRepositoryInterface):
    """Redis + PostgreSQL Hybrid 저장소"""
    
    def __init__(self, db: DBSession, cache: SessionCache):
        self.pg_repo = PostgresSessionRepository(db)
        self.cache = cache
    
    def create(self, global_session_key: str, **kwargs) -> Dict[str, Any]:
        # 1. PostgreSQL에 저장 (영구)
        session = self.pg_repo.create(global_session_key, **kwargs)
        
        # 2. Redis에 캐시
        self.cache.set(
            global_session_key, 
            session, 
            ttl=settings.SESSION_CACHE_TTL
        )
        
        return session
    
    def get(self, global_session_key: str) -> Optional[Dict[str, Any]]:
        # 1. Redis 캐시 우선 조회
        session = self.cache.get(global_session_key)
        if session:
            return session
        
        # 2. Cache Miss → PostgreSQL 조회
        session = self.pg_repo.get(global_session_key)
        if session:
            # 캐시에 저장
            self.cache.set(
                global_session_key, 
                session, 
                ttl=settings.SESSION_CACHE_TTL
            )
        
        return session
    
    def update(self, global_session_key: str, **kwargs) -> bool:
        # 1. PostgreSQL 업데이트
        result = self.pg_repo.update(global_session_key, **kwargs)
        
        # 2. Redis 캐시 무효화
        self.cache.delete(global_session_key)
        
        return result
```

---

## 📅 Sprint 3: 고급 기능 구현 (추후)

### 🟡 P1: 중요 구현

#### 1. Local 세션 매핑 (Redis)
**목표**: Global ↔ Local 세션 키 매핑

```python
# app/repositories/redis/local_session_mapping.py
class LocalSessionMapping:
    """Redis 기반 Local 세션 매핑"""
    
    def set_mapping(self, global_key: str, agent_id: str, local_key: str):
        """매핑 등록"""
        mapping_key = f"mapping:{global_key}:{agent_id}"
        self.redis.set(
            mapping_key,
            local_key,
            ex=settings.SESSION_MAP_TTL
        )
    
    def get_mapping(self, global_key: str, agent_id: str) -> Optional[str]:
        """매핑 조회"""
        mapping_key = f"mapping:{global_key}:{agent_id}"
        return self.redis.get(mapping_key)
```

#### 2. Task Queue 관리 (Redis Sorted Set)
**목표**: 업무 큐 상태 관리

```python
# app/services/task_queue_service.py
class TaskQueueService:
    """Task Queue 관리 (Redis Sorted Set)"""
    
    def add_task(self, global_key: str, task: Dict[str, Any]):
        """Task 추가"""
        score = time.time()  # timestamp
        self.redis.zadd(
            f"queue:{global_key}",
            {json.dumps(task): score}
        )
    
    def get_queue_status(self, global_key: str) -> str:
        """Queue 상태 조회"""
        count = self.redis.zcard(f"queue:{global_key}")
        return "notnull" if count > 0 else "null"
    
    def pop_task(self, global_key: str) -> Optional[Dict[str, Any]]:
        """Task 꺼내기 (FIFO)"""
        result = self.redis.zpopmin(f"queue:{global_key}", 1)
        if result:
            task_json, _ = result[0]
            return json.loads(task_json)
        return None
```

#### 3. 세션 만료 처리
**목표**: TTL 만료 시 자동 정리

```python
# app/services/session_cleanup_service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class SessionCleanupService:
    """세션 만료 처리 (스케줄러)"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """스케줄러 시작"""
        # 매 10분마다 만료 세션 정리
        self.scheduler.add_job(
            self.cleanup_expired_sessions,
            'interval',
            minutes=10
        )
        self.scheduler.start()
    
    def cleanup_expired_sessions(self):
        """만료된 세션 정리"""
        # PostgreSQL에서 만료된 세션 조회
        expired = self.db.query(Session).filter(
            Session.expires_at < datetime.utcnow()
        ).all()
        
        for session in expired:
            # Redis 캐시 삭제
            self.cache.delete(session.global_session_key)
            
            # PostgreSQL 상태 업데이트 또는 삭제
            session.session_state = "expired"
            self.db.commit()
```

#### 4. 프로파일 실제 조회 (VDB 연동)
**목표**: Mock → 실제 DB 조회

```python
# app/services/profile_service.py (수정)
class ProfileService:
    def get_customer_profile(self, user_id: str):
        # PostgreSQL에서 조회
        profiles = self.repo.get(user_id)
        
        if not profiles:
            # VDB에서 가져오기 (외부 API 호출)
            profiles = self.fetch_from_vdb(user_id)
            
            # DB에 캐싱
            if profiles:
                self.repo.batch_upsert(profiles)
        
        return profiles
```

#### 5. 배치 업로드 최적화
**목표**: Bulk Insert/Upsert 성능 개선

```python
# app/repositories/postgres/profile_repository.py
from sqlalchemy.dialects.postgresql import insert

class PostgresProfileRepository:
    def batch_upsert(self, profiles: List[Dict[str, Any]]) -> int:
        """Bulk Upsert (PostgreSQL ON CONFLICT)"""
        stmt = insert(CustomerProfile).values(profiles)
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'attribute_key'],
            set_={
                'attribute_value': stmt.excluded.attribute_value,
                'updated_at': datetime.utcnow(),
            }
        )
        
        result = self.db.execute(stmt)
        self.db.commit()
        
        return result.rowcount
```

---

---

## 🟢 P2: 개선 사항 (추후)

### 1. Redis Cluster 지원
현재 단일 Redis 인스턴스 → Cluster 모드

### 2. 세션 만료 이벤트
TTL 만료 시 정리 로직 (Celery/APScheduler)

### 3. 메트릭/모니터링
Prometheus metrics, 로깅 강화

### 4. Rate Limiting
호출자별 API Rate Limit

### 5. API 버저닝
v2 마이그레이션 대비

---

## 📝 구현 순서 (Sprint별)

### Sprint 1 (현재)
```
✅ SQLAlchemy 모델 정의
   └── app/models/*.py (완료)

🔄 Mock Repository 구현
   └── app/repositories/mock/*.py

🔄 Service Layer 리팩토링
   └── Repository 패턴 적용

🔄 Dependency Injection
   └── Mock Repository 주입
```

### Sprint 2 (다음)
```
PostgreSQL 연결
   └── app/db/postgres.py

Alembic 마이그레이션
   └── alembic/versions/*.py

Real Repository 구현
   └── app/repositories/postgres/*.py

Redis + DB Hybrid
   └── 캐시 레이어 추가
```

### Sprint 3 (추후)
```
Redis 연결
   └── app/db/redis.py

Fallback 로직
   └── Redis 장애 대응

프로파일 실제 조회
   └── VDB 연동

배치 업로드
   └── Bulk insert/upsert
```

---

## 🚀 uv 환경 설정

```bash
# 1. uv 설치 (Mac)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 가상환경 생성
uv venv

# 3. 의존성 설치
uv pip install -e ".[dev]"

# 4. 서버 실행
uv run uvicorn app.main:app --reload

# 5. 테스트 실행
uv run pytest tests/ -v

# 6. 린트 실행
uv run ruff check .
uv run ruff format .
```

---

## 🔧 빠른 시작 (개발자용)

```bash
# 전체 설정
uv venv && uv pip install -e ".[dev]"

# 서버 실행 (Mock 모드)
uv run uvicorn app.main:app --reload --port 8000

# API 문서 확인
open http://localhost:8000/api/v1/docs

# 테스트
uv run pytest tests/ -v --cov=app
```
