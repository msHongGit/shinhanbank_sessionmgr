# Redis 조회 및 간단한 API 테스트 가이드

> Session Manager의 Redis 데이터 조회 및 핵심 API 테스트 명령어 모음

---

## 1. Redis CLI 조회 명령어

### 1.1 Redis 연결

#### 로컬 Docker 컨테이너 Redis 접근

```bash
# 방법 1: 컨테이너 내부에서 직접 redis-cli 실행 (권장)
docker exec -it <redis_container_name> redis-cli

# 예시: 컨테이너 이름이 "redis"인 경우
docker exec -it redis redis-cli

# 비밀번호가 있는 경우
docker exec -it redis redis-cli -a "YOUR_PASSWORD"

# 방법 2: 컨테이너 내부 쉘 접근 후 redis-cli 실행
docker exec -it <redis_container_name> sh
# 쉘 내부에서
redis-cli

# 방법 3: 호스트에서 포트 매핑을 통해 접근 (컨테이너가 포트를 노출한 경우)
# 예: docker run -p 6379:6379 redis
redis-cli -h localhost -p 6379

# 비밀번호가 있는 경우
redis-cli -h localhost -p 6379 -a "YOUR_PASSWORD"
```

#### Azure Redis 연결 (프로덕션)

```bash
# Azure Redis 연결 (예시)
redis-cli -h redis-shinhan-sol-test.koreacentral.redis.azure.net \
  -p 10000 \
  --tls \
  -a "YOUR_REDIS_PASSWORD"

# 또는 환경변수 사용
export REDISCLI_AUTH="YOUR_REDIS_PASSWORD"
redis-cli -h redis-shinhan-sol-test.koreacentral.redis.azure.net -p 10000 --tls
```

```

### 1.2 세션 조회

#### 모든 세션 키 조회
```bash
# 패턴으로 모든 세션 키 찾기
KEYS session:*

# 특정 세션 조회 (Hash 타입)
HGETALL session:gsess_20260107120000_abc123
```

#### 세션 특정 필드 조회
```bash
# 세션 상태 조회
HGET session:gsess_20260107120000_abc123 session_state

# 사용자 ID 조회
HGET session:gsess_20260107120000_abc123 user_id

# 고객번호 조회 (실시간 프로파일 저장 후)
HGET session:gsess_20260107120000_abc123 cusno

# 세션 생성 시각 조회
HGET session:gsess_20260107120000_abc123 created_at

# 세션 TTL 확인
TTL session:gsess_20260107120000_abc123
```

### 1.3 턴(Turn) 목록 조회

```bash
# 특정 세션의 모든 턴 조회 (List 타입)
LRANGE turns:gsess_20260107120000_abc123 0 -1

# 턴 개수 확인
LLEN turns:gsess_20260107120000_abc123

# 특정 인덱스의 턴 조회
LINDEX turns:gsess_20260107120000_abc123 0
```

### 1.4 JWT 토큰 매핑 조회

```bash
# JTI로 global_session_key 조회 (String 타입)
GET jti:550e8400-e29b-41d4-a716-446655440000

# 모든 JTI 매핑 키 조회
KEYS jti:*

# JTI 매핑 TTL 확인
TTL jti:550e8400-e29b-41d4-a716-446655440000
```

### 1.5 프로파일 조회

#### 실시간 프로파일 조회
```bash
# 실시간 프로파일 조회 (String 타입, JSON)
GET profile:realtime:0616001905

# JSON 포맷팅하여 조회 (jq 사용)
GET profile:realtime:0616001905 | python3 -m json.tool
```

#### 배치 프로파일 조회
```bash
# 배치 프로파일 조회 (String 타입, JSON)
GET profile:batch:0616001905

# JSON 포맷팅하여 조회
GET profile:batch:0616001905 | python3 -m json.tool
```

### 1.6 유용한 조회 명령어 모음

```bash
# 1. 특정 세션의 모든 정보 조회
HGETALL session:gsess_20260107120000_abc123

# 2. 세션의 턴 목록과 함께 조회
HGETALL session:gsess_20260107120000_abc123
LRANGE turns:gsess_20260107120000_abc123 0 -1

# 3. 고객번호로 프로파일 조회 (세션에서 cusno 추출 후)
# 먼저 세션에서 cusno 확인
HGET session:gsess_20260107120000_abc123 cusno
# 그 다음 프로파일 조회
GET profile:realtime:0616001905
GET profile:batch:0616001905

# 4. 모든 활성 세션 개수 확인
DBSIZE
KEYS session:* | wc -l

