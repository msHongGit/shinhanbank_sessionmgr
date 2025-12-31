# Session Manager - Product Requirements Document (PRD)

## 1. 개요

### 1.1 제품 목적
Session Manager(SM)는 은행 AI Agent 시스템에서 세션 생명주기, 고객 프로파일, Task Queue 상태를 관리하는 핵심 API 서비스입니다.

### 1.2 배경
- Master Agent(MA)는 Stateless 구조로 설계되어 외부 상태 저장소 필요
- 세션 상태, Task Queue, 고객 프로파일을 중앙에서 관리해야 함
- Agent GW, MA, Portal 등 다양한 클라이언트가 세션 정보에 접근

### 1.3 목표
- 세션 생명주기(생성/조회/업데이트/종료) 관리
- Task Queue 상태 관리 (Redis 연동)
- 고객 프로파일 관리 (배치 연동)
- 대화 이력 관리 (Portal 연동)

---

## 2. 사용자 및 이해관계자

### 2.1 주요 사용자
| 사용자 | 역할 | 주요 API |
|--------|------|----------|
| Agent GW | 초기 세션 생성 | CreateInitialSession |
| Master Agent | 세션 조회/업데이트, Task 관리 | ResolveSession, PatchSessionState, EnqueueTask |
| Portal Admin | 대화 이력 조회/삭제 | ListConversations, DeleteHistory |
| Vertical DB | 고객 프로파일 배치 연동 | BatchUpsertCustomerProfiles |

### 2.2 이해관계자
- 개발팀: API 개발 및 유지보수
- 인프라팀: 배포 및 모니터링
- 보안팀: 고객 정보 보호

---

## 3. 기능 요구사항

### 3.1 세션 생명주기 API

#### FR-001: CreateInitialSession
- **설명**: AGW가 최초 진입 시 초기 세션 생성
- **우선순위**: P0 (필수)
- **입력**: user_id, channel, session_key, request_id
- **출력**: session_id, conversation_id, session_state, expires_at
- **비즈니스 규칙**:
  - session_key가 존재하면 기존 세션 반환
  - 존재하지 않으면 새 세션 생성
  - 만료된 세션은 새로 생성

#### FR-002: ResolveSession
- **설명**: MA가 세션을 조회하고 현재 상태 획득
- **우선순위**: P0 (필수)
- **입력**: session_key, channel, conversation_id?, user_id_ref?
- **출력**: session_id, session_state, is_first_call, task_queue_status, subagent_status, last_event, customer_profile_ref
- **비즈니스 규칙**:
  - 세션이 없으면 자동 생성
  - Redis 캐시 우선 조회, 없으면 PostgreSQL 조회

#### FR-003: PatchSessionState
- **설명**: MA가 세션 상태 업데이트
- **우선순위**: P0 (필수)
- **입력**: session_id, conversation_id, turn_id, session_state, state_patch
- **출력**: status, updated_at
- **비즈니스 규칙**:
  - state_patch에 포함된 필드만 업데이트
  - 업데이트 후 Redis 캐시 갱신
  - 비동기로 PostgreSQL 스냅샷 저장

#### FR-004: CloseSession
- **설명**: 세션 종료 및 메타정보 취합
- **우선순위**: P0 (필수)
- **입력**: session_id, conversation_id, close_reason, final_summary?
- **출력**: status, closed_at, archived_conversation_id
- **비즈니스 규칙**:
  - 세션 상태를 "end"로 변경
  - Task Queue 정리
  - 대화 이력 아카이브

### 3.2 Task Queue 관리 API

#### FR-005: EnqueueTask
- **설명**: Task Queue에 작업 적재
- **우선순위**: P0 (필수)
- **입력**: session_id, conversation_id, turn_id, intent, priority, session_state, task_payload
- **출력**: status, task_id
- **비즈니스 규칙**:
  - priority 기준 정렬
  - 동일 session_id 내에서 task_id 고유

#### FR-006: GetTaskStatus
- **설명**: Task 실행 상태 조회
- **우선순위**: P1 (중요)
- **입력**: task_id
- **출력**: task_id, task_status, progress?, updated_at

#### FR-007: GetTaskResult
- **설명**: Task 실행 결과 조회
- **우선순위**: P1 (중요)
- **입력**: task_id
- **출력**: task_id, task_status, outcome, response_text?, result_payload?

### 3.3 고객 프로파일 API

