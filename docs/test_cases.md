# Session Manager 단위 테스트 케이스 명세서

> 작성일: 2026-03-01  
> 대상 서비스: Session Manager (FastAPI + Redis)  
> 테스트 범위: 순수 로직 단위 테스트 (Mock Redis/Repo 사용, HTTP 레이어 제외)

---

## 실행 방법

```bash
# 단위 테스트만 (pytest-asyncio 지원, 권장)
pytest tests/unit/ -v

# 단위 테스트만 (unittest 실행 - async 테스트 제한적)
python -m unittest discover -s tests/unit -v

# 전체 테스트 실행 (단위 + 통합)
pytest tests/ -v
```

> **주의**: `IsolatedAsyncioTestCase` 기반 async 테스트는 `pytest tests/unit/` 로 실행해야 정상 동작합니다.
> `unittest discover`만 사용하면 async 테스트가 실행되지 않을 수 있습니다.

---

## TC-LOG: LoggerExtraData 직렬화

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-LOG-001 | 로그 기본값 검증: 미명시 필드는 '-' | - | 1) `LoggerExtraData(logType="SESSION_CREATE", payload={})` 인스턴스 생성<br>2) `custNo`, `sessionId`, `turnId`, `agentId`, `transactionId` 필드 각각 조회 | `logType="SESSION_CREATE"`, `payload={}` | 5개 필드 모두 `"-"` 문자열 반환 |
| TC-LOG-002 | 로그 명시값 검증: 입력값이 기본값 덮어씀 | - | 1) `LoggerExtraData` 생성 시 custNo, sessionId, turnId, agentId, transactionId 모두 명시<br>2) 각 필드 값 조회 | `custNo="123456"`, `sessionId="gsess_001"`, `turnId="turn_1"`, `agentId="agent_1"`, `transactionId="txn_1"` | 각 필드가 입력값과 동일 |
| TC-LOG-003 | 로그 필수필드 검증: logType 없으면 ValidationError | - | 1) `LoggerExtraData(payload={})` 생성 시도 (logType 생략) | `payload={}` | `pydantic.ValidationError` 발생, 예외 없이 통과하지 않음 |
| TC-LOG-004 | SESSION_CREATE 로그 직렬화: FieldInfo 누락 방지 | - | 1) SESSION_CREATE 형태의 `LoggerExtraData` 생성 (userId, channel, startType, triggerId, createdAt 포함)<br>2) `model_dump_json()` 호출 | `logType="SESSION_CREATE"`, `payload={"userId":"700000001","channel":"SOL","startType":"ICON_ENTRY","triggerId":"TRG-001","createdAt":"2026-03-01T00:00:00+00:00"}` | `PydanticSerializationError` 미발생, 반환 JSON에 "SESSION_CREATE", "700000001" 포함 |
| TC-LOG-005 | SESSION_RESOLVE 로그 직렬화 | - | 1) `LoggerExtraData(logType="SESSION_RESOLVE", custNo="12345678", payload={...})` 생성<br>2) `model_dump_json()` 호출 | `logType="SESSION_RESOLVE"`, `custNo="12345678"`, `payload={"sessionState":"talk","agentType":"task","isFirstCall":false}` | 직렬화 성공, 결과 문자열에 "SESSION_RESOLVE", "12345678", "talk" 포함 |
| TC-LOG-006 | REALTIME_BATCH_PROFILE_UPDATE 로그 직렬화 | - | 1) REALTIME_BATCH_PROFILE_UPDATE 형태의 `LoggerExtraData` 생성<br>2) `model_dump_json()` 호출 | `logType="REALTIME_BATCH_PROFILE_UPDATE"`, `custNo="99999999"`, `payload={"hasCusno":true,"savedRealtimeKey":"99999999","batchProfileFetched":true}` | 직렬화 성공, "REALTIME_BATCH_PROFILE_UPDATE", "99999999" 포함 |
| TC-LOG-007 | SESSION_STATE_UPDATE 로그 직렬화 | - | 1) SESSION_STATE_UPDATE 형태의 `LoggerExtraData` 생성<br>2) `model_dump_json()` 호출 | `logType="SESSION_STATE_UPDATE"`, `turnId="turn_001"`, `agentId="agent_001"`, `payload={"newSessionState":"talk","hasStatePatch":true}` | 직렬화 성공, "SESSION_STATE_UPDATE", "talk" 포함 |
| TC-LOG-008 | SESSION_CLOSE 로그 직렬화 | - | 1) SESSION_CLOSE 형태의 `LoggerExtraData` 생성<br>2) `model_dump_json()` 호출 | `logType="SESSION_CLOSE"`, `custNo="11111111"`, `payload={"sessionState":"end","closedAt":"2026-03-01T00:00:00+00:00"}` | 직렬화 성공, "SESSION_CLOSE", "end" 포함 |
| TC-LOG-009 | 빈 payload dict 직렬화 | - | 1) `LoggerExtraData(logType="TEST", payload={})` 생성<br>2) `model_dump_json()` 호출 | `logType="TEST"`, `payload={}` | 직렬화 성공, 결과에 "{}" 포함 |
| TC-LOG-010 | None payload 직렬화 | - | 1) `LoggerExtraData(logType="TEST", payload=None)` 생성<br>2) `model_dump_json()` 호출 | `logType="TEST"`, `payload=None` | 직렬화 성공, "TEST" 포함 |