# 5. 세션 만료 시간 확인
TTL session:gsess_20260107120000_abc123
# -1: TTL 없음 (만료 안 됨)
# -2: 키가 존재하지 않음
# 양수: 남은 초 단위 시간
```

---

## 2. 간단한 API 테스트 (curl)

### 2.1 환경 설정

```bash
# Base URL 설정
export BASE_URL="http://sol-session-manager.crewai-axd.com"
# 또는 로컬 테스트
# export BASE_URL="http://localhost:5000"
```

### 2.2 핵심 API 테스트

#### 1. Health Check
```bash
curl -sS "${BASE_URL}/"
```

#### 2. 세션 생성 (JWT 토큰 발급)
```bash
RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "0616001905",
    "channel": {
      "eventType": "ICON_ENTRY",
      "eventChannel": "web"
    }
  }')

# 응답에서 필요한 값 추출
GLOBAL_SESSION_KEY=$(echo $RESPONSE | python3 -c 'import sys, json; print(json.load(sys.stdin)["global_session_key"])')
ACCESS_TOKEN=$(echo $RESPONSE | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')
REFRESH_TOKEN=$(echo $RESPONSE | python3 -c 'import sys, json; print(json.load(sys.stdin)["refresh_token"])')

echo "Session Key: $GLOBAL_SESSION_KEY"
echo "Access Token: ${ACCESS_TOKEN:0:50}..."
```

#### 3. 세션 조회
```bash
curl -sS "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}" | python3 -m json.tool
```

#### 4. 세션 상태 업데이트
```bash
curl -sS -X PATCH "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/state" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"${GLOBAL_SESSION_KEY}\",
    \"turn_id\": \"turn-001\",
    \"session_state\": \"talk\",
    \"state_patch\": {
      \"subagent_status\": \"continue\",
      \"action_owner\": \"ma\"
    }
  }" | python3 -m json.tool
```

#### 5. 세션 Ping (토큰 기반)
```bash
curl -sS -X GET "${BASE_URL}/api/v1/sessions/ping" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | python3 -m json.tool
```

#### 6. 토큰 검증 및 세션 정보 조회
```bash
curl -sS -X GET "${BASE_URL}/api/v1/sessions/verify" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" | python3 -m json.tool
```

#### 7. 토큰 갱신 (Refresh Token Rotation)
```bash
RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/sessions/refresh" \
  -H "Authorization: Bearer ${REFRESH_TOKEN}" \
  -H "Content-Type: application/json")

# 새 토큰으로 업데이트
ACCESS_TOKEN=$(echo $RESPONSE | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')
REFRESH_TOKEN=$(echo $RESPONSE | python3 -c 'import sys, json; print(json.load(sys.stdin)["refresh_token"])')

echo "New tokens received"
```

#### 8. 실시간 프로파일 업데이트
```bash
curl -sS -X POST "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/realtime-personal-context" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"${GLOBAL_SESSION_KEY}\",
    \"profile_data\": {
      \"cusnoN10\": \"0616001905\",
      \"cusSungNmS20\": \"홍길동\",
      \"hpNoS12\": \"01031286270\",
      \"biryrMmddS6\": \"710115\",
      \"onlyAgeN3\": 55,
      \"membGdS2\": \"02\",
      \"loginDt\": \"2026.01.21\",
      \"loginTimesS6\": \"14:23:59\",
      \"ygSexS1\": \"2\",
      \"cusSangtaeS2\": \"OK\"
    }
  }" | python3 -m json.tool
```

#### 9. SOL API 결과 저장
```bash
curl -sS -X POST "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/api-results" \
  -H "Content-Type: application/json" \
  -d "{
    \"global_session_key\": \"${GLOBAL_SESSION_KEY}\",
    \"turn_id\": \"turn-001\",
    \"agent\": \"dbs_caller\",
    \"transactionPayload\": [
      {
        \"trxCd\": \"TRX001\",
        \"dataBody\": {\"from\": \"KRW\", \"to\": \"USD\"}
      }
    ],
    \"globId\": \"glob-001\",
    \"requestId\": \"req-001\",
    \"result\": \"SUCCESS\",
    \"resultCode\": \"0000\",
    \"resultMsg\": \"OK\",
    \"transactionResult\": [
      {
        \"trxCd\": \"TRX001\",
        \"responseData\": {\"rate\": 1320.5, \"timestamp\": \"2026-01-07T10:30:00Z\"}
      }
    ]
  }" | python3 -m json.tool
```

#### 10. 세션 전체 정보 조회 (세션 + 턴 목록)
```bash
curl -sS "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/full" | python3 -m json.tool
```

#### 11. 세션 종료
```bash
curl -sS -X DELETE "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}?close_reason=test-completed" | python3 -m json.tool
```