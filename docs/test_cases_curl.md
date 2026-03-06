# Session Manager — curl 수동 테스트 가이드

`docs/test_cases.md` 의 TC / IT 케이스를 **curl 명령어 한 줄씩** 실행하는 가이드입니다.  
스크립트·Python 파일 없이 터미널에 직접 붙여넣어 사용할 수 있습니다.

---

## 온프렘 테스트 결과 → Excel 기록

온프렘에서 curl 테스트 후 결과를 `docs/test_cases_sm.xlsx` 에 기록할 수 있습니다.

| 시트 | 용도 |
|------|------|
| **TC-단위테스트** | TC-LOG, TC-AUTH, TC-PROF, TC-SESS (단위 테스트 케이스) |
| **IT-통합테스트** | IT-SESS, IT-AUTH, IT-PROF (curl 통합 테스트 케이스) |

**결과 컬럼**에 `PASS` / `FAIL` / `-`(미실행) 입력, **비고 컬럼**에 오류 메시지·환경 정보 등을 기록하세요.

> Excel 파일은 `python scripts/generate_test_cases_excel.py` 로 `docs/test_cases.md` 기준 재생성됩니다.  
> 결과/비고는 수동 입력이므로 재생성 시 덮어쓰지 않도록 백업하거나 별도 시트로 관리하세요.

---

## 공통 준비

```bash
# 서버 주소 (로컬 또는 K8s 포드)
BASE="http://localhost:5000"

# 아래 세 변수는 세션 생성 후 응답에서 직접 복사해서 사용
GSKEY="gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ACCESS="eyJhbGciOi..."
REFRESH="eyJhbGciOi..."
```

> **jq** 미설치 시 출력이 한 줄로 나옵니다. macOS: `brew install jq`

---

## 헬스체크

```bash
# 서버가 살아있는지 먼저 확인
curl -s "$BASE/health" | cat
```

**예상 응답**
```json
{"status": "healthy", "service": "session-manager", "version": "5.0.0", "storage": "redis"}
```

---

## TC-LOG — LoggerExtraData 직렬화 (TC-LOG-001 ~ 010)

> ℹ️ TC-LOG 는 **Pydantic 모델 내부 직렬화** 테스트입니다.  
> 별도 API 엔드포인트가 없으므로 curl 로 직접 호출할 수 없습니다.  
> 세션 생성/조회 등 다른 API 호출 시 **서버 로그(stdout)** 에 해당 필드가 출력되면 통과로 간주합니다.

| TC | 검증 방법 |
|----|---------|
| TC-LOG-001~005 | `POST /api/v1/sessions` 후 서버 로그에서 `-` 기본값 필드 확인 |
| TC-LOG-006~010 | `POST /api/v1/sessions/realtime-personal-context` 후 로그 확인 |

---

## TC-AUTH — 인증 서비스

### TC-AUTH-001 ~ 004 : create_tokens (세션 생성 시 토큰 발급)

> `POST /api/v1/sessions`  
> 내부적으로 `create_tokens(user_id, global_session_key)` 를 호출해 토큰을 발급합니다.

---

#### TC-AUTH-001 · access_token, refresh_token, jti 반환

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "700000001"}' | python3 -m json.tool
```

**예상 응답** `201 Created`
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### TC-AUTH-002 · jti UUID 형식 확인

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "700000002"}' \
  | python3 -c "
import sys, json, re
d = json.load(sys.stdin)
jti = d.get('jti','')
ok = bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', jti))
print('jti:', jti)
print('UUID 형식:', 'OK' if ok else 'FAIL')
"
```

**예상 출력**
```
jti: 550e8400-e29b-41d4-a716-446655440000
UUID 형식: OK
```

---

#### TC-AUTH-003 · jti → global_session_key Redis 매핑 저장 (간접 검증)

jti 발급 후 **verify API** 에서 세션 정보가 정상 반환되면 매핑이 저장된 것입니다.

```bash
# 1) 세션 생성
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "700000003"}'
# → access_token 복사 후 아래 ACCESS 변수에 대입

# 2) 토큰으로 세션 검증 (매핑 저장 여부 간접 확인)
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" | python3 -m json.tool
```

**예상 응답**
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "session_state": "start",
  "is_alive": true,
  "expires_at": "2026-03-01T01:00:00+00:00"
}
```

---

#### TC-AUTH-004 · userId 빈 문자열 허용

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

**예상 응답** `201 Created` — `access_token` 포함, 오류 없음
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "jti": "..."
}
```

---

### TC-AUTH-005 ~ 009 : verify_token_and_get_session

---