---

## TC-AUTH: AuthService 인증 로직

### create_tokens (세션 생성 시 토큰 발급)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-AUTH-001 | 토큰 발급: access_token, refresh_token, jti 반환 | Redis Mock 설정 | 1) `create_tokens("700000001", "gsess_test_001")` 호출<br>2) 반환 객체의 `access_token`, `refresh_token`, `jti` 필드 존재 여부 확인 | `user_id="700000001"`, `global_session_key="gsess_test_001"` | `access_token`, `refresh_token`, `jti` 3개 필드 모두 존재하고 비어있지 않음 |
| TC-AUTH-002 | 토큰 발급: jti가 UUID4 형식인지 검증 | Redis Mock 설정 | 1) `create_tokens("user", "gsess_test")` 호출<br>2) 반환된 jti를 정규식 `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`로 검증 | `user_id="user"`, `global_session_key="gsess_test"` | jti가 UUID4 형식(8-4-4-4-12 hex)과 일치 |
| TC-AUTH-003 | 토큰 발급: Redis에 jti→global_session_key 매핑 저장 | Redis Mock 설정 | 1) `create_tokens("user", "gsess_test_key")` 호출<br>2) Mock의 `set_jti_mapping(jti, "gsess_test_key", TTL)` 호출 여부 및 횟수 확인 | `global_session_key="gsess_test_key"` | `set_jti_mapping` 호출 1회, 인자 `global_session_key="gsess_test_key"` |
| TC-AUTH-004 | 토큰 발급: user_id 빈 문자열 허용 | Redis Mock 설정 | 1) `create_tokens("", "gsess_empty_user")` 호출<br>2) 반환 객체에 `access_token` 존재 여부 확인 | `user_id=""` | 예외 없이 반환, `access_token` 필드 존재 |

### verify_token_and_get_session (토큰 검증 및 세션 조회)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-AUTH-005 | 토큰 검증: 위조/만료 토큰 → 401 | - | 1) `verify_token_and_get_session("invalid_token_string")` 호출 | `token="invalid_token_string"` | `HTTPException(status_code=401)` 발생 |
| TC-AUTH-006 | 토큰 검증: refresh 토큰으로 verify → 401 | Redis Mock | 1) 유효한 refresh 토큰으로 `verify_token_and_get_session()` 호출 | refresh 토큰 문자열 | `HTTPException(status_code=401)` 발생 |
| TC-AUTH-007 | 토큰 검증: jti Redis 매핑 없음 → 401 | Redis Mock (jti 매핑 없음) | 1) 유효한 access 토큰으로 `verify_token_and_get_session()` 호출<br>2) Redis Mock은 jti 조회 시 None 반환 | 유효한 access 토큰, Redis jti 매핑 없음 | `HTTPException(status_code=401)` 발생 |
| TC-AUTH-008 | 토큰 검증: 세션 없음 → is_alive=False | Redis Mock, 세션 없음 | 1) 유효한 access 토큰으로 `verify_token_and_get_session()` 호출<br>2) 반환 객체의 `is_alive` 확인 | 유효한 access 토큰, session=None | `is_alive=False`, `session_state=""`, `expires_at=None` |
| TC-AUTH-009 | 토큰 검증: 세션 있음 → is_alive=True | Redis Mock, 세션 있음 | 1) 유효한 access 토큰으로 `verify_token_and_get_session()` 호출<br>2) 반환 객체의 `is_alive`, `session_state` 확인 | 유효한 access 토큰, session={"session_state":"talk"} | `is_alive=True` |

