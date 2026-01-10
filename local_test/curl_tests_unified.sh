#!/usr/bin/env bash
set -euo pipefail

# Session Manager 통합 API 테스트 스크립트
# 새로운 /api/v1/sessions 엔드포인트 사용


BASE_URL="${BASE_URL:-http://sol-session-manager.crewai-axd.com}"
AGW_API_KEY="${AGW_API_KEY:-changeme-agw}"
MA_API_KEY="${MA_API_KEY:-changeme-ma}"
PORTAL_API_KEY="${PORTAL_API_KEY:-changeme-portal}"
CLIENT_API_KEY="${CLIENT_API_KEY:-changeme-client}"

ROOT_STATUS="SKIP"
HEALTH_STATUS="SKIP"
READY_STATUS="SKIP"
SESSION_CREATE_STATUS="SKIP"
SESSION_GET_STATUS="SKIP"
SESSION_PATCH_STATUS="SKIP"
SESSION_GET_AFTER_PATCH_STATUS="SKIP"
CONTEXT_GET_STATUS="SKIP"
TURN_CREATE_STATUS="SKIP"
TURN_GET_STATUS="SKIP"
TURN_LIST_STATUS="SKIP"
SESSION_CLOSE_STATUS="SKIP"

print_section() {
  echo
  echo "=============================="
  echo "[TEST] $1"
  echo "=============================="
}

# 1. Health checks
print_section "ROOT HEALTH (/)"
if curl -sS "${BASE_URL}/"; then
  ROOT_STATUS="OK"
else
  ROOT_STATUS="FAIL"
fi

print_section "/health"
if curl -sS "${BASE_URL}/health"; then
  HEALTH_STATUS="OK"
else
  HEALTH_STATUS="FAIL"
fi

print_section "/ready"
if curl -sS "${BASE_URL}/ready"; then
  READY_STATUS="OK"
else
  READY_STATUS="FAIL"
fi

SESSION_RESPONSE=""
SESSION_GET_RESPONSE=""
GLOBAL_SESSION_KEY=""
CONTEXT_ID=""
CONVERSATION_ID=""