#### TC-AUTH-005 · 위조/만료 토큰 → 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer invalid.token.here"
```

**예상 출력**
```
401
```

---

#### TC-AUTH-006 · refresh 토큰으로 verify → 401

```bash
# 세션 생성 후 refresh_token 을 $REFRESH 에 저장한 뒤 실행
curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $REFRESH"
```

**예상 출력**
```
401
```

---

#### TC-AUTH-007 · 위조/잘못된 서명 토큰 → 401

> 잘못된 secret으로 서명된 JWT는 검증 시 401 반환

```bash
# python3 로 테스트용 토큰 생성 (HS256, sub=test, type=access, wrong secret)
FAKE=$(python3 -c "
import jwt, datetime, uuid
payload = {'sub': 'test', 'jti': str(uuid.uuid4()), 'type': 'access',
           'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
print(jwt.encode(payload, 'wrong_secret_key', algorithm='HS256'))
")
curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $FAKE"
```

**예상 출력**
```
401
```

---

#### TC-AUTH-008 · 세션 없음 → is_alive=false

```bash
# 세션이 만료/삭제된 상태의 유효한 access_token 필요
# (Redis 에서 직접 키를 삭제 후 verify 호출)
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" | python3 -m json.tool
```

세션 삭제 후 **예상 응답**
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "is_alive": false,
  "session_state": "",
  "expires_at": null
}
```

---

#### TC-AUTH-009 · 세션 있음 → is_alive=true

```bash
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" | python3 -m json.tool
```

**예상 응답**
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "session_state": "start",
  "is_alive": true,
  "expires_at": "2026-03-01T01:00:00+00:00"
}
```

---

### TC-AUTH-012 ~ 015 : refresh_token

---

#### TC-AUTH-012 · 위조 refresh 토큰 → 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v1/sessions/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "invalid.refresh.token"}'
```

**예상 출력**
```
401
```

---

#### TC-AUTH-013 · access 토큰으로 refresh 요청 → 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v1/sessions/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$ACCESS\"}"
```

**예상 출력**
```
401
```

---

#### TC-AUTH-014 · 정상 refresh → 새 토큰 반환

```bash
curl -s -X POST "$BASE/api/v1/sessions/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH\"}" | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "access_token": "eyJ...<새 access token>...",
  "refresh_token": "eyJ...<새 refresh token>...",
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "jti": "새로운 UUID"
}
```

---

#### TC-AUTH-015 · refresh 후 TTL 연장 확인 (간접)

```bash
# 1) refresh 전 verify 로 expires_at 기록
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('before:', d.get('expires_at'))"

# 2) refresh 실행 (새 토큰 취득)
curl -s -X POST "$BASE/api/v1/sessions/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH\"}"
# → 새 ACCESS 값으로 교체

# 3) refresh 후 verify 로 expires_at 비교
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('after:', d.get('expires_at'))"
```

**예상 출력**: `after` 의 expires_at 가 `before` 보다 미래 또는 갱신됨

---

## TC-PROF — 프로파일 서비스

### TC-PROF-001 ~ 007 : _merge_profiles (내부 정적 메서드)

> ℹ️ `_merge_profiles` 는 **서비스 내부 정적 메서드**입니다.  
> curl 로 직접 호출할 수 없으며, `GET /api/v1/sessions/{key}` 의  
> 응답 `batch_profile`, `realtime_profile` 필드를 통해 간접 검증합니다.  
> 실시간 프로파일 저장 후 세션 조회 시 `realtime_profile` 결과를 확인하세요.

| TC | 간접 검증 방법 |
|----|--------------|
| TC-PROF-001 | 프로파일 없는 세션 조회 → `batch_profile: null`, `realtime_profile: null` |
| TC-PROF-002~003 | realtime-personal-context 저장 후 세션 조회 → `realtime_profile` 에서 `user_id`, `segment` 확인 |
| TC-PROF-004 | realtime에 빈 값 포함 저장 후 조회 → `attributes` 에서 제외 확인 |
| TC-PROF-005 | batch만 있는 상태에서 조회 → `batch_profile` 확인 |
| TC-PROF-006 | realtime 저장 후 조회 → `realtime_profile.preferences.source: "realtime"` |
| TC-PROF-007 | cusnoN10 없이 저장 후 조회 → batch user_id fallback |

---

#### TC-PROF-001 (간접) · 프로파일 없는 세션 조회

```bash
# 세션 생성 (프로파일 미저장)
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": ""}' | python3 -m json.tool
# GSKEY 변수에 global_session_key 값 저장

curl -s "$BASE/api/v1/sessions/$GSKEY" | python3 -m json.tool
```

**예상 응답 (프로파일 부분)**
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "session_state": "start",
  "batch_profile": null,
  "realtime_profile": null
}
```

---

### TC-PROF-008 ~ 014 : update_realtime_personal_context

---

#### TC-PROF-008 · 세션 없음 → 404

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid_token_xxx" \
  -d '{"profile_data": {"someField": "val"}}'
```

**예상 출력**
```
401
```

> ⚠️ 토큰 검증이 먼저 수행되므로, 세션 부재 전에 401 이 반환됩니다.  
> 유효한 토큰 + 삭제된 세션으로 테스트할 경우 404 반환.

---

#### TC-PROF-009 · cusnoN10 최상위 → realtime 저장

```bash
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{
    "profile_data": {
      "cusnoN10": "11111111",
      "membGdS2": "VIP",
      "risk_grade": "3",
      "asset_total": "50000000"
    }
  }' | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "updated_at": "2026-03-01T00:00:00.000000+00:00"
}
```

---

#### TC-PROF-009b · cusnoN10 있으면 세션에 cusno 저장

```bash
# 1) realtime-personal-context 로 cusnoN10 포함 저장
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"profile_data": {"cusnoN10": "11111111", "membGdS2": "VIP"}}' \
  -o /dev/null -w "%{http_code}\n"