### refresh_token (토큰 갱신)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-AUTH-012 | 토큰 갱신: 위조 refresh 토큰 → 401 | - | 1) `refresh_token("invalid_refresh_token")` 호출 | `token="invalid_refresh_token"` | `HTTPException(status_code=401)` 발생 |
| TC-AUTH-013 | 토큰 갱신: access 토큰으로 refresh 요청 → 401 | - | 1) access 토큰으로 `refresh_token()` 호출 | access 토큰 문자열 | `HTTPException(status_code=401)` 발생 |
| TC-AUTH-014 | 토큰 갱신: 정상 refresh → 새 access, refresh, jti 반환 | Redis Mock, 세션 있음 | 1) 유효한 refresh 토큰으로 `refresh_token()` 호출<br>2) 반환된 jti가 기존과 다른지 확인 | 유효한 refresh 토큰 | 새 `access_token`, `refresh_token`, 기존과 다른 `jti` 반환 |
| TC-AUTH-015 | 토큰 갱신: refresh 성공 시 session_repo.refresh_ttl 호출 | Redis Mock, 세션 있음 | 1) 유효한 refresh 토큰으로 `refresh_token()` 호출<br>2) Mock의 `session_repo.refresh_ttl(global_session_key)` 호출 여부 확인 | 유효한 refresh 토큰 | `refresh_ttl(global_session_key)` 1회 호출 |

### close_session_by_token (토큰 기반 세션 종료)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-AUTH-016 | 토큰 기반 세션 종료: 토큰 없음 → 401 | - | 1) `DELETE /api/v1/sessions` 호출 (Authorization 헤더 없음) | - | `HTTPException(status_code=401)` 발생 |
| TC-AUTH-017 | 토큰 기반 세션 종료: 위조 토큰 → 401 | - | 1) `DELETE /api/v1/sessions` 호출 (Bearer invalid.token) | `Authorization: Bearer invalid.token` | `HTTPException(status_code=401)` 발생 |
| TC-AUTH-018 | 토큰 기반 세션 종료: 정상 → session_state='end', jti 삭제 | 세션 있음, 유효 access_token | 1) `close_session_by_token(access_token, close_reason="user_logout")` 호출<br>2) `repo.update` session_state='end' 확인<br>3) Redis jti 매핑 삭제 확인 | 유효 access_token, `close_reason="user_logout"` | `SessionCloseResponse` 반환, `session_state='end'`, jti 삭제됨 |

---

## TC-PROF: ProfileService 프로파일 로직

### _merge_profiles (배치·실시간 프로파일 병합)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-PROF-001 | 프로파일 병합: batch/realtime 모두 None → None | - | 1) `_merge_profiles(None, None)` 호출<br>2) 반환값 확인 | `batch=None`, `realtime=None` | `None` 반환 |
| TC-PROF-002 | 프로파일 병합: realtime 있으면 실시간 프로파일 우선 | - | 1) `_merge_profiles(None, realtime)` 호출<br>2) 반환값의 `user_id` 확인 | `realtime={"cusnoN10":"12345","membGdS2":"VIP"}` | `CustomerProfile` 반환, `user_id="12345"` |
| TC-PROF-003 | 프로파일 병합: realtime의 membGdS2 → segment 설정 | - | 1) `_merge_profiles(None, realtime)` 호출<br>2) 반환값의 `segment` 확인 | `realtime={"cusnoN10":"12345","membGdS2":"VIP"}` | `result.segment == "VIP"` |
| TC-PROF-004 | 프로파일 병합: realtime 빈 값은 attributes에서 제외 | - | 1) `_merge_profiles(None, realtime)` 호출 (emptyField="", noneField=None, validField="abc" 포함)<br>2) 반환 attributes의 키 목록 확인 | `realtime={"cusnoN10":"12345","emptyField":"","noneField":None,"validField":"abc"}` | attributes에 "emptyField", "noneField" 없고, "validField" 있음 |
| TC-PROF-005 | 프로파일 병합: realtime 없으면 batch 반환 | - | 1) `_merge_profiles(batch, None)` 호출 | `batch=CustomerProfile(user_id="batch_user")` | `result.user_id == "batch_user"` |
| TC-PROF-006 | 프로파일 병합: realtime 프로파일 source는 'realtime' | - | 1) `_merge_profiles(None, realtime)` 호출<br>2) 반환값의 `preferences["source"]` 확인 | `realtime={"cusnoN10":"12345","someField":"val"}` | `result.preferences["source"] == "realtime"` |
| TC-PROF-007 | 프로파일 병합: realtime에 cusnoN10 없으면 batch.user_id 사용 | batch 있음 | 1) `_merge_profiles(batch, realtime)` 호출 (realtime에 cusnoN10 없음) | `batch=CustomerProfile(user_id="fallback_user")`, `realtime={"someField":"val"}` | `result.user_id == "fallback_user"` |

