# Session Manager API 명세 (Sprint 6 기준)

> **Sprint 6 구현 기준** – MinIO 기반 배치 프로파일 조회, 세션 라이프사이클 ES 로그 적재
> **Session Manager 역할**: 세션/컨텍스트/프로파일 메타데이터 저장 및 조회 (Redis 필수, MinIO 선택적, ES 로그 파일 선택적)

---

## 0. Sprint 5 문서와 무엇이 달라졌나?

이 문서는 [docs/Session_Manager_API_Sprint5.md](Session_Manager_API_Sprint5.md) 기준에서 **Sprint 6 실제 코드**에 맞게 변경 사항을 정리한 **증분(diff) 문서**입니다.

API 스펙(엔드포인트, 요청/응답 스키마)은 Sprint 5와 동일하며, **저장소 구현과 로그 적재 방식만 변경/추가**되었습니다.

### 0.1 주요 변경 요약

1. **배치 프로파일 저장소: MariaDB → MinIO**
   - Sprint 5: `MariaDBBatchProfileRepository` 를 통한 RDB 조회 (선택적)
   - Sprint 6: `MinioBatchProfileRepository` 를 통한 **MinIO Object Storage 기반 조회 (선택적)**
   - MinIO에서 일 배치/월 배치 JSON 라인을 읽어와 Redis에 캐시하고, 세션 조회 시 `batch_profile` 로 반환

2. **세션 라이프사이클 ES 로그 적재 추가**
   - 서비스 레이어에서 세션의 **생성/조회/상태 변경/종료/실시간·배치 프로파일 저장** 시점에
     **ES 전용 로그 파일(eslog_*.log)로 JSON 로그**를 남김
   - 로그 파일은 별도 Log 수집기(Filebeat/Fluent Bit 등)가 Elasticsearch로 전송하는 것을 가정

3. **환경 변수 & 설정 정리**
   - MariaDB 관련 환경 변수 제거
   - MinIO 관련 환경 변수(`MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`) 추가/정리
   - ES 로그 디렉터리 경로를 제어하는 `ES_LOG_PATH` 추가

---

## 1. 저장소 구조 변경 (배치 프로파일)

### 1.1 개요

- Sprint 6에서는 배치 프로파일을 **MariaDB가 아닌 MinIO** 에서 조회합니다.
- MinIO에는 **일 배치/월 배치 JSON Lines 파일**이 저장되어 있고, Session Manager는 이를 읽어 특정 `CUSNO` 의 레코드만 찾아냅니다.
- 찾은 배치 프로파일은 Redis에 캐시된 뒤, 세션 조회 응답의 `batch_profile` 필드로 반환됩니다.

### 1.2 관련 컴포넌트

- Repository:
  - `app/repositories/minio_batch_profile_repository.py`
- 서비스:
  - `app/services/profile_service.py` – 실시간/배치 프로파일 저장 로직
  - `app/services/batch_profile_minio_retrieve.py` – MinIO에서 `CUSNO` 기준으로 배치 프로파일 조회

### 1.3 동작 흐름 (요약)

1. MA가 **실시간 프로파일 업데이트 API** 를 호출할 때, 요청 Body 안에 `cusnoN10` 이 포함되어 있으면:
   - `ProfileService.update_realtime_personal_context` 에서 `cusnoN10` 을 추출하여 세션의 `cusno` 필드에 저장
   - 동시에 MinIO에서 해당 CUSNO의 **배치 프로파일(daily, monthly)** 을 조회 시도
2. MinIO 조회가 성공하면:
   - Redis에 `profile:batch:{cusno}` 키로 배치 프로파일을 저장
3. 이후 세션 조회(`GET /api/v1/sessions/{global_session_key}`) 시:
   - 세션의 `cusno` 값을 기준으로 `profile:batch:{cusno}` 를 읽어서 `batch_profile` 로 반환

### 1.4 Redis 키 구조 (배치/실시간 프로파일)

Sprint 5와 동일하지만, **배치 프로파일의 실제 소스가 MinIO로 변경**되었습니다.