# 2) 세션 조회로 cusno 필드 확인 (session_repo.update 결과 반영)
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
cusno = d.get('cusno')
print('cusno:', cusno)
print('OK' if cusno == '11111111' else 'FAIL')
"
```

**예상 출력**
```
200
cusno: 11111111
OK
```

---

#### TC-PROF-010 · responseData 안의 cusnoN10

```bash
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{
    "profile_data": {
      "responseData": {
        "cusnoN10": "22222222",
        "membGdS2": "GOLD"
      }
    }
  }' | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "updated_at": "2026-03-01T00:00:00.000000+00:00"
}
```

---

#### TC-PROF-011 · cusnoN10 없음 → 세션 키 기준 저장

```bash
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{
    "profile_data": {
      "someField": "someValue"
    }
  }' | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "updated_at": "2026-03-01T00:00:00.000000+00:00"
}
```

---

#### TC-PROF-012 · profile_repo 배치 저장 (간접 검증)

```bash
# realtime 저장 → 이후 세션 조회로 배치+실시간 병합 확인
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{
    "profile_data": {
      "cusnoN10": "33333333",
      "membGdS2": "VIP",
      "risk_grade": "3"
    }
  }' | python3 -m json.tool

# 세션 조회로 realtime_profile.preferences.source 확인
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
rp = d.get('realtime_profile')
print('realtime_profile:', json.dumps(rp, indent=2, ensure_ascii=False) if rp else 'null')
"
```

---

#### TC-PROF-013 · profile_repo 없음 → 배치 저장 없음

```bash
# cusnoN10 없이 realtime 저장 → batch 저장 안 됨
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{
    "profile_data": {
      "someField": "test"
    }
  }' | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "updated_at": "2026-03-01T00:00:00.000000+00:00"
}
```

---

#### TC-PROF-014 · 응답 status == "success"

```bash
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{
    "profile_data": {
      "cusnoN10": "55555555"
    }
  }' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d.get('status')); print('updated_at:', d.get('updated_at'))"
```

**예상 출력**
```
status: success
updated_at: 2026-03-01T00:00:00.000000+00:00
```

---

## TC-SESS — 세션 서비스

### TC-SESS-001 ~ 009 : create_session

---

#### TC-SESS-001 · global_session_key, access_token, refresh_token, jti 반환

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "700000001"}' | python3 -m json.tool
```

**예상 응답** `201 Created`
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

#### TC-SESS-002 · channel 없음 → channel="utterance"

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_001"}' \
  | python3 -c "
import sys, json
d=json.load(sys.stdin)
print('global_session_key:', d.get('global_session_key'))
print('access_token 존재:', bool(d.get('access_token')))
"
# channel 은 응답에 포함되지 않음, 내부에 'utterance' 로 저장됨
# 세션 조회로 확인:
# curl -s "$BASE/api/v1/sessions/$GSKEY" | python3 -c "..."
```

이후 세션 조회로 channel 확인:

```bash
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
ch = d.get('channel')
print('channel:', ch)
"
```

**예상 출력**
```
channel: {"eventType": "", "eventChannel": "utterance"}
```

---

#### TC-SESS-003 · channel 있음 → eventChannel, eventType 설정

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user_002",
    "channel": {
      "eventType": "ICON_ENTRY",
      "eventChannel": "SOL"
    }
  }' | python3 -m json.tool
# GSKEY2 에 저장

curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('channel:', json.dumps(d.get('channel'), ensure_ascii=False))
"
```

**예상 출력**
```json
{"eventType": "ICON_ENTRY", "eventChannel": "SOL"}
```

---

#### TC-SESS-004 · userId 없음 → user_id=''

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
```

**예상 응답** `201 Created` — global_session_key 포함, 오류 없음

---

#### TC-SESS-005 · triggerId 없음 → trigger_id=''

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_003"}' | python3 -m json.tool
```

**예상 응답** `201 Created`

---

#### TC-SESS-006 · triggerId 전달

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_004", "triggerId": "TRG-001"}' | python3 -m json.tool
```

**예상 응답** `201 Created`

---

#### TC-SESS-007 · session_state='start' 확인

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_005"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
gskey = d['global_session_key']
print('GSKEY:', gskey)
" 
# 위에서 얻은 GSKEY로 조회
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('session_state:', d.get('session_state'))"
```

**예상 출력**
```
session_state: start
```

---

#### TC-SESS-008 · auth_service.create_tokens 호출 확인

```bash
# 세션 생성 응답에 access_token 이 있으면 create_tokens 가 호출된 것
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_006"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('access_token 존재:', 'access_token' in d and bool(d['access_token']))
print('jti 존재:', 'jti' in d and bool(d['jti']))
"
```

**예상 출력**
```
access_token 존재: True
jti 존재: True
```

---

#### TC-SESS-009 · SESSION_CREATE ES 로그 payload (FieldInfo 없음)