### update_realtime_personal_context (실시간 프로파일 업데이트)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-PROF-008 | 실시간 프로파일 저장: 세션 없음 → SessionNotFoundError | session=None | 1) `update_realtime_personal_context("gsess_missing", req)` 호출 | `global_session_key="gsess_missing"` | `SessionNotFoundError` 발생 |
| TC-PROF-009 | 실시간 프로파일 저장: profile_data 최상위 cusnoN10에서 cusno 추출 | 세션 있음, Redis Mock | 1) `profile_data={"cusnoN10":"11111111"}` 로 호출<br>2) Mock의 `set_realtime_profile` 호출 인자 확인 | `cusnoN10="11111111"` (최상위) | `set_realtime_profile("11111111", profile_data)` 호출 |
| TC-PROF-009b | 실시간 프로파일 저장: cusnoN10 있으면 세션에 cusno 저장 | 세션 있음, Redis Mock | 1) `profile_data={"cusnoN10":"11111111"}` 로 호출<br>2) Mock의 `session_repo.update` 호출 인자 확인 | `cusnoN10="11111111"` | `session_repo.update(global_session_key, cusno="11111111")` 호출 |
| TC-PROF-010 | 실시간 프로파일 저장: profile_data.responseData 안의 cusnoN10 추출 | 세션 있음, Redis Mock | 1) `profile_data={"responseData":{"cusnoN10":"22222222"}}` 로 호출<br>2) Mock의 `set_realtime_profile` 호출 인자 확인 | `cusnoN10="22222222"` (responseData 안) | `set_realtime_profile("22222222", profile_data)` 호출 |
| TC-PROF-011 | 실시간 프로파일 저장: cusnoN10 없으면 global_session_key로 저장 | 세션 있음, Redis Mock | 1) `profile_data={"someField":"val"}` 로 호출 (cusnoN10 없음)<br>2) Mock의 `set_realtime_profile` 호출 인자 확인 | cusnoN10 없음 | `set_realtime_profile("gsess_test", profile_data)` 호출 |
| TC-PROF-012 | 실시간 프로파일 저장: profile_repo 있고 배치 있으면 Redis 저장 | 세션 있음, Redis Mock, profile_repo Mock | 1) `profile_repo.get_batch_profile` 이 배치 데이터 반환하도록 설정<br>2) cusnoN10 포함 요청으로 호출<br>3) `set_batch_profile` 호출 확인 | `cusnoN10="33333333"`, 배치 데이터 있음 | `set_batch_profile("33333333", batch_data)` 호출 |
| TC-PROF-013 | 실시간 프로파일 저장: profile_repo 없으면 배치 조회 없음 | 세션 있음, Redis Mock, profile_repo=None | 1) `profile_repo=None` 으로 서비스 생성<br>2) cusnoN10 포함 요청으로 호출<br>3) `set_batch_profile` 호출 여부 확인 | `cusnoN10="44444444"`, profile_repo=None | `set_batch_profile` 미호출 |
| TC-PROF-014 | 실시간 프로파일 저장: 정상 처리 시 status, updated_at 반환 | 세션 있음, Redis Mock | 1) 정상 프로파일 데이터로 호출<br>2) 반환 객체의 `status`, `updated_at` 확인 | `cusnoN10="55555555"` | `result.status == "success"`, `result.updated_at` not None |

---

## TC-SESS: SessionService 세션 로직