- 실시간 프로파일
  - `profile:realtime:{cusno}` – `cusnoN10` 기반 실시간 프로파일
  - `profile:realtime:{global_session_key}` – `cusnoN10` 이 없을 때 세션 키 기반으로 저장
- 배치 프로파일 (MinIO → Redis 캐시)
  - `profile:batch:{cusno}` – MinIO에서 조회한 배치 프로파일(daily/monthly)을 통째로 저장

### 1.5 MinIO 파일 구조 예시

기본 버킷 이름은 `MINIO_BUCKET` (기본값: `shinhanobj`) 이며, 일/월 배치는 Prefix로 구분됩니다.

- 일 배치(Daily) Prefix: `ifc_cus_dd_smry_tot`  (코드 상 `PREFIX_DAILY`)
- 월 배치(Monthly) Prefix: `ifc_cus_mmby_smry_tot` (코드 상 `PREFIX_MONTHLY`)

#### 1.5.1 일 배치 디렉터리 구조 예시

```text
shinhanobj/
  ifc_cus_dd_smry_tot/
    _latest_date.json                    # 최신 일자 및 use_latest 플래그 메타데이터
    20250121/                            # STD_DT(YYYYMMDD) 기준 디렉터리
      bulk.jsonl                         # 일자 전체 레코드(JSON Lines)
      index_000.json                     # CUSNO 샤드 인덱스 (예: 끝 3자리 000~999)
      index_001.json
      ...
      index.json                         # 전체 인덱스(옵션, 환경에 따라 사용)
      7000001.json                       # CUSNO 단건 JSON(옵션, 존재할 수도 있고 없을 수도 있음)
    latest/                              # use_latest=true 이거나 fallback 용 최신 경로
      bulk.jsonl
      index_000.json
      index.json
      7000001.json
```

`_latest_date.json` 예시:

```json
{
  "latest_date": "20250121",
  "use_latest": true
}
```

샤드 인덱스(`index_000.json`) 예시:

```json
{
  "7000001": [123456, 789],  // bulk.jsonl 안에서 offset=123456, length=789
  "7000002": [124245, 812]
}
```

`bulk.jsonl` 안의 한 줄 예시 (CUSNO 한 건):

```json
{
  "CUSNO": "7000001",
  "encrypted_yn": 0,
  "data": {
    "STD_DT": "20250121",
    "ACCT_CNT": 3,
    "AVG_BAL": 1500000,
    "AVG_DEP_AMT": 200000
  }
}
```

월 배치(Monthly)의 경우에도 동일한 구조이며, Prefix와 기준 값만 다릅니다.

- Prefix: `ifc_cus_mmby_smry_tot`
- 날짜 대신 기준 연월 `STD_YM`(YYYYMM)을 디렉터리 이름으로 사용 (예: `202501/`)
- 나머지 파일 이름(`_latest_date.json`, `bulk.jsonl`, `index_*.json`, `{CUSNO}.json`) 패턴은 동일

---

## 2. 세션 라이프사이클 ES 로그 적재

### 2.1 개요

- Sprint 6에서는 **세션의 주요 라이프사이클 이벤트**를 ES 전용 로그 파일에 적재합니다.
- 이 로그는 이후 Log 수집기(예: Filebeat, Fluent Bit)가 Elasticsearch로 전송하여 검색/분석에 사용됩니다.
- JSON 포맷으로 기록되며, 공통 스키마를 가진 `payload` 와 `logType` 으로 구분됩니다.

### 2.2 로그 파일 구성

- 로그 파일 이름: `eslog_{pod_uid}.log`
- 위치: 환경 변수 `ES_LOG_PATH` 로 제어 (예: `./eslogs/eslog_xxx.log`)
- 회전 정책: `TimedRotatingFileHandler` 로 일 단위 회전 (코드 기준)

### 2.3 로그 타입

현재 Session Manager는 아래 **5가지 logType** 만 ES 로그로 남깁니다.