```bash
# 세션 생성 시 서버 내부에서 LoggerExtraData 직렬화가 발생
# → 서버 에러 없이 201 이 반환되면 FieldInfo 없이 정상 직렬화된 것
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_007", "triggerId": "TRG-007", "channel": {"eventType": "ICON_ENTRY", "eventChannel": "SOL"}}'
```

**예상 출력**
```
201
```

---

### TC-SESS-010 ~ 015 : resolve_session

---

#### TC-SESS-010 · 세션 없음 → 404

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/api/v1/sessions/gsess_nonexistent_key_12345"
```

**예상 출력**
```
404
```

---

#### TC-SESS-011 · 세션 있음 → SessionResolveResponse 반환

```bash
curl -s "$BASE/api/v1/sessions/$GSKEY" | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "session_state": "start",
  "is_first_call": true,
  "channel": null,
  "task_queue_status": null,
  "subagent_status": "undefined",
  "batch_profile": null,
  "realtime_profile": null,
  "conversation_history": null,
  "turn_count": null
}
```

---

#### TC-SESS-012 · cusno 있으면 배치+실시간 프로파일 조회

```bash
# 1) realtime-personal-context 로 cusnoN10 포함 저장
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"profile_data": {"cusnoN10": "12345678", "membGdS2": "VIP"}}'

# 2) 세션 조회 → realtime_profile 에 프로파일 포함 확인
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
rp = d.get('realtime_profile')
if rp:
  print('user_id:', rp.get('user_id'))
  print('segment:', rp.get('segment'))
  print('source:', rp.get('preferences',{}).get('source'))
else:
  print('realtime_profile: null')
"
```

**예상 출력**
```
user_id: 12345678
segment: VIP
source: realtime
```

---

#### TC-SESS-013 · cusno 없음 → 세션 키 기준 실시간 프로파일 조회

```bash
# 1) cusnoN10 없이 realtime 저장
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"profile_data": {"someField": "testValue"}}'

# 2) 세션 조회
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
rp = d.get('realtime_profile')
print('realtime_profile:', 'exists' if rp else 'null')
"
```

---

#### TC-SESS-014 · conversation_history 가 list 아니면 400 (저장 안 됨)

> ℹ️ PATCH 시점에 검증되어 400 반환, 잘못된 데이터는 저장되지 않습니다.  
> (resolve 단계에서 기존 Redis에 잘못된 데이터가 있을 때 null 반환하는 방어 로직은 별도 Redis 설정 필요)

```bash
# PATCH 로 reference_information 에 문자열 conversation_history 전송 → 400
curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"state_patch\": {
      \"reference_information\": {
        \"conversation_history\": \"invalid_string\"
      }
    }
  }"
```

**예상 출력**
```
400
```

---

#### TC-SESS-015 · turn_count 가 int 아니면 400 (저장 안 됨)

```bash
# PATCH 로 turn_count 에 문자열 전송 → 400
curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"state_patch\": {
      \"reference_information\": {
        \"turn_count\": \"not_int\"
      }
    }
  }"
```

**예상 출력**
```
400
```

---

### TC-SESS-016 ~ 021 : patch_session_state

---

#### TC-SESS-016 · 세션 없음 → 404

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH "$BASE/api/v1/sessions/gsess_nonexistent_key/state" \
  -H "Content-Type: application/json" \
  -d '{"global_session_key": "gsess_nonexistent_key", "session_state": "talk"}'
```

**예상 출력**
```
404
```

---

#### TC-SESS-017 · session_state=talk → TTL 연장 (refresh_ttl 간접 확인)

```bash
# 1) 세션 생성
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "user_talk"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['global_session_key'])"
# → GSKEY 에 저장

# 2) talk 상태로 PATCH
curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"session_state\": \"talk\"
  }" | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "updated_at": "2026-03-01T00:00:00.000000+00:00"
}
```

---

#### TC-SESS-018 · session_state=end → refresh_ttl 미호출

```bash
curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"session_state\": \"end\"
  }" | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "updated_at": "2026-03-01T00:00:00.000000+00:00"
}
```

---

#### TC-SESS-019 · turn_id 누적 저장

```bash
# 세션 생성 후 turn_id 포함 PATCH
curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"turn_id\": \"turn_001\"
  }"

curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"turn_id\": \"turn_002\"
  }"

# 세션 조회로 turn_ids 확인 (full 엔드포인트의 session.turn_ids)
curl -s "$BASE/api/v1/sessions/$GSKEY/full" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
turn_ids = d.get('session', {}).get('turn_ids') or []
print('turn_ids:', turn_ids)
"
```

---

#### TC-SESS-020 · 동일 turn_id 중복 추가 안 됨

```bash
# 같은 turn_id 두 번 PATCH
for i in 1 2; do
  curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
    -H "Content-Type: application/json" \
    -d "{\"global_session_key\": \"$GSKEY\", \"turn_id\": \"turn_dup\"}"
done

# 세션 full 조회로 session.turn_ids에서 중복 없는지 확인
curl -s "$BASE/api/v1/sessions/$GSKEY/full" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
turn_ids = d.get('session', {}).get('turn_ids') or []
dup_count = turn_ids.count('turn_dup')
print('turn_dup 횟수:', dup_count)
"
```

**예상 출력**
```
turn_dup 횟수: 1
```

---