### create_session (세션 생성)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-SESS-001 | 세션 생성: 정상 입력 시 global_session_key, 토큰 반환 | Mock Repo/Auth | 1) `create_session(SessionCreateRequest(userId="700000001"))` 호출<br>2) 반환 객체의 `global_session_key`, `access_token`, `refresh_token`, `jti` 확인 | `userId="700000001"` | `global_session_key`가 "gsess_"로 시작, `access_token`, `refresh_token`, `jti` 모두 존재 |
| TC-SESS-002 | 세션 생성: channel 없으면 channel='utterance', start_type=None | Mock Repo/Auth | 1) `channel=None` 으로 세션 생성<br>2) `repo.create` 호출 인자 확인 | `userId="user_001"`, channel 없음 | `channel="utterance"`, `start_type=None` 으로 저장 |
| TC-SESS-003 | 세션 생성: channel 있으면 event_channel, event_type 그대로 사용 | Mock Repo/Auth | 1) `channel=ChannelInfo(eventType="ICON_ENTRY", eventChannel="SOL")` 으로 생성<br>2) `repo.create` 호출 인자 확인 | `eventType="ICON_ENTRY"`, `eventChannel="SOL"` | `channel="SOL"`, `start_type="ICON_ENTRY"` 로 저장 |
| TC-SESS-004 | 세션 생성: userId 없으면 user_id='' | Mock Repo/Auth | 1) `SessionCreateRequest()` (userId 없음) 으로 생성<br>2) `repo.create` 호출 인자 확인 | userId 없음 | `user_id=""` 로 저장 |
| TC-SESS-005 | 세션 생성: triggerId 없으면 trigger_id='' | Mock Repo/Auth | 1) `SessionCreateRequest(userId="user_003")` (triggerId 없음) 으로 생성<br>2) `repo.create` 호출 인자 확인 | triggerId 없음 | `trigger_id=""` 로 저장 |
| TC-SESS-006 | 세션 생성: triggerId 있으면 그대로 전달 | Mock Repo/Auth | 1) `SessionCreateRequest(userId="user_004", triggerId="TRG-001")` 으로 생성<br>2) `repo.create` 호출 인자 확인 | `triggerId="TRG-001"` | `trigger_id="TRG-001"` 로 저장 |
| TC-SESS-007 | 세션 생성: session_state='start' | Mock Repo/Auth | 1) 세션 생성<br>2) `repo.create` 호출 인자의 `session_state` 확인 | - | `session_state="start"` 로 저장 |
| TC-SESS-008 | 세션 생성: auth_service.create_tokens 호출 | Mock Repo/Auth | 1) 세션 생성<br>2) Mock의 `auth_service.create_tokens` 호출 횟수 확인 | `userId="user_006"` | `auth_service.create_tokens` 1회 호출 |
| TC-SESS-009 | SESSION_CREATE ES 로그 payload 직렬화: FieldInfo 누락 방지 | - | 1) SESSION_CREATE 형태의 LoggerExtraData 직접 생성 (userId, channel, startType, triggerId, createdAt 포함)<br>2) `model_dump_json()` 호출 | `userId`, `channel`, `startType`, `triggerId`, `createdAt` 포함 | `PydanticSerializationError` 없이 직렬화 성공 |

