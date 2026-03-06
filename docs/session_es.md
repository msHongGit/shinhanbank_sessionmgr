# Session Manager ES 연동 설계 (활성 세션 카운트)

## 1. 목적

- Redis TTL(5분)을 그대로 사용하면서, Elasticsearch 인덱스를 통해 **현재 활성 세션 수**를 조회할 수 있도록 한다.
- Session Manager 애플리케이션은 **ES에 직접 연결하지 않고**, `logger_config.py` 를 통해 ESLOG 파일만 남긴다.
- ES 적재/인덱싱은 Filebeat/Fluent Bit/Fluentd 등 로그 수집 파이프라인에서 처리한다.

---

## 2. ESLOG 이벤트 정의

### 공통 포맷 (`LoggerExtraData`)

- `logType`: 이벤트 타입 (문자열)
- `sessionId`: 글로벌 세션 키 (예: `gsess_xxx`)
- `turnId`, `agentId`, `transactionId`: 현재는 "-" 또는 jti 사용
- `payload`: 이벤트별 상세 정보 (JSON 객체)

### 세션 관련 logType

Session Manager에서 ESLOG로 남기는 주요 세션 이벤트는 다음과 같다.

1. `SESSION_CREATE`
   - 위치: `SessionService.create_session`
   - 의미: 세션 최초 생성
   - payload 예시:
     - `userId`, `channel`, `startType`, `createdAt`

2. `SESSION_RESOLVE`
   - 위치: `SessionService.resolve_session`
   - 의미: 세션 조회 (API: `GET /sessions/{key}`, `/sessions/{key}/full` 등)

3. `SESSION_STATE_UPDATE`
   - 위치: `SessionService.patch_session_state`
   - 의미: 세션 상태/추가 정보 PATCH

4. `REALTIME_BATCH_PROFILE_UPDATE`
   - 위치: `ProfileService.update_realtime_personal_context`
   - 의미: 실시간/배치 프로파일 저장 결과 (배치 프로파일 조회 성공 여부 포함)

5. `SESSION_CLOSE`
   - 위치:
     - `SessionService.close_session` (명시적 종료 API)
     - `AuthService.close_session_by_token` (토큰 기반 종료)
   - 의미: 세션 종료
   - payload 예시:
     - `closeReason`, `closedAt`, `byToken`

6. `SESSION_VERIFY` 
   - 위치: `AuthService.verify_token_and_get_session`
   - 의미: Access Token 검증 및 세션 생존 여부 확인 (API: `GET /sessions/verify`)
   - payload 예시:
     - `result`: "success"
     - `reason`: "verify"
     - `isAlive`: `true` / `false`

7. `SESSION_REFRESH`
   - 위치: `AuthService.refresh_token`
   - 의미: Refresh Token 기반 토큰 재발급 + 세션 TTL 연장 (API: `POST /sessions/refresh`)
   - payload 예시:
     - `result`: "success"
     - `reason`: "refresh"

---

## 3. ES 인덱스 설계 (`session_state`)

ES 쪽에서는 세션 상태 전용 인덱스를 하나 둔다.

- 인덱스명: 예) `session_state`
- 문서 1개 = 세션 1개 (문서 `_id` = `sessionId`)

### 필드 예시

- `sessionId` (string)
- `status` (string) : `"active"` / `"end"`
- `start_time` (date)
- `end_time` (date, nullable)
- `last_update` (date)
- 그 외 필요한 필드: `userId`, `channel`, `startType`, `close_reason` 등

### ingest / 파이프라인 로직 (예시)

로그 수집 파이프라인에서 ESLOG를 읽어 `session_state` 인덱스를 갱신한다.

1. **세션 생성 (`SESSION_CREATE`)**

   - 조건: `logType == "SESSION_CREATE"`
   - 동작 (upsert):
     - `id = sessionId`
     - `status = "active"`
     - `start_time = payload.createdAt`
     - `last_update = payload.createdAt`

2. **세션 조회/업데이트/활동 heartbeat**

   다음 logType 들은 세션이 여전히 사용 중이라는 신호로 본다.

   - `SESSION_RESOLVE`
   - `SESSION_STATE_UPDATE`
   - `REALTIME_BATCH_PROFILE_UPDATE`
   - `SESSION_VERIFY`
   - `SESSION_REFRESH`

   - 조건 예시:
     - `logType` 가 위 목록 중 하나이고,
     - `payload.result == "success"` (있는 경우)
   - 동작 (update):
     - 기존 `sessionId` 문서의 `last_update = @timestamp` (또는 로그 내 시각 필드)
     - `status` 는 `"active"` 유지

3. **세션 명시적 종료 (`SESSION_CLOSE`)**

   - 조건: `logType == "SESSION_CLOSE"`
   - 동작 (update):
     - 기존 `sessionId` 문서의
       - `status = "end"`
       - `end_time = payload.closedAt`
       - `last_update = payload.closedAt`
       - `close_reason = payload.closeReason` (있는 경우)

> 세션 관련 API에서 발생하는 ESLOG 들을 heartbeat 로 사용하여 `last_update` 를 갱신한다.

---

## 4. 활성 세션 카운트 쿼리

애플리케이션 설정:

- Access Token 만료: 5분
- Refresh Token 만료: 5분 30초
- Redis 세션 TTL (`SESSION_CACHE_TTL`): 5분
- 실제 운용에서는 2-4분마다 Refresh 호출 (세션이 살아 있는 동안 계속 활동 발생)

이 설정을 고려하면, ES에서는 다음과 같이 **활성 세션 수**를 조회할 수 있다.

```json
{
  "query": {
    "bool": {
      "must": [
        { "term": { "status": "active" } },
        {
          "range": {
            "last_update": {
              "gte": "now-5m"
            }
          }
        }
      ]
    }
  }
}
```

- 의미:
  - `status = "active"` 인 세션 중에서
  - 최근 5분 이내에 한 번이라도 heartbeat 이벤트(조회/검증/갱신 등)가 있었던 세션 수를 카운트
- 장점:
  - Redis TTL(5분)과 동일한 윈도우를 사용하므로,
    실제 Redis 상에서 살아 있는 세션 수와 **거의 동일한 값**을 얻을 수 있다.

---

## 5. 동작 시나리오 정리

1. 사용자가 세션을 생성 → `SESSION_CREATE` → `session_state` 문서 생성, `status=active`, `start_time`, `last_update` 설정.
2. 세션을 조회/상태 변경/프로파일 업데이트/검증/리프레시 → 해당 logType(RESOLVE/STATE_UPDATE/REALTIME_BATCH_PROFILE_UPDATE/SESSION_VERIFY/SESSION_REFRESH) 발생 → 같은 문서의 `last_update` 갱신.
3. 사용자가 명시적으로 종료 API 호출 → `SESSION_CLOSE` → `status=end`, `end_time`, `last_update` 갱신.
4. 사용자가 아무 요청도 하지 않고 방치 → 더 이상 heartbeat 로그 없음 → `last_update` 가 멈춤 → 5분 경과 후 ES 쿼리에서 활성 세션에서 자동 제외.