#### TC-SESS-021 · conversation_history 가 list 아님 → 400

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"state_patch\": {
      \"reference_information\": {
        \"conversation_history\": \"not_a_list\"
      }
    }
  }"
```

**예상 출력**
```
400
```

---

### TC-SESS-022 ~ 025 : close_session

---

#### TC-SESS-022 · 세션 없음 → 404

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE "$BASE/api/v1/sessions/gsess_nonexistent_key?close_reason=test"
```

**예상 출력**
```
404
```

---

#### TC-SESS-023 · 정상 종료 → session_state='end'

```bash
curl -s -X DELETE "$BASE/api/v1/sessions/$GSKEY?close_reason=user_request" \
  | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "closed_at": "2026-03-01T00:00:00.000000+00:00",
  "archived_conversation_id": "arch_gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "cleaned_local_sessions": 0
}
```

---

#### TC-SESS-024 · archived_id 형식 확인

```bash
curl -s -X DELETE "$BASE/api/v1/sessions/$GSKEY?close_reason=done" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
arch_id = d.get('archived_conversation_id', '')
print('archived_conversation_id:', arch_id)
print('형식 OK:', arch_id.startswith('arch_'))
"
```

**예상 출력**
```
archived_conversation_id: arch_gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
형식 OK: True
```

---

#### TC-SESS-025 · final_summary 포함 종료

```bash
curl -s -X DELETE "$BASE/api/v1/sessions/$GSKEY?close_reason=done" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool
```

> ⚠️ `final_summary` 는 DELETE body 로 전달하기 어려우므로, 토큰 기반 종료 API 사용 권장:

```bash
curl -s -X DELETE "$BASE/api/v1/sessions" \
  -H "Authorization: Bearer $ACCESS" \
  -G --data-urlencode "close_reason=done" \
  | python3 -m json.tool
```

---

### TC-AUTH-016 ~ 018 : close_session_by_token (토큰 기반 세션 종료)

> `DELETE /api/v1/sessions` — 경로 변수 없음. Authorization: Bearer \<access_token\> 필수.

---

#### TC-AUTH-016 · 토큰 없음 → 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE "$BASE/api/v1/sessions?close_reason=test"
```

**예상 출력**
```
401
```

---

#### TC-AUTH-017 · 위조 토큰 → 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X DELETE "$BASE/api/v1/sessions?close_reason=test" \
  -H "Authorization: Bearer invalid.token.here"
```

**예상 출력**
```
401
```

---

#### TC-AUTH-018 · 정상 종료 → status, closed_at, jti 무효화

```bash
# 1) 세션 생성 후 access_token 저장
RESP=$(curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"0616001905","channel":{"eventType":"ICON_ENTRY","eventChannel":"web"}}')
ACCESS=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# 2) 토큰 기반 세션 종료
curl -s -X DELETE "$BASE/api/v1/sessions?close_reason=user_logout" \
  -H "Authorization: Bearer $ACCESS" | python3 -m json.tool
```

**예상 응답** `200 OK`
```json
{
  "status": "success",
  "closed_at": "2026-03-01T00:00:00.000000+00:00",
  "archived_conversation_id": "arch_gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "cleaned_local_sessions": 0
}
```

**jti 무효화 확인**: 종료 후 동일 access_token으로 verify 호출 시 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS"
# 예상: 401
```

---

### TC-SESS-026 ~ 028 : _serialize_reference_information (내부 정적 메서드)

> ℹ️ `_serialize_reference_information` 은 **서비스 내부 정적 메서드**입니다.  
> `PATCH /api/v1/sessions/{key}/state` 의 `state_patch.reference_information` 을 통해 간접 검증합니다.

---

#### TC-SESS-026 (간접) · 빈 reference_information

```bash
curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"state_patch\": {
      \"reference_information\": {}
    }
  }" | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d.get('status'))"
```

**예상 출력**
```
status: success
```

---

#### TC-SESS-027 (간접) · JSON 키 정렬 확인

```bash
curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"state_patch\": {
      \"reference_information\": {
        \"z_key\": 1,
        \"a_key\": 2
      }
    }
  }"

# 세션 조회로 저장된 reference_information 확인
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
# reference_information 은 응답에서 turn_count/conversation_history 로 파싱됨
print(json.dumps(d, indent=2, ensure_ascii=False))
"
```

---

#### TC-SESS-028 (간접) · conversation_history 순서 유지

```bash
curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"state_patch\": {
      \"reference_information\": {
        \"conversation_history\": [
          {\"msg\": \"first\"},
          {\"msg\": \"second\"}
        ]
      }
    }
  }"

curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
ch = d.get('conversation_history')
if ch:
  print('첫 번째:', ch[0])
  print('두 번째:', ch[1])
else:
  print('conversation_history: null')
"
```

**예상 출력**
```
첫 번째: {'msg': 'first'}
두 번째: {'msg': 'second'}
```

---

### TC-SESS-029 ~ 031 : save_api_result (실시간 API 연동 결과 저장)

> `POST /api/v1/sessions/{global_session_key}/api-results` — DBS 등 외부 실시간 API 호출 결과를 턴 메타데이터로 저장

---

#### TC-SESS-029 · 세션 없음 → 404

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v1/sessions/gsess_nonexistent_12345/api-results" \
  -H "Content-Type: application/json" \
  -d '{"global_session_key":"gsess_nonexistent_12345","turn_id":"turn_001"}'
```