### resolve_session (세션 조회)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-SESS-010 | 세션 조회: 세션 없음 → SessionNotFoundError | session=None | 1) `resolve_session(SessionResolveRequest(global_session_key="gsess_missing"))` 호출 | `global_session_key="gsess_missing"` | `SessionNotFoundError` 발생 |
| TC-SESS-011 | 세션 조회: 세션 있음 → SessionResolveResponse 반환 | session 있음 | 1) 세션 존재하는 상태에서 `resolve_session()` 호출<br>2) 반환 객체의 `global_session_key`, `session_state` 확인 | `global_session_key="gsess_found"`, 세션 존재 | `result.global_session_key == "gsess_found"`, `result.session_state.value == "start"` |
| TC-SESS-012 | 세션 조회: cusno 있으면 get_batch_and_realtime_profiles 호출 | session에 cusno 있음 | 1) cusno 있는 세션에서 `resolve_session()` 호출<br>2) `profile_service.get_batch_and_realtime_profiles("12345678")` 호출 여부 확인 | session에 `cusno="12345678"` | `profile_service.get_batch_and_realtime_profiles("12345678")` 1회 호출 |
| TC-SESS-013 | 세션 조회: cusno 없으면 session_key로 실시간 프로파일 조회 | session에 cusno 없음, Redis Mock | 1) cusno 없는 세션에서 `resolve_session()` 호출<br>2) `helper.get_realtime_profile("gsess_nocusno")` 호출 여부 확인 | `global_session_key="gsess_nocusno"`, session에 cusno 없음 | `helper.get_realtime_profile("gsess_nocusno")` 호출 |
| TC-SESS-014 | 세션 조회: conversation_history가 list 아니면 None | session에 잘못된 형식 저장 | 1) Redis에 `reference_information={"conversation_history":"invalid_string"}` (JSON 직렬화) 저장된 세션 준비<br>2) `resolve_session()` 호출<br>3) `result.conversation_history` 확인 | `reference_information={"conversation_history":"invalid_string"}` | `result.conversation_history is None` |
| TC-SESS-015 | 세션 조회: turn_count가 int 아니면 None | session에 잘못된 형식 저장 | 1) Redis에 `reference_information={"turn_count":"not_int"}` 저장된 세션 준비<br>2) `resolve_session()` 호출<br>3) `result.turn_count` 확인 | `reference_information={"turn_count":"not_int"}` | `result.turn_count is None` |

### patch_session_state (세션 상태 업데이트)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-SESS-016 | 세션 상태 업데이트: 세션 없음 → SessionNotFoundError | session=None | 1) `patch_session_state(SessionPatchRequest(global_session_key="gsess_missing"))` 호출 | `global_session_key="gsess_missing"` | `SessionNotFoundError` 발생 |
| TC-SESS-017 | 세션 상태 업데이트: session_state=TALK이면 refresh_ttl 호출 | 세션 있음, Mock Repo | 1) `session_state="talk"` 로 patch 호출<br>2) Mock의 `repo.refresh_ttl` 호출 횟수 확인 | `session_state="talk"` | `repo.refresh_ttl("gsess_talk")` 1회 호출 |
| TC-SESS-018 | 세션 상태 업데이트: session_state=TALK 아니면 refresh_ttl 미호출 | 세션 있음, Mock Repo | 1) `session_state="end"` 로 patch 호출<br>2) Mock의 `repo.refresh_ttl` 호출 여부 확인 | `session_state="end"` | `repo.refresh_ttl` 미호출 |
| TC-SESS-019 | 세션 상태 업데이트: turn_id 중복 없이 누적 저장 | 세션에 기존 turn_id 있음 | 1) 기존 turn_ids `["turn_001","turn_002"]` 인 세션<br>2) `turn_id="turn_003"` 로 patch 호출<br>3) 저장값 확인 | 기존 `["turn_001","turn_002"]`, 신규 `turn_id="turn_003"` | 저장값에 "turn_003" 추가, 중복 없음 |
| TC-SESS-020 | 세션 상태 업데이트: 이미 있는 turn_id는 중복 추가 안 됨 | 세션에 기존 turn_id 있음 | 1) 기존 turn_ids `["turn_001"]` 인 세션<br>2) `turn_id="turn_001"` 로 patch 호출<br>3) 저장값 확인 | 기존 `["turn_001"]`, 신규 `turn_id="turn_001"` | 저장값에 "turn_001" 1개만 존재 |
| TC-SESS-021 | 세션 상태 업데이트: conversation_history가 list 아니면 400 | 세션 있음 | 1) `reference_information={"conversation_history":"not_a_list"}` 로 patch 호출 | `reference_information={"conversation_history":"not_a_list"}` | `HTTPException(status_code=400)` 발생 |

