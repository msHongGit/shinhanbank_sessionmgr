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
SESSION_CREATE_STATUS="SKIP"
SESSION_GET_STATUS="SKIP"
SESSION_PATCH_STATUS="SKIP"
SESSION_GET_AFTER_PATCH_STATUS="SKIP"
SOL_TURN_STATUS="SKIP"
SESSION_CLOSE_STATUS="SKIP"

print_section() {
  echo
  echo "=============================="
  echo "[TEST] $1"
  echo "=============================="
}

# 1. Health check (root only - 현재 코드 기준)
print_section "ROOT HEALTH (/)"
if curl -sS "${BASE_URL}/"; then
  ROOT_STATUS="OK"
else
  ROOT_STATUS="FAIL"
fi

SESSION_RESPONSE=""
SESSION_GET_RESPONSE=""
GLOBAL_SESSION_KEY=""

# 2. 세션 생성 (통합 API, AGW 키 사용)
print_section "세션 생성 (POST /api/v1/sessions)"
if SESSION_RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${AGW_API_KEY}" \
  -d '{
    "userId": "user-001",
    "startType": "ICON_ENTRY"
  }'); then
  echo "Response: ${SESSION_RESPONSE}"
  GLOBAL_SESSION_KEY=$(printf '%s' "${SESSION_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("global_session_key", ""))')
  if [ -n "${GLOBAL_SESSION_KEY}" ]; then
    SESSION_CREATE_STATUS="OK"
    echo "[INFO] Parsed global_session_key: ${GLOBAL_SESSION_KEY}"
  else
    SESSION_CREATE_STATUS="FAIL"
    echo "[WARN] global_session_key를 응답에서 파싱하지 못했습니다."
  fi
else
  SESSION_CREATE_STATUS="FAIL"
  echo "[ERROR] 세션 생성 요청 실패"
fi

if [ "${SESSION_CREATE_STATUS}" != "OK" ]; then
  echo
  echo "########## UNIFIED API TEST SUMMARY ##########"
  echo "ROOT            : ${ROOT_STATUS}"
  echo "SESSION_CREATE  : ${SESSION_CREATE_STATUS}"
  echo "SESSION_GET     : ${SESSION_GET_STATUS}"
  echo "SESSION_PATCH   : ${SESSION_PATCH_STATUS}"
  echo "SESSION_GET_2   : ${SESSION_GET_AFTER_PATCH_STATUS}"
  echo "SOL_TURN        : ${SOL_TURN_STATUS}"
  echo "SESSION_CLOSE   : ${SESSION_CLOSE_STATUS}"
  echo "OVERALL         : FAIL"
  exit 1
fi

# 3. 세션 조회 (통합 API, MA 키 사용)
print_section "세션 조회 (GET /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if SESSION_GET_RESPONSE=$(curl -sS "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}" \
  -H "X-API-Key: ${MA_API_KEY}"); then
  echo "Response: ${SESSION_GET_RESPONSE}"
  SESSION_STATE=$(printf '%s' "${SESSION_GET_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("session_state", ""))')
  if [ "${SESSION_STATE}" = "start" ]; then
    SESSION_GET_STATUS="OK"
    echo "[INFO] Parsed session_state      : ${SESSION_STATE}"
  else
    SESSION_GET_STATUS="FAIL"
    echo "[WARN] session_state가 기대값이 아닙니다: ${SESSION_STATE}"
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
if SESSION_GET_RESPONSE=$(curl -sS "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}" \
  -H "X-API-Key: ${MA_API_KEY}"); then
  SESSION_GET_AFTER_PATCH_STATUS="OK"
else
  SESSION_GET_AFTER_PATCH_STATUS="FAIL"
fi

# 6. Sprint 3: SOL 연동 결과 저장 (POST /api/v1/contexts/turn-results)
print_section "Sprint 3: SOL 결과 저장 (POST /api/v1/contexts/turn-results)"
SOL_TURN_RESPONSE=""
if SOL_TURN_RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/contexts/turn-results" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${MA_API_KEY}" \
  -d "$(cat <<EOF
{
  "sessionId": "${GLOBAL_SESSION_KEY}",
  "turnId": "turn-unified-001",
  "agent": "dbs_caller",
  "transactionPayload": [
    {
      "trxCd": "TRX001",
      "dataBody": {"from": "KRW", "to": "USD"}
    }
  ],
  "globId": "glob-unified-001",
  "requestId": "req-unified-001",
  "result": "SUCCESS",
  "resultCode": "0000",
  "resultMsg": "OK",
  "transactionResult": [
    {
      "trxCd": "TRX001",
      "responseData": {"rate": 1320.5, "timestamp": "2026-01-07T10:30:00Z"}
    }
  ]
}
EOF
)"; then
  echo "Response: ${SOL_TURN_RESPONSE}"
  SAVED_TURN_ID=$(printf '%s' "${SOL_TURN_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("turn_id", ""))')
  if [ -n "${SAVED_TURN_ID}" ]; then
    SOL_TURN_STATUS="OK"
    echo "[INFO] Saved turn_id: ${SAVED_TURN_ID}"
  else
    SOL_TURN_STATUS="FAIL"
    echo "[WARN] turn_id를 응답에서 파싱하지 못했습니다."
  fi
else
  SOL_TURN_STATUS="FAIL"
  echo "[ERROR] SOL 결과 저장 요청 실패"
fi

# 7. 세션 종료 (통합 API, MA 키 사용)
print_section "세션 종료 (DELETE /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if curl -sS -X DELETE "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}?close_reason=unified-api-test-finished" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  SESSION_CLOSE_STATUS="OK"
else
  SESSION_CLOSE_STATUS="FAIL"
fi

echo
echo "########## UNIFIED API TEST SUMMARY ##########"
echo "ROOT            : ${ROOT_STATUS}"
echo "SESSION_CREATE  : ${SESSION_CREATE_STATUS}"
echo "SESSION_GET     : ${SESSION_GET_STATUS}"
echo "SESSION_PATCH   : ${SESSION_PATCH_STATUS}"
echo "SESSION_GET_2   : ${SESSION_GET_AFTER_PATCH_STATUS}"
echo "SOL_TURN        : ${SOL_TURN_STATUS}"
echo "SESSION_CLOSE   : ${SESSION_CLOSE_STATUS}"

if [[ "${ROOT_STATUS}" == "OK" && \
  "${SESSION_CREATE_STATUS}" == "OK" && "${SESSION_GET_STATUS}" == "OK" && \
  "${SESSION_PATCH_STATUS}" == "OK" && "${SESSION_GET_AFTER_PATCH_STATUS}" == "OK" && \
  "${SOL_TURN_STATUS}" == "OK" && "${SESSION_CLOSE_STATUS}" == "OK" ]]; then
  echo "OVERALL         : SUCCESS"
else
  echo "OVERALL         : FAIL"
fi

echo
echo "[DONE] 통합 API 테스트 시퀀스 완료"
