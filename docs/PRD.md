# Session Manager - PRD (Product Requirements Document)

## 1. 개요

### 1.1 제품 목적
Session Manager(SM)는 은행 AI Agent 시스템에서 세션 상태와 대화 이력을 중앙 관리하는 서비스입니다.

### 1.2 핵심 가치
- **세션 일관성**: Global/Local 세션 매핑으로 멀티턴 대화 지원
- **중앙 집중화**: 모든 세션 상태를 단일 서비스에서 관리
- **호출자 분리**: AGW, MA, Portal, VDB 각각 역할에 맞는 API 제공

---

## 2. 이해관계자

| 역할 | 설명 | SM 사용 목적 |
|------|------|-------------|
| **Client** | 사용자 앱/웹 | Global Session Key 발급 (직접 연동 없음) |
| **Agent GW** | 클라이언트 전처리, 연동 | 초기 세션 생성 요청 |
| **MA (Master Agent)** | 전체 대화 주관 | 세션 조회/업데이트, 대화 이력 관리 |
| **SA (Sub Agent)** | 개별 업무 처리 | 직접 연동 없음 (MA 통해 간접) |
| **Portal** | 관리자 화면 | 세션 조회, Context 삭제 |
| **VDB** | 고객 데이터 시스템 | 프로파일 배치 업로드 |

---

## 3. 기능 요구사항

### 3.1 AGW API (Agent Gateway)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| AGW-01 | 초기 세션 생성 | Client가 발급한 Global Key로 세션 생성 | P0 |
| AGW-02 | 기존 세션 반환 | 유효한 세션 있으면 재사용 | P0 |

### 3.2 MA API (Master Agent)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| MA-01 | 세션 조회 (Resolve) | 세션 상태, Task Queue, SubAgent 상태 조회 | P0 |
| MA-02 | Local 세션 등록 | 업무 Agent Start 후 매핑 저장 | P0 |
| MA-03 | Local 세션 조회 | Global→Local 키 조회 | P0 |
| MA-04 | 세션 상태 업데이트 | SubAgent 상태, Last Event 업데이트 | P0 |
| MA-05 | 세션 종료 | 세션 종료, Local 매핑 정리 | P0 |
| MA-06 | 대화 이력 조회 | Talk 요청용 History 조회 | P0 |
| MA-07 | 대화 턴 저장 | 사용자/어시스턴트 발화 저장 | P0 |
| MA-08 | 프로파일 조회 | Start 요청용 프로파일 조회 | P0 |

### 3.3 Portal API

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| PT-01 | 세션 목록 조회 | 필터/페이징 지원, 읽기 전용 | P1 |
| PT-02 | Context 정보 조회 | context_id로 메타 정보 조회 | P1 |
| PT-03 | Context 삭제 | context_id 기준 대화 이력 삭제 | P0 |

### 3.4 Batch API (VDB)

| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| VDB-01 | 프로파일 배치 업로드 | 다수 프로파일 Upsert | P1 |

---

## 4. 비기능 요구사항

### 4.1 성능
- API 응답 시간: p95 < 100ms
- 동시 세션 처리: 10,000 세션 이상

### 4.2 가용성
- SLA: 99.9%
- Redis 장애 시 PostgreSQL Fallback (TODO)

### 4.3 보안
- 호출자별 API Key 분리
- 세션 키 노출 방지

### 4.4 확장성
- 수평 확장 가능한 Stateless 설계
- Redis Cluster 지원 (TODO)

---

## 5. 제약사항

### 5.1 연동 범위
- SM ↔ SA: **직접 연동 없음** (MA가 담당)
- SM ↔ Client: **직접 연동 없음** (AGW가 담당)

### 5.2 권한 범위
- Portal: 세션 **삭제 불가**, Context만 삭제 가능
- AGW: 세션 **생성만** 가능

---

## 6. 용어 정의

| 용어 | 설명 |
|------|------|
| **Global Session Key** | Client가 발급, 전체 대화 식별 |
| **Local Session Key** | 업무 Agent가 발급, 멀티턴 식별 |
| **Context ID** | SM이 발급, 대화 이력 식별 |
| **Conversation ID** | SM이 발급, 대화 인스턴스 식별 |

---

## 7. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-03-16 | 초기 작성 |