# 2. 세션 생성 (통합 API, AGW 키 사용)
print_section "세션 생성 (POST /api/v1/sessions)"
if SESSION_RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${AGW_API_KEY}" \
  -d '{
    "user_id": "user-001",
    "channel": "mobile",
    "request_id": "req-unified-001"
  }'); then
  echo "Response: ${SESSION_RESPONSE}"
  GLOBAL_SESSION_KEY=$(printf '%s' "${SESSION_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("global_session_key", ""))')
  CONTEXT_ID=$(printf '%s' "${SESSION_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("context_id", ""))')
  if [ -n "${GLOBAL_SESSION_KEY}" ] && [ -n "${CONTEXT_ID}" ]; then
    SESSION_CREATE_STATUS="OK"
    echo "[INFO] Parsed global_session_key: ${GLOBAL_SESSION_KEY}"
    echo "[INFO] Parsed context_id         : ${CONTEXT_ID}"
  else
    SESSION_CREATE_STATUS="FAIL"
    echo "[WARN] global_session_key 또는 context_id를 응답에서 파싱하지 못했습니다."
  fi
else
  SESSION_CREATE_STATUS="FAIL"
  echo "[ERROR] 세션 생성 요청 실패"
fi

if [ "${SESSION_CREATE_STATUS}" != "OK" ]; then
  echo
  echo "########## UNIFIED API TEST SUMMARY ##########"
  echo "ROOT            : ${ROOT_STATUS}"
  echo "HEALTH          : ${HEALTH_STATUS}"
  echo "READY           : ${READY_STATUS}"
  echo "SESSION_CREATE  : ${SESSION_CREATE_STATUS}"
  echo "SESSION_GET     : ${SESSION_GET_STATUS}"
  echo "SESSION_PATCH   : ${SESSION_PATCH_STATUS}"
  echo "SESSION_GET_2   : ${SESSION_GET_AFTER_PATCH_STATUS}"
  echo "LOCAL_REGISTER  : ${LOCAL_SESSION_REGISTER_STATUS}"
  echo "LOCAL_GET       : ${LOCAL_SESSION_GET_STATUS}"
  echo "CONTEXT_GET     : ${CONTEXT_GET_STATUS}"
  echo "TURN_CREATE     : ${TURN_CREATE_STATUS}"
  echo "TURN_GET        : ${TURN_GET_STATUS}"
  echo "TURN_LIST       : ${TURN_LIST_STATUS}"
  echo "SESSION_CLOSE   : ${SESSION_CLOSE_STATUS}"
  echo "OVERALL         : FAIL"
  exit 1
fi

# 3. 세션 조회 (통합 API, MA 키 사용)
print_section "세션 조회 (GET /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if SESSION_GET_RESPONSE=$(curl -sS "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}" \
  -H "X-API-Key: ${MA_API_KEY}"); then
  echo "Response: ${SESSION_GET_RESPONSE}"
  CONVERSATION_ID=$(printf '%s' "${SESSION_GET_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("conversation_id", ""))')
  if [ -n "${CONVERSATION_ID}" ]; then
    SESSION_GET_STATUS="OK"
    echo "[INFO] Parsed conversation_id    : ${CONVERSATION_ID}"
  else
    SESSION_GET_STATUS="FAIL"
    echo "[WARN] conversation_id를 응답에서 파싱하지 못했습니다."
  fi
else
  SESSION_GET_STATUS="FAIL"
fi

# 4. 세션 상태 업데이트 (통합 API, MA 키 사용)
print_section "세션 상태 업데이트 (PATCH /api/v1/sessions/${GLOBAL_SESSION_KEY}/state)"
if curl -sS -X PATCH "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/state" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${MA_API_KEY}" \
  -d "$(cat <<EOF
{
  "global_session_key": "${GLOBAL_SESSION_KEY}",
  "conversation_id": "${CONVERSATION_ID}",
  "turn_id": "turn-unified-001",
  "session_state": "talk",
  "state_patch": {
    "subagent_status": "continue",
    "action_owner": "ma"
  }
}
EOF
)"; then
  SESSION_PATCH_STATUS="OK"
else
  SESSION_PATCH_STATUS="FAIL"
fi

# 5. 세션 조회 (PATCH 이후, MA 키 사용)
print_section "세션 조회 - after patch (GET /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if curl -sS "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  SESSION_GET_AFTER_PATCH_STATUS="OK"
else
  SESSION_GET_AFTER_PATCH_STATUS="FAIL"
fi

# 6. Sprint 3: Context 조회 (MA 키 사용)
print_section "Sprint 3: Context 조회 (GET /api/v1/contexts/${CONTEXT_ID})"
if curl -sS "${BASE_URL}/api/v1/contexts/${CONTEXT_ID}" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  CONTEXT_GET_STATUS="OK"
else
  CONTEXT_GET_STATUS="FAIL"
fi

# 7. Sprint 3: Turn 생성 - API 호출 결과 저장 (EXTERNAL 키 사용)
print_section "Sprint 3: Turn 생성 - API 호출 결과 (POST /api/v1/contexts/${CONTEXT_ID}/turns)"
TURN_RESPONSE=""
if TURN_RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/contexts/${CONTEXT_ID}/turns" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${MA_API_KEY}" \
  -d "$(cat <<EOF
{
  "turn_id": "turn-unified-001",
  "timestamp": "2026-01-07T10:30:00Z",
  "turn_number": 1,
  "role": "system",
  "agent_id": "dbs_caller",
   "agent_type": "external",
  "metadata": {
    "api_call": {
      "api_name": "get_exchange_rate",
      "params": {"from": "KRW", "to": "USD"},
      "result": {"rate": 1320.5, "timestamp": "2026-01-07T10:30:00Z"},
      "status": "success",
      "duration_ms": 150
    }
  }
}
EOF
)"); then
  echo "Response: ${TURN_RESPONSE}"
  TURN_ID=$(printf '%s' "${TURN_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("turn_id", ""))')
  if [ -n "${TURN_ID}" ]; then
    TURN_CREATE_STATUS="OK"
    echo "[INFO] Parsed turn_id: ${TURN_ID}"
  else
    TURN_CREATE_STATUS="FAIL"
    echo "[WARN] turn_id를 응답에서 파싱하지 못했습니다."
  fi
else
  TURN_CREATE_STATUS="FAIL"
  echo "[ERROR] Turn 생성 요청 실패"
fi

# 8. Sprint 3: Turn 조회 (MA 키 사용)
if [ "${TURN_CREATE_STATUS}" == "OK" ] && [ -n "${TURN_ID}" ]; then
  print_section "Sprint 3: Turn 조회 (GET /api/v1/contexts/${CONTEXT_ID}/turns/${TURN_ID})"
  if curl -sS "${BASE_URL}/api/v1/contexts/${CONTEXT_ID}/turns/${TURN_ID}" \
    -H "X-API-Key: ${MA_API_KEY}"; then
    TURN_GET_STATUS="OK"
  else
    TURN_GET_STATUS="FAIL"
  fi
else
  TURN_GET_STATUS="SKIP"
  echo "[SKIP] Turn 조회 테스트 (Turn 생성 실패로 인해)"
fi

# 9. Sprint 3: Turn 목록 조회 (MA 키 사용)
print_section "Sprint 3: Turn 목록 조회 (GET /api/v1/contexts/${CONTEXT_ID}/turns)"
if curl -sS "${BASE_URL}/api/v1/contexts/${CONTEXT_ID}/turns?limit=10" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  TURN_LIST_STATUS="OK"
else
  TURN_LIST_STATUS="FAIL"
fi

# 10. 세션 종료 (통합 API, MA 키 사용)
print_section "세션 종료 (DELETE /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if curl -sS -X DELETE "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}?conversation_id=${CONVERSATION_ID}&close_reason=unified-api-test-finished" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  SESSION_CLOSE_STATUS="OK"
else
  SESSION_CLOSE_STATUS="FAIL"
fi

echo
echo "########## UNIFIED API TEST SUMMARY ##########"
echo "ROOT            : ${ROOT_STATUS}"
echo "HEALTH          : ${HEALTH_STATUS}"
echo "READY           : ${READY_STATUS}"
echo "SESSION_CREATE  : ${SESSION_CREATE_STATUS}"
echo "SESSION_GET     : ${SESSION_GET_STATUS}"
echo "SESSION_PATCH   : ${SESSION_PATCH_STATUS}"
echo "SESSION_GET_2   : ${SESSION_GET_AFTER_PATCH_STATUS}"
echo "CONTEXT_GET     : ${CONTEXT_GET_STATUS}"
echo "TURN_CREATE     : ${TURN_CREATE_STATUS}"
echo "TURN_GET        : ${TURN_GET_STATUS}"
echo "TURN_LIST       : ${TURN_LIST_STATUS}"
echo "SESSION_CLOSE   : ${SESSION_CLOSE_STATUS}"

if [[ "${ROOT_STATUS}" == "OK" && "${HEALTH_STATUS}" == "OK" && "${READY_STATUS}" == "OK" && \
  "${SESSION_CREATE_STATUS}" == "OK" && "${SESSION_GET_STATUS}" == "OK" && \
  "${SESSION_PATCH_STATUS}" == "OK" && "${SESSION_GET_AFTER_PATCH_STATUS}" == "OK" && \
  "${CONTEXT_GET_STATUS}" == "OK" && "${TURN_CREATE_STATUS}" == "OK" && \
      "${TURN_GET_STATUS}" == "OK" && "${TURN_LIST_STATUS}" == "OK" && \
      "${SESSION_CLOSE_STATUS}" == "OK" ]]; then
  echo "OVERALL         : SUCCESS"
else
  echo "OVERALL         : FAIL"
fi

echo
echo "[DONE] 통합 API 테스트 시퀀스 완료"