**예상 출력**
```
404
```

---

#### TC-SESS-030 · 정상 저장 → 201, turn_id·metadata.sol_api 반환

```bash
# 최소 필드 (global_session_key, turn_id 필수)
curl -s -X POST "$BASE/api/v1/sessions/$GSKEY/api-results" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"turn_id\": \"turn_sol_001\"
  }" | python3 -m json.tool

# 전체 필드 (SOL 스펙)
curl -s -X POST "$BASE/api/v1/sessions/$GSKEY/api-results" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"$GSKEY\",
    \"turn_id\": \"turn_sol_002\",
    \"agent\": \"dbs_caller\",
    \"transactionPayload\": [
      {\"trxCd\": \"TRX001\", \"dataBody\": {\"foo\": \"bar\"}}
    ],
    \"globId\": \"GLOB123\",
    \"requestId\": \"REQ123\",
    \"result\": \"SUCCESS\",
    \"resultCode\": \"0000\",
    \"resultMsg\": \"OK\",
    \"transactionResult\": [
      {\"trxCd\": \"TRX001\", \"responseData\": {\"balance\": 100000}}
    ]
  }" | python3 -m json.tool
```

**예상 응답** `201 Created`
```json
{
  "turn_id": "turn_sol_002",
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "timestamp": "2026-03-01T00:00:00.000000+00:00",
  "metadata": {
    "sol_api": {
      "global_session_key": "gsess_...",
      "turn_id": "turn_sol_002",
      "agent": "dbs_caller",
      "request": {...},
      "response": {...}
    }
  }
}
```

**저장 확인**: `GET /api/v1/sessions/$GSKEY/full` 로 turns 목록 조회

```bash
curl -s "$BASE/api/v1/sessions/$GSKEY/full" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
turns = d.get('turns', [])
print('total_turns:', d.get('total_turns'))
for t in turns:
  print('  turn_id:', t.get('turn_id'))
"
```

---

#### TC-SESS-031 · path와 body의 global_session_key 불일치 → 400

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v1/sessions/$GSKEY/api-results" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"gsess_wrong_key_12345\",
    \"turn_id\": \"turn_001\"
  }"
```

**예상 출력**
```
400
```

---

## IT — 통합 테스트 (실제 Redis 필요)

> 통합 테스트는 **실제 Redis Sentinel** 에 연결된 환경에서 수행합니다.  
> 각 테스트 후 Redis 키(`inttest_*`, `jti:*`)는 수동으로 정리하세요.

---

## IT-SESS — 세션 서비스 통합 테스트 (IT-SESS-001 ~ 008)

---

#### IT-SESS-001 · 세션 생성 후 Redis 저장 확인

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "IT700000001"}' | python3 -m json.tool
```

**예상 응답** `201 Created` — `global_session_key` 포함

---

#### IT-SESS-002 · TTL > 0 확인

```bash
# 세션 생성 후 verify 에서 expires_at 이 미래 시각이면 TTL > 0
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('expires_at:', d.get('expires_at'))
print('TTL 설정됨:', d.get('expires_at') is not None)
"
```

**예상 출력**
```
expires_at: 2026-03-01T01:00:00+00:00
TTL 설정됨: True
```

---

#### IT-SESS-003 · 생성된 세션 조회

```bash
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('global_session_key:', d.get('global_session_key'))
print('session_state:', d.get('session_state'))
"
```

**예상 출력**
```
global_session_key: gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
session_state: start
```

---

#### IT-SESS-004 · 없는 세션 조회 → 404

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/api/v1/sessions/gsess_it_nonexist_12345"
```

**예상 출력**
```
404
```

---

#### IT-SESS-005 · patch 후 turn_id 저장 확인

```bash
curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
  -H "Content-Type: application/json" \
  -d "{\"global_session_key\": \"$GSKEY\", \"turn_id\": \"it_turn_001\"}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d.get('status'))"
```

**예상 출력**
```
status: success
```

---

#### IT-SESS-006 · 동일 turn_id 두 번 → 중복 없음

```bash
for i in 1 2; do
  curl -s -X PATCH "$BASE/api/v1/sessions/$GSKEY/state" \
    -H "Content-Type: application/json" \
    -d "{\"global_session_key\": \"$GSKEY\", \"turn_id\": \"it_turn_dup\"}" \
    -o /dev/null -w "PATCH $i: %{http_code}\n"
done

