#!/usr/bin/env bash
set -uuo pipefail

# Session Manager curl test script
# 사용 전 아래 환경 변수를 셋업하세요:
#   export BASE_URL="http://sol-session-manager.crewai-axd.com"
#   export AGW_API_KEY="..."
#   export MA_API_KEY="..."
#   export PORTAL_API_KEY="..."   # 필요 시
#   export VDB_API_KEY="..."      # 필요 시

BASE_URL="${BASE_URL:-http://sol-session-manager.crewai-axd.com}"
AGW_API_KEY="${AGW_API_KEY:-changeme-agw}"
MA_API_KEY="${MA_API_KEY:-changeme-ma}"
PORTAL_API_KEY="${PORTAL_API_KEY:-changeme-portal}"
VDB_API_KEY="${VDB_API_KEY:-changeme-vdb}"

ROOT_STATUS="SKIP"
HEALTH_STATUS="SKIP"
READY_STATUS="SKIP"
AGW_STATUS="SKIP"
MA_RESOLVE_STATUS="SKIP"
MA_PATCH_STATUS="SKIP"
MA_RESOLVE_AFTER_PATCH_STATUS="SKIP"
MA_LOCAL_REGISTER_STATUS="SKIP"
MA_LOCAL_GET_STATUS="SKIP"
PORTAL_LIST_STATUS="SKIP"
MA_CLOSE_STATUS="SKIP"

print_section() {
  echo
  echo "=============================="
  echo "[TEST] $1"
  echo "=============================="
}

# 1. Health checks
print_section "ROOT HEALTH (/)"
if curl -v "${BASE_URL}/"; then
  ROOT_STATUS="OK"
else
  ROOT_STATUS="FAIL"
fi

print_section "/health"
if curl -v "${BASE_URL}/health"; then
  HEALTH_STATUS="OK"
else
  HEALTH_STATUS="FAIL"
fi

print_section "/ready"
if curl -v "${BASE_URL}/ready"; then
  READY_STATUS="OK"
else
  READY_STATUS="FAIL"
fi

AGW_RESPONSE=""
GLOBAL_SESSION_KEY=""
CONVERSATION_ID=""

# 2. AGW - 세션 생성
print_section "AGW - 세션 생성 (/api/v1/agw/sessions)"
if AGW_RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/agw/sessions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${AGW_API_KEY}" \
  -d '{
    "user_id": "user-001",
    "channel": "mobile",
    "request_id": "req-001"
  }'); then
  echo "Response: ${AGW_RESPONSE}"
  GLOBAL_SESSION_KEY=$(printf '%s' "${AGW_RESPONSE}" | python -c 'import sys, json; d=json.load(sys.stdin); print(d.get("global_session_key", ""))')
  CONVERSATION_ID=$(printf '%s' "${AGW_RESPONSE}" | python -c 'import sys, json; d=json.load(sys.stdin); print(d.get("conversation_id", ""))')
  if [ -n "${GLOBAL_SESSION_KEY}" ] && [ -n "${CONVERSATION_ID}" ]; then
    AGW_STATUS="OK"
    echo "[INFO] Parsed global_session_key: ${GLOBAL_SESSION_KEY}"
    echo "[INFO] Parsed conversation_id    : ${CONVERSATION_ID}"
  else
    AGW_STATUS="FAIL"
    echo "[WARN] global_session_key 또는 conversation_id를 응답에서 파싱하지 못했습니다. 이후 MA/Portal 테스트는 건너뜁니다."
  fi
else
  AGW_STATUS="FAIL"
  echo "[ERROR] AGW 세션 생성 요청 실패"
fi

if [ "${AGW_STATUS}" != "OK" ]; then
  echo
  echo "########## CURL TEST SUMMARY ##########"
  echo "ROOT          : ${ROOT_STATUS}"
  echo "HEALTH        : ${HEALTH_STATUS}"
  echo "READY         : ${READY_STATUS}"
  echo "AGW_CREATE    : ${AGW_STATUS}"
  echo "MA_RESOLVE    : ${MA_RESOLVE_STATUS}"
  echo "MA_PATCH      : ${MA_PATCH_STATUS}"
  echo "MA_RESOLVE_2  : ${MA_RESOLVE_AFTER_PATCH_STATUS}"
  echo "MA_LOCAL_REG  : ${MA_LOCAL_REGISTER_STATUS}"
  echo "MA_LOCAL_GET  : ${MA_LOCAL_GET_STATUS}"
  echo "PORTAL_LIST   : ${PORTAL_LIST_STATUS}"
  echo "MA_CLOSE      : ${MA_CLOSE_STATUS}"
  echo "OVERALL       : FAIL"
  exit 1
fi

# 3. MA - 세션 조회(resolve)
print_section "MA - 세션 조회 (/api/v1/ma/sessions/resolve)"
if curl -v "${BASE_URL}/api/v1/ma/sessions/resolve?global_session_key=${GLOBAL_SESSION_KEY}" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  MA_RESOLVE_STATUS="OK"
else
  MA_RESOLVE_STATUS="FAIL"
fi