#### FR-008: GetCustomerProfile
- **설명**: 고객 프로파일 조회
- **우선순위**: P1 (중요)
- **입력**: session_id, user_id, attribute_keys?
- **출력**: user_id, attributes[], computed_at

#### FR-009: BatchUpsertCustomerProfiles
- **설명**: 고객 프로파일 배치 연동
- **우선순위**: P1 (중요)
- **입력**: batch_id, source_system, computed_at, records[]
- **출력**: batch_id, accepted, processed_count, failed_count, errors?

### 3.4 Portal 관리 API

#### FR-010: ListConversationsByPeriod
- **설명**: 기간별 대화 이력 목록 조회
- **우선순위**: P2 (보통)
- **입력**: admin_id, from_datetime, to_datetime, cursor?, limit?, filters?
- **출력**: success, data{items[], cursor_next, total_count}, error?

#### FR-011: GetConversationDetail
- **설명**: 대화 상세 조회
- **우선순위**: P2 (보통)
- **입력**: admin_id, conversation_id, cursor?, limit?
- **출력**: success, data{conversation_id, session_id, items[], cursor_next}, error?

#### FR-012: DeleteConversationHistory
- **설명**: 대화 이력 삭제
- **우선순위**: P2 (보통)
- **입력**: admin_id, conversation_id, reason?
- **출력**: success, data{conversation_id, deleted}, error?

---

## 4. 비기능 요구사항

### 4.1 성능
- **NFR-001**: API 응답 시간 95th percentile < 100ms
- **NFR-002**: 동시 처리 능력 > 1000 RPS
- **NFR-003**: Redis 캐시 히트율 > 95%

### 4.2 가용성
- **NFR-004**: 서비스 가용성 > 99.9%
- **NFR-005**: 장애 복구 시간 < 5분

### 4.3 보안
- **NFR-006**: 모든 API는 인증 필수 (JWT 또는 API Key)
- **NFR-007**: 고객 정보는 암호화 저장
- **NFR-008**: 감사 로그 기록

### 4.4 확장성
- **NFR-009**: 수평 확장 지원 (Stateless 설계)
- **NFR-010**: 컨테이너 기반 배포 (Docker/K8s)

---

## 5. 기술 스택

| 구분 | 기술 |
|------|------|
| Framework | FastAPI |
| Language | Python 3.11+ |
| Validation | Pydantic v2 |
| Cache | Redis |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Container | Docker |
| Documentation | OpenAPI (Swagger) |

---

## 6. 인터페이스 연동

### 6.1 내부 연동
| 연동 | 방식 | 설명 |
|------|------|------|
| SM ↔ Redis | Direct (Sync) | 세션 캐시, Task Queue |
| SM ↔ PostgreSQL | Direct (Async) | 영속 저장 |

### 6.2 외부 연동
| 연동 | 방식 | 설명 |
|------|------|------|
| AGW → SM | RESTful (Sync) | 세션 생성 |
| MA → SM | RESTful (Sync) | 세션 조회/업데이트 |
| Portal → SM | RESTful (Sync) | 이력 관리 |
| VDB → SM | RESTful (Batch) | 프로파일 배치 |

---

## 7. 마일스톤

| Phase | 기간 | 목표 |
|-------|------|------|
| Phase 1 | Week 1-2 | 세션 생명주기 API (FR-001~004) |
| Phase 2 | Week 3 | Task Queue API (FR-005~007) |
| Phase 3 | Week 4 | 고객 프로파일 API (FR-008~009) |
| Phase 4 | Week 5 | Portal 관리 API (FR-010~012) |
| Phase 5 | Week 6 | 테스트 및 최적화 |

---

## 8. 성공 지표

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| API 응답 시간 | p95 < 100ms | APM 모니터링 |
| 에러율 | < 0.1% | 로그 분석 |
| 캐시 히트율 | > 95% | Redis 메트릭 |
| 코드 커버리지 | > 80% | pytest-cov |

---

## 9. 리스크 및 대응

| 리스크 | 영향 | 대응 방안 |
|--------|------|----------|
| Redis 장애 | 높음 | Redis Cluster 구성, Fallback to PostgreSQL |
| PostgreSQL 장애 | 높음 | Read Replica, Connection Pool |
| 트래픽 급증 | 중간 | Auto Scaling, Rate Limiting |

---

## 10. 변경 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0 | 2025-03-16 | - | 초기 작성 |