curl -s "$BASE/api/v1/sessions/$GSKEY/full" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
turn_ids = d.get('session', {}).get('turn_ids') or []
dup_count = turn_ids.count('it_turn_dup')
print('it_turn_dup 횟수:', dup_count)
"
```

**예상 출력**
```
PATCH 1: 200
PATCH 2: 200
it_turn_dup 횟수: 1
```

---

#### IT-SESS-007 · 세션 종료 후 status, closed_at, archived_conversation_id

```bash
curl -s -X DELETE "$BASE/api/v1/sessions/$GSKEY?close_reason=USER_LOGOUT" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('status:', d.get('status'))
print('closed_at:', d.get('closed_at'))
print('archived_conversation_id:', d.get('archived_conversation_id'))
print('cleaned_local_sessions:', d.get('cleaned_local_sessions'))
"
```

**예상 출력**
```
status: success
closed_at: 2026-03-01T00:00:00.000000+00:00
archived_conversation_id: arch_gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
cleaned_local_sessions: 0
```

---

#### IT-SESS-008 · archived_conversation_id 에 세션 키 포함

```bash
curl -s -X DELETE "$BASE/api/v1/sessions/$GSKEY?close_reason=done" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
arch_id = d.get('archived_conversation_id', '')
print('archived_conversation_id:', arch_id)
"
```

**예상 출력**
```
archived_conversation_id: arch_gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## IT-AUTH — 인증 서비스 통합 테스트 (IT-AUTH-001 ~ 007)

---

#### IT-AUTH-001 · 토큰 생성 후 jti Redis 저장

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "IT_user_001"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('jti:', d.get('jti'))
print('access_token 길이:', len(d.get('access_token', '')))
"
```

**예상 출력**
```
jti: 550e8400-e29b-41d4-a716-446655440000
access_token 길이: 200 이상
```

---

#### IT-AUTH-002 · 발급된 access token 검증

```bash
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" | python3 -m json.tool
```

**예상 응답**
```json
{
  "global_session_key": "gsess_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "session_state": "start",
  "is_alive": true,
  "expires_at": "2026-03-01T01:00:00+00:00"
}
```

---

#### IT-AUTH-003 · Refresh 후 jti 갱신

```bash
# 1) 현재 jti 기록
OLD_JTI=$(curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "IT_user_003"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['jti'])")
echo "OLD JTI: $OLD_JTI"

# 2) refresh 실행
curl -s -X POST "$BASE/api/v1/sessions/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH\"}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('NEW JTI:', d.get('jti'))
"
```

**예상 출력**
```
OLD JTI: 550e8400-e29b-41d4-a716-446655440000
NEW JTI: 6ba7b810-9dad-11d1-80b4-00c04fd430c8  ← 다른 UUID
```

---

#### IT-AUTH-004 · 위조 토큰 → 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer not.a.real.token"
```

**예상 출력**
```
401
```

---

#### IT-AUTH-005 · access 토큰으로 refresh → 401

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/api/v1/sessions/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$ACCESS\"}"
```

**예상 출력**
```
401
```

---

#### IT-AUTH-006 · jti TTL > 0 (verify expires_at 로 간접 확인)

```bash
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" \
  | python3 -c "
import sys, json
from datetime import datetime
d = json.load(sys.stdin)
exp = d.get('expires_at')
print('expires_at:', exp)
print('TTL > 0:', exp is not None)
"
```

**예상 출력**
```
expires_at: 2026-03-01T01:00:00+00:00
TTL > 0: True
```

---

#### IT-AUTH-007 · jti UUID 형식

```bash
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": "IT_user_007"}' \
  | python3 -c "
import sys, json, re
d = json.load(sys.stdin)
jti = d.get('jti', '')
ok = bool(re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', jti))
print('jti:', jti)
print('UUID 형식 OK:', ok)
"
```

**예상 출력**
```
jti: 550e8400-e29b-41d4-a716-446655440000
UUID 형식 OK: True
```

---

## IT-PROF — 프로파일 서비스 통합 테스트 (IT-PROF-001 ~ 006)

---

#### IT-PROF-001 · 실시간 프로파일 저장 후 세션 조회로 확인

```bash
# 1) realtime 저장
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"profile_data": {"cusnoN10": "99000001", "risk_grade": "3", "asset_total": "5000000"}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d.get('status'))"

# 2) 세션 조회로 realtime_profile 확인
curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
rp = d.get('realtime_profile')
if rp:
  print('risk_grade:', rp.get('risk_grade'))
  print('user_id:', rp.get('cusnoN10'))
else:
  print('realtime_profile: null')
"
```

**예상 출력**
```
status: success
risk_grade: 3
user_id: 99000001
```

---

#### IT-PROF-002 · realtime TTL > 0 (expires_at 로 간접 확인)

```bash
curl -s "$BASE/api/v1/sessions/verify" \
  -H "Authorization: Bearer $ACCESS" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('expires_at:', d.get('expires_at'))
"
```

---

#### IT-PROF-003 · 실시간 + 배치 병합

```bash
# 실시간 저장 후 세션 조회 → realtime_profile 에 저장 결과 확인
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"profile_data": {"cusnoN10": "99000003", "risk_grade": "4"}}' \
  -o /dev/null -w "%{http_code}\n"

curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
rp = d.get('realtime_profile')
print('realtime_profile 존재:', rp is not None)
if rp:
  print('risk_grade:', rp.get('risk_grade'))
"
```

---

#### IT-PROF-004 · 실시간 프로파일이 배치보다 우선

```bash
# 실시간에 risk_grade 저장 → 배치에 다른 값이 있어도 실시간 우선
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"profile_data": {"cusnoN10": "99000004", "risk_grade": "RT_GRADE"}}' \
  -o /dev/null

curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
rp = d.get('realtime_profile')
if rp:
  print('risk_grade (실시간 우선):', rp.get('risk_grade'))
  print('cusnoN10:', rp.get('cusnoN10'))
"
```

**예상 출력**
```
risk_grade (실시간 우선): RT_GRADE
cusnoN10: 99000004
```

---

#### IT-PROF-005 · 없는 cusno → 프로파일 없음

```bash
# 프로파일 미저장 세션 생성 후 조회
curl -s -X POST "$BASE/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{"userId": ""}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['global_session_key'])"
# → 새 GSKEY_EMPTY

curl -s "$BASE/api/v1/sessions/$GSKEY_EMPTY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('batch_profile:', d.get('batch_profile'))
print('realtime_profile:', d.get('realtime_profile'))
"
```

**예상 출력**
```
batch_profile: None
realtime_profile: None
```

---

#### IT-PROF-006 · 실시간 우선 검증 (get_batch_and_realtime_profiles)

```bash
# cusnoN10 포함 저장 → 조회 시 realtime source 확인
curl -s -X POST "$BASE/api/v1/sessions/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS" \
  -d '{"profile_data": {"cusnoN10": "99000006", "risk_grade": "RT"}}' \
  -o /dev/null

curl -s "$BASE/api/v1/sessions/$GSKEY" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
rp = d.get('realtime_profile')
if rp:
  print('cusnoN10:', rp.get('cusnoN10'))
  print('risk_grade:', rp.get('risk_grade'))
else:
  print('realtime_profile: null')
"
```

**예상 출력**
```
cusnoN10: 99000006
risk_grade: RT
```

---

## 공통 오류 코드 정리

| HTTP 코드 | 의미 | 주요 발생 케이스 |
|-----------|------|----------------|
| `201` | 세션 생성 성공 | `POST /api/v1/sessions` |
| `200` | 조회/업데이트 성공 | GET, PATCH, DELETE, realtime-personal-context |
| `400` | 잘못된 요청 | conversation_history 타입 오류, key mismatch |
| `401` | 인증 실패 | 위조/만료/타입오류 토큰, 토큰 없음 |
| `404` | 세션 없음 | 존재하지 않는 global_session_key |
| `422` | Validation 실패 | Pydantic 스키마 오류 |
| `500` | 서버 내부 오류 | Redis 연결 실패 등 |

---

## 순서 권장 (처음 테스트 시)

```
1. 헬스체크
2. TC-SESS-001  (POST → GSKEY, ACCESS, REFRESH 취득)
3. TC-AUTH-009  (GET /verify → is_alive 확인)
4. TC-SESS-011  (GET /{key})
5. TC-PROF-009  (POST /realtime-personal-context)
6. TC-SESS-012  (GET /{key} → batch_profile, realtime_profile 확인)
7. TC-SESS-017  (PATCH /state → talk)
8. TC-AUTH-014  (POST /refresh → 새 토큰 취득)
9. TC-SESS-023  (DELETE /{key} → global_session_key 기반)
10. TC-AUTH-018 (DELETE /sessions → 토큰 기반 세션 종료)
11. TC-SESS-030 (POST /{key}/api-results → 실시간 API 결과 저장)
12. TC-AUTH-012 (위조 refresh → 401)
```

---

## TC/IT ID → curl 섹션 매핑 (Excel 결과 기록용)

| TC/IT ID | curl 가이드 섹션 | 비고 |
|----------|------------------|------|
| TC-LOG-001~010 | TC-LOG (로그는 API 간접 검증) | 서버 로그 확인 |
| TC-AUTH-001~004 | TC-AUTH-001 ~ 004 | create_tokens |
| TC-AUTH-005~009 | TC-AUTH-005 ~ 009 | verify_token |
| TC-AUTH-012~015 | TC-AUTH-012 ~ 015 | refresh_token |
| TC-AUTH-016~018 | TC-AUTH-016 ~ 018 | close_session_by_token (토큰 기반 세션 종료) |
| TC-PROF-001~007 | TC-PROF-001 (간접), 002~007 | _merge_profiles 간접 검증 |
| TC-PROF-008~014, 009b | TC-PROF-008 ~ 014, 009b | update_realtime_personal_context (009b: 세션 cusno 저장) |
| TC-SESS-001~009 | TC-SESS-001 ~ 009 | create_session |
| TC-SESS-010~015 | TC-SESS-010 ~ 015 | resolve_session |
| TC-SESS-016~021 | TC-SESS-016 ~ 021 | patch_session_state |
| TC-SESS-022~025 | TC-SESS-022 ~ 025 | close_session |
| TC-SESS-026~028 | TC-SESS-026 ~ 028 | _serialize_reference_information (간접) |
| TC-SESS-029~031 | TC-SESS-029 ~ 031 | save_api_result (api-results) |
| IT-SESS-001~008 | IT-SESS-001 ~ 008 | 세션 통합 테스트 |
| IT-AUTH-001~007 | IT-AUTH-001 ~ 007 | 인증 통합 테스트 |
| IT-PROF-001~006 | IT-PROF-001 ~ 006 | 프로파일 통합 테스트 |