# 4. MA - 세션 상태 업데이트 (PATCH)
print_section "MA - 세션 상태 업데이트 (/api/v1/ma/sessions/state)"
if curl -v -X PATCH "${BASE_URL}/api/v1/ma/sessions/state" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${MA_API_KEY}" \
  -d "$(cat <<EOF
{
  \"global_session_key\": \"${GLOBAL_SESSION_KEY}\",
  \"conversation_id\": \"${CONVERSATION_ID}\",
  \"turn_id\": \"turn-001\",
  \"session_state\": \"talk\",\
  \"state_patch\": {
    \"subagent_status\": \"continue\",\
    \"action_owner\": \"ma\"
  }
}
EOF
)"; then
  MA_PATCH_STATUS="OK"
else
  MA_PATCH_STATUS="FAIL"
fi

# 5. MA - 세션 조회 (PATCH 이후)
print_section "MA - 세션 조회 (after patch) (/api/v1/ma/sessions/resolve)"
if curl -v "${BASE_URL}/api/v1/ma/sessions/resolve?global_session_key=${GLOBAL_SESSION_KEY}" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  MA_RESOLVE_AFTER_PATCH_STATUS="OK"
else
  MA_RESOLVE_AFTER_PATCH_STATUS="FAIL"
fi

LOCAL_RESPONSE=""

# 6. MA - Local 세션 등록
print_section "MA - Local 세션 등록 (/api/v1/ma/sessions/local)"
if LOCAL_RESPONSE=$(curl -sS -X POST "${BASE_URL}/api/v1/ma/sessions/local" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${MA_API_KEY}" \
  -d "$(cat <<EOF
{
  \"global_session_key\": \"${GLOBAL_SESSION_KEY}\",
  \"agent_id\": \"ma-001\",
  \"local_session_key\": \"local-${GLOBAL_SESSION_KEY}\"
}
EOF
)"); then
  MA_LOCAL_REGISTER_STATUS="OK"
  echo "Response: ${LOCAL_RESPONSE}"
else
  MA_LOCAL_REGISTER_STATUS="FAIL"
  echo "[ERROR] MA Local 세션 등록 실패"
fi

# 7. MA - Local 세션 조회
print_section "MA - Local 세션 조회 (/api/v1/ma/sessions/local)"
if curl -v "${BASE_URL}/api/v1/ma/sessions/local?global_session_key=${GLOBAL_SESSION_KEY}&agent_id=ma-001" \
  -H "X-API-Key: ${MA_API_KEY}"; then
  MA_LOCAL_GET_STATUS="OK"
else
  MA_LOCAL_GET_STATUS="FAIL"
fi

# 8. Portal - 세션 목록 조회 (옵션)
print_section "Portal - 세션 목록 조회 (/api/v1/portal/sessions)"
if curl -v "${BASE_URL}/api/v1/portal/sessions?page=1&page_size=10" \
  -H "X-API-Key: ${PORTAL_API_KEY}"; then
  PORTAL_LIST_STATUS="OK"
else
  PORTAL_LIST_STATUS="FAIL"
fi

# 9. MA - 세션 종료 (옵션)
print_section "MA - 세션 종료 (/api/v1/ma/sessions/close)"
if curl -v -X POST "${BASE_URL}/api/v1/ma/sessions/close" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${MA_API_KEY}" \
  -d "$(cat <<EOF
{
  \"global_session_key\": \"${GLOBAL_SESSION_KEY}\",\
  \"conversation_id\": \"${CONVERSATION_ID}\",\
  \"close_reason\": \"demo-finished\",\
  \"final_summary\": \"demo finished by curl_tests.sh\"\
}
EOF
)"; then
  MA_CLOSE_STATUS="OK"
else
  MA_CLOSE_STATUS="FAIL"
fi

echo
echo "########## CURL TEST SUMMARY ##########"
echo "ROOT          : ${ROOT_STATUS}"
echo "HEALTH        : ${HEALTH_STATUS}"
echo "READY         : ${READY_STATUS}"
echo "AGW_CREATE    : ${AGW_STATUS}"
echo "MA_RESOLVE    : ${MA_RESOLVE_STATUS}"
echo "MA_PATCH      : ${MA_PATCH_STATUS}"
echo "MA_RESOLVE_2  : ${MA_RESOLVE_AFTER_PATCH_STATUS}"
echo "MA_LOCAL_REG  : ${MA_LOCAL_REGISTER_STATUS}"
echo "MA_LOCAL_GET  : ${MA_LOCAL_GET_STATUS}"
echo "PORTAL_LIST   : ${PORTAL_LIST_STATUS}"
echo "MA_CLOSE      : ${MA_CLOSE_STATUS}"

if [[ "${ROOT_STATUS}" == "OK" && "${HEALTH_STATUS}" == "OK" && "${READY_STATUS}" == "OK" && \
  "${AGW_STATUS}" == "OK" && "${MA_RESOLVE_STATUS}" == "OK" && \
  "${MA_PATCH_STATUS}" == "OK" && "${MA_RESOLVE_AFTER_PATCH_STATUS}" == "OK" && \
      "${MA_LOCAL_REGISTER_STATUS}" == "OK" && "${MA_LOCAL_GET_STATUS}" == "OK" && \
      "${PORTAL_LIST_STATUS}" == "OK" && "${MA_CLOSE_STATUS}" == "OK" ]]; then
  echo "OVERALL       : SUCCESS"
else
  echo "OVERALL       : FAIL"
fi

echo
echo "[DONE] curl 테스트 시퀀스 완료"