### close_session (세션 종료)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-SESS-022 | 세션 종료: 세션 없음 → SessionNotFoundError | session=None | 1) `close_session(SessionCloseRequest(global_session_key="gsess_missing"))` 호출 | `global_session_key="gsess_missing"` | `SessionNotFoundError` 발생 |
| TC-SESS-023 | 세션 종료: 정상 종료 시 session_state='end' 업데이트 | 세션 있음 | 1) `close_session(SessionCloseRequest(global_session_key="gsess_close", close_reason="user_request"))` 호출<br>2) `repo.update` 호출 인자 확인 | `global_session_key="gsess_close"`, `close_reason="user_request"` | `session_state='end'`, `close_reason='user_request'` 로 업데이트 |
| TC-SESS-024 | 세션 종료: archived_conversation_id 형식 검증 | 세션 있음 | 1) `close_session()` 호출<br>2) 반환 객체의 `archived_conversation_id` 확인 | `global_session_key="gsess_arch"` | `result.archived_conversation_id == "arch_gsess_arch"` |
| TC-SESS-025 | 세션 종료: final_summary 있으면 업데이트에 포함 | 세션 있음 | 1) `final_summary="This is summary"` 로 close 호출<br>2) `repo.update` 호출 인자 확인 | `final_summary="This is summary"` | `update_call["final_summary"] == "This is summary"` |

### _serialize_reference_information (reference_information 직렬화)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-SESS-026 | reference_information 직렬화: 빈 dict → '{}' | - | 1) `_serialize_reference_information({})` 호출<br>2) 반환값 확인 | `{}` | `"{}"` 반환 |
| TC-SESS-027 | reference_information 직렬화: JSON 키 알파벳 순 정렬 | - | 1) `_serialize_reference_information({"z_key":1,"a_key":2})` 호출<br>2) 반환 JSON의 키 순서 확인 | `{"z_key":1,"a_key":2}` | 키가 알파벳 순(a_key, z_key)으로 정렬된 JSON 반환 |
| TC-SESS-028 | reference_information 직렬화: list 순서 유지 | - | 1) `_serialize_reference_information({"conversation_history":[{"msg":"first"},{"msg":"second"}]})` 호출<br>2) 파싱 후 `[0].msg`, `[1].msg` 확인 | `{"conversation_history":[{"msg":"first"},{"msg":"second"}]}` | 파싱 후 `[0].msg=="first"`, `[1].msg=="second"` |

### save_api_result (실시간 API 연동 결과 저장)

| TC ID | 테스트케이스명 | 사전조건 | 테스트 수행절차 | 입력 데이터 | 기대결과 |
|---|---|---|---|---|---|
| TC-SESS-029 | api-results: 세션 없음 → 404 | session=None | 1) `POST /api/v1/sessions/{key}/api-results` 호출 (존재하지 않는 key) | `global_session_key="gsess_missing"`, `turn_id="turn_001"` | `HTTPException(status_code=404)` 발생 |
| TC-SESS-030 | api-results: 정상 저장 → 201, turn_id·metadata 반환 | 세션 있음 | 1) `POST /api/v1/sessions/{key}/api-results` 호출 (global_session_key, turn_id, agent 등)<br>2) `session_repo.add_turn` 호출 확인<br>3) 반환 객체의 `turn_id`, `metadata.sol_api` 확인 | `global_session_key`, `turn_id`, `agent`, `transactionPayload`, `transactionResult` | `201 Created`, `TurnResponse` 반환, `metadata.sol_api` 포함 |
| TC-SESS-031 | api-results: path와 body의 global_session_key 불일치 → 400 | 세션 있음 | 1) path=`/api/v1/sessions/gsess_key_a` 로 호출, body에 `global_session_key="gsess_key_b"` | path key ≠ body key | `HTTPException(status_code=400, detail="global_session_key mismatch")` 발생 |

---

## 테스트 커버리지 요약

| 서비스 | TC 수 | 주요 검증 항목 |
|---|---|---|
| LoggerExtraData | 10 | 기본값, 직렬화, FieldInfo 방어 |
| AuthService | 16 | 토큰 생성/검증/갱신, jti 매핑, TTL 연장, 토큰 기반 세션 종료 |
| ProfileService | 15 | 프로파일 병합, cusno 추출·세션 저장, Redis 저장 경로 |
| SessionService | 31 | 세션 생성/조회/상태변경/종료, 레퍼런스 파싱, api-results 저장 |
| **합계** | **72** | |

---

## 파일 위치

```
tests/
  unit/
    __init__.py
    test_logger_config_unit.py    # TC-LOG-001~010
    test_auth_service_unit.py     # TC-AUTH-001~015
    test_profile_service_unit.py  # TC-PROF-001~014
    test_session_service_unit.py  # TC-SESS-001~028
  conftest.py                     # 통합 테스트 fixture
  test_session_create.py          # 통합: 세션 생성
  test_session_jwt.py             # 통합: JWT 검증/갱신
  ...
```