1. `SESSION_CREATE`
   - 언제: 세션 생성 성공 후 (`POST /api/v1/sessions`)
   - 주요 필드 예시:
     - `sessionId`: `global_session_key`
     - `payload.userId`: 세션 사용자 ID
     - `payload.channel`: 진입 채널 정보 (`eventType`, `eventChannel`)
     - `payload.startType`: 진입 타입 (필요 시)

2. `SESSION_RESOLVE`
   - 언제: 세션 조회 시 (`GET /api/v1/sessions/{global_session_key}`)
   - 주요 필드 예시:
     - `sessionId`: `global_session_key`
     - `payload.sessionState`: 현재 세션 상태 (`start`/`talk`/`end`)
     - `payload.cusno`: 세션에 매핑된 CUSNO (있을 경우)
     - `payload.agentType`: 조회 요청 시 전달된 `agent_type`
     - `payload.isFirstCall`: `session_state == "start"` 여부

3. `SESSION_STATE_UPDATE`
   - 언제: 세션 상태/멀티턴 컨텍스트 업데이트 시 (`PATCH /api/v1/sessions/{global_session_key}/state`)
   - 주요 필드 예시:
     - `sessionId`: `global_session_key`
     - `turnId`: 요청에서 전달된 `turn_id`
     - `payload.newSessionState`: 변경 이후 세션 상태
     - `payload.hasStatePatch`: `state_patch` 유무

4. `SESSION_CLOSE`
   - 언제:
     - 키 기반 종료: `DELETE /api/v1/sessions/{global_session_key}` (있는 경우)
     - 토큰 기반 종료: `DELETE /api/v1/sessions` (Authorization 헤더 기반)
   - 주요 필드 예시:
     - `sessionId`: `global_session_key`
     - `transactionId`: 토큰 기반 종료 시 JTI, 그 외에는 `-` 또는 빈 값
     - `payload.closeReason`: 종료 사유 (query param `close_reason`)
     - `payload.closedAt`: 종료 시각

5. `REALTIME_BATCH_PROFILE_UPDATE`
   - 언제: 실시간 프로파일 업데이트 시 (`POST /api/v1/sessions/{global_session_key}/profiles/realtime`)
   - 주요 필드 예시:
     - `sessionId`: `global_session_key`
     - `payload.cusno`: 요청에서 추출한 `cusnoN10` (없으면 빈 문자열)
     - `payload.hasCusno`: `cusnoN10` 존재 여부
     - `payload.savedRealtimeKey`: 실시간 프로파일이 저장된 Redis 키 기준 (`cusno` 또는 `global_session_key`)
     - `payload.batchProfileFetched`: MinIO에서 배치 프로파일을 성공적으로 가져왔는지 여부

### 2.4 구현 위치

- 로거/핸들러 설정: `app/logger_config.py`
  - 커스텀 레벨: `ESLOG`
  - 헬퍼: `logger.eslog(LoggerExtraData(...))`
  - 파일 핸들러 초기화: `setup_es_logger()`
- 초기화 시점: `app/main.py` 의 FastAPI `lifespan` 안에서 **서버 기동 시 1회 호출**
- 서비스 레이어에서의 사용:
  - `app/services/session_service.py`
    - `create_session` → `SESSION_CREATE`
    - `resolve_session` → `SESSION_RESOLVE`
    - `patch_session_state` → `SESSION_STATE_UPDATE`
    - `close_session` (키 기반) → `SESSION_CLOSE`
  - `app/services/auth_service.py`
    - `close_session_by_token` (토큰 기반) → `SESSION_CLOSE`
  - `app/services/profile_service.py`
    - `update_realtime_personal_context` → `REALTIME_BATCH_PROFILE_UPDATE`

### 2.5 ES 로그 JSON 예시 한 줄

실제 파일에는 Python logging 포맷터가 붙기 때문에 아래와 같이 **앞부분은 로그 메타데이터**, 뒷부분이
`LoggerExtraData` 를 JSON으로 dump 한 문자열입니다.

```text
2026-01-13 10:30:00,123 [ESLOG] session_service.py:120 create_session() - {"logType":"SESSION_CREATE","sessionId":"gsess_20260113_abc123","turnId":"-","agentId":"-","transactionId":"-","payload":{"userId":"0616001905","channel":{"eventType":"ICON_ENTRY","eventChannel":"mobile"},"startType":"ICON_ENTRY","createdAt":"2026-01-13T10:30:00+09:00"}}
```

위 예시에서 **중괄호 내부**가 ES 수집 대상 JSON이며, 주요 필드는 다음과 같습니다.

- `logType`: 로그 유형 (`SESSION_CREATE` 등)
- `sessionId`: 글로벌 세션 키
- `turnId` / `agentId` / `transactionId`: 상황에 따라 채워지는 식별자
- `payload`: 각 logType 별 상세 정보 (세션 상태, cusno, 프로파일 저장 여부 등)

---

## 3. 환경 변수 정리 (Sprint 6 기준)

### 3.1 필수

- `REDIS_URL` – Redis 연결 URL
- `JWT_SECRET_KEY` – JWT 서명 키

### 3.2 선택적 (기본값 있음)

- `DEBUG` – 디버그 모드 여부 (기본: `true`)
- `API_PREFIX` – API Prefix (기본: `/api/v1`)
- `ALLOWED_ORIGINS` – CORS 허용 Origin 목록 (기본: `*`)
- `REDIS_MAX_CONNECTIONS` – Redis 연결 풀 사이즈 (기본: `10`)
- `SESSION_CACHE_TTL` – 세션/프로파일 TTL 초 단위 (기본: `300`)
- `GLOBAL_SESSION_PREFIX` – 글로벌 세션 키 prefix (기본: `gsess`)
- `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` – Access Token 만료 시간 (기본: `300`)
- `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` – Refresh Token 만료 시간 (기본: `330`)

### 3.3 ES 로그 관련

- `ES_LOG_PATH`
  - ES 전용 로그 파일(eslog_*.log)을 남길 디렉터리 경로
  - 예시 (로컬): `ES_LOG_PATH=eslogs`  → 프로젝트 루트 기준 `./eslogs` 디렉터리 사용
  - 운영 환경: PVC 또는 로컬 디스크 마운트 경로 등으로 설정

### 3.4 MinIO 관련 (배치 프로파일 조회용, 선택적)

- `MINIO_ENDPOINT`
  - MinIO 접속 엔드포인트 (예: `http://minio-host:9000`)
- `MINIO_ACCESS_KEY`
  - MinIO Access Key
- `MINIO_SECRET_KEY`
  - MinIO Secret Key
- `MINIO_BUCKET`
  - 배치 프로파일이 저장된 버킷 이름 (코드 기본값이 있다면 생략 가능)

MinIO 관련 값이 설정되지 않은 경우, **배치 프로파일 조회는 비활성화**되며 서비스는
실시간 프로파일과 세션 관리 기능만으로 정상 동작합니다.

---

## 4. README / 아키텍처 상의 위치 변경 요약

Sprint 6 기준으로 아키텍처/README 상에서 다음과 같이 이해하면 됩니다.

- Repository Layer
  - `RedisSessionRepository` – 세션/턴/매핑 저장 (Redis)
  - `MinioBatchProfileRepository` – 배치 프로파일 조회 (MinIO, 선택적)
- Service Layer
  - `ProfileService` – 실시간/배치 프로파일 조회 및 Redis 저장
  - `SessionService` / `AuthService` – 세션 생성/조회/상태 변경/종료, JWT 통합
- Logging
  - 기존 애플리케이션 로그와 별도로, **ES 전용 세션 로그를 분리된 파일(eslog_*.log)** 로 남김
  - `ES_LOG_PATH` 를 통해 파일 위치를 제어하고, 이후 별도 수집기가 Elasticsearch 로 전송

상세한 엔드포인트 스펙과 예제 요청/응답은 [docs/Session_Manager_API_Sprint5.md](Session_Manager_API_Sprint5.md)를 그대로 사용하면 됩니다.
