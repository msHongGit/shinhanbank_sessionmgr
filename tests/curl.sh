#!/usr/bin/env bash
set -euo pipefail

# Session Manager 통합 API 테스트 스크립트 (v5.0 - Sprint 5)
# JWT 토큰 기반 인증, Redis 전용 저장소
#
# 주요 변경사항:
# - userId: 세션 생성 시 선택적 필드 (없으면 빈 문자열로 저장)
# - user_id: 응답에서 제외됨 (임시값이므로 클라이언트에 노출하지 않음)
# - cusnoS10: 실시간 프로파일 저장 시 선택적 필드 (없어도 저장 가능, 단 배치 프로파일은 조회 안 됨)
# 주요 변경사항:
# - userId: 세션 생성 시 선택적 필드 (없으면 빈 문자열로 저장)
# - user_id: 응답에서 제외됨 (임시값이므로)
# - cusnoS10: 실시간 프로파일 저장 시 선택적 필드 (없어도 저장 가능)


BASE_URL="${BASE_URL:-http://sol-session-manager.crewai-axd.com}"

ROOT_STATUS="SKIP"
SESSION_CREATE_STATUS="SKIP"
SESSION_GET_STATUS="SKIP"
SESSION_PATCH_STATUS="SKIP"
SESSION_GET_AFTER_PATCH_STATUS="SKIP"
SESSION_PING_STATUS="SKIP"
SESSION_VERIFY_STATUS="SKIP"
SESSION_REFRESH_STATUS="SKIP"
SOL_TURN_STATUS="SKIP"
REALTIME_PROFILE_STATUS="SKIP"
SESSION_FULL_STATUS="SKIP"
SESSION_CLOSE_STATUS="SKIP"

print_section() {
  echo
  echo "=============================="
  echo "[TEST] $1"
  echo "=============================="
}

# 1. Health check
print_section "ROOT HEALTH (/)"
if curl -sS "${BASE_URL}/"; then
  ROOT_STATUS="OK"
else
  ROOT_STATUS="FAIL"
fi

SESSION_RESPONSE=""
SESSION_GET_RESPONSE=""
GLOBAL_SESSION_KEY=""
ACCESS_TOKEN=""
REFRESH_TOKEN=""

# 2. 세션 생성 (JWT 토큰 발급 포함, 인증 없음)
# 참고: userId는 선택적 필드 (없어도 세션 생성 가능)
print_section "세션 생성 (POST /api/v1/sessions)"
HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_create_response.json -X POST "${BASE_URL}/api/v1/sessions" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "0616001905",
    "channel": {
      "eventType": "ICON_ENTRY",
      "eventChannel": "web"
    }
  }')
SESSION_RESPONSE=$(cat /tmp/session_create_response.json 2>/dev/null || echo "")

if [ "${HTTP_CODE}" -eq 201 ] || [ "${HTTP_CODE}" -eq 200 ]; then
  echo "HTTP Status: ${HTTP_CODE}"
  echo "Response: ${SESSION_RESPONSE}"
  if [ -n "${SESSION_RESPONSE}" ]; then
    GLOBAL_SESSION_KEY=$(printf '%s' "${SESSION_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("global_session_key", ""))' 2>/dev/null || echo "")
    ACCESS_TOKEN=$(printf '%s' "${SESSION_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("access_token", ""))' 2>/dev/null || echo "")
    REFRESH_TOKEN=$(printf '%s' "${SESSION_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("refresh_token", ""))' 2>/dev/null || echo "")
    if [ -n "${GLOBAL_SESSION_KEY}" ] && [ -n "${ACCESS_TOKEN}" ]; then
      SESSION_CREATE_STATUS="OK"
      echo "[INFO] Parsed global_session_key: ${GLOBAL_SESSION_KEY}"
      echo "[INFO] Access token received (length: ${#ACCESS_TOKEN})"
    else
      SESSION_CREATE_STATUS="FAIL"
      echo "[WARN] global_session_key 또는 access_token을 응답에서 파싱하지 못했습니다."
      echo "[DEBUG] Response was: ${SESSION_RESPONSE}"
    fi
  else
    SESSION_CREATE_STATUS="FAIL"
    echo "[ERROR] 응답이 비어있습니다."
  fi
else
  SESSION_CREATE_STATUS="FAIL"
  echo "[ERROR] 세션 생성 요청 실패 (HTTP ${HTTP_CODE})"
  echo "[DEBUG] Response: ${SESSION_RESPONSE}"
fi

if [ "${SESSION_CREATE_STATUS}" != "OK" ]; then
  echo
  echo "########## UNIFIED API TEST SUMMARY ##########"
  echo "ROOT            : ${ROOT_STATUS}"
  echo "SESSION_CREATE  : ${SESSION_CREATE_STATUS}"
  echo "SESSION_GET     : ${SESSION_GET_STATUS}"
  echo "SESSION_PATCH   : ${SESSION_PATCH_STATUS}"
  echo "SESSION_GET_2   : ${SESSION_GET_AFTER_PATCH_STATUS}"
  echo "SESSION_PING    : ${SESSION_PING_STATUS}"
  echo "SESSION_VERIFY  : ${SESSION_VERIFY_STATUS}"
  echo "SESSION_REFRESH : ${SESSION_REFRESH_STATUS}"
  echo "SOL_TURN        : ${SOL_TURN_STATUS}"
  echo "REALTIME_PROFILE: ${REALTIME_PROFILE_STATUS}"
  echo "SESSION_FULL    : ${SESSION_FULL_STATUS}"
  echo "SESSION_CLOSE   : ${SESSION_CLOSE_STATUS}"
  echo "OVERALL         : FAIL"
  exit 1
fi

# 3. 세션 조회 (내부 서비스용, global_session_key 경로 사용)
print_section "세션 조회 (GET /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if [ -z "${GLOBAL_SESSION_KEY}" ]; then
  echo "[ERROR] global_session_key가 없어서 세션 조회를 건너뜁니다."
  SESSION_GET_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_get_response.json "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}")
  SESSION_GET_RESPONSE=$(cat /tmp/session_get_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    echo "Response: ${SESSION_GET_RESPONSE}"
    if [ -n "${SESSION_GET_RESPONSE}" ]; then
      SESSION_STATE=$(printf '%s' "${SESSION_GET_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("session_state", ""))' 2>/dev/null || echo "")
      if [ "${SESSION_STATE}" = "start" ]; then
        SESSION_GET_STATUS="OK"
        echo "[INFO] Parsed session_state: ${SESSION_STATE}"
      else
        SESSION_GET_STATUS="FAIL"
        echo "[WARN] session_state가 기대값이 아닙니다: ${SESSION_STATE}"
      fi
    else
      SESSION_GET_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    SESSION_GET_STATUS="FAIL"
    echo "[ERROR] 세션 조회 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${SESSION_GET_RESPONSE}"
  fi
fi

# 4. 세션 상태 업데이트 (내부 서비스용, global_session_key 경로 사용)
print_section "세션 상태 업데이트 (PATCH /api/v1/sessions/${GLOBAL_SESSION_KEY}/state)"
if [ -z "${GLOBAL_SESSION_KEY}" ]; then
  echo "[ERROR] global_session_key가 없어서 세션 업데이트를 건너뜁니다."
  SESSION_PATCH_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_patch_response.json -X PATCH "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/state" \
    -H "Content-Type: application/json" \
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
)")
  PATCH_RESPONSE=$(cat /tmp/session_patch_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    SESSION_PATCH_STATUS="OK"
  else
    SESSION_PATCH_STATUS="FAIL"
    echo "[ERROR] 세션 상태 업데이트 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${PATCH_RESPONSE}"
  fi
fi

# 5. 세션 조회 (PATCH 이후)
print_section "세션 조회 - after patch (GET /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if [ -z "${GLOBAL_SESSION_KEY}" ]; then
  echo "[ERROR] global_session_key가 없어서 세션 조회를 건너뜁니다."
  SESSION_GET_AFTER_PATCH_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_get2_response.json "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}")
  SESSION_GET_RESPONSE=$(cat /tmp/session_get2_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    if [ -n "${SESSION_GET_RESPONSE}" ]; then
      SESSION_STATE=$(printf '%s' "${SESSION_GET_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("session_state", ""))' 2>/dev/null || echo "")
      if [ "${SESSION_STATE}" = "talk" ]; then
        SESSION_GET_AFTER_PATCH_STATUS="OK"
        echo "[INFO] Parsed session_state after patch: ${SESSION_STATE}"
      else
        SESSION_GET_AFTER_PATCH_STATUS="FAIL"
        echo "[WARN] session_state가 기대값이 아닙니다: ${SESSION_STATE}"
      fi
    else
      SESSION_GET_AFTER_PATCH_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    SESSION_GET_AFTER_PATCH_STATUS="FAIL"
    echo "[ERROR] 세션 조회 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${SESSION_GET_RESPONSE}"
  fi
fi

# 6. 세션 Ping (토큰 기반, TTL 연장 없음)
print_section "세션 Ping (GET /api/v1/sessions/ping)"
if [ -z "${ACCESS_TOKEN}" ]; then
  echo "[ERROR] access_token이 없어서 세션 Ping을 건너뜁니다."
  SESSION_PING_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_ping_response.json -X GET "${BASE_URL}/api/v1/sessions/ping" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}")
  PING_RESPONSE=$(cat /tmp/session_ping_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    echo "Response: ${PING_RESPONSE}"
    if [ -n "${PING_RESPONSE}" ]; then
      IS_ALIVE=$(printf '%s' "${PING_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("is_alive", False))' 2>/dev/null || echo "False")
      if [ "${IS_ALIVE}" = "True" ]; then
        SESSION_PING_STATUS="OK"
        echo "[INFO] 세션 생존 확인 성공"
      else
        SESSION_PING_STATUS="FAIL"
        echo "[WARN] 세션이 살아있지 않습니다: ${IS_ALIVE}"
      fi
    else
      SESSION_PING_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    SESSION_PING_STATUS="FAIL"
    echo "[ERROR] 세션 Ping 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${PING_RESPONSE}"
  fi
fi

# 7. 토큰 검증 및 세션 정보 조회
print_section "토큰 검증 및 세션 정보 조회 (GET /api/v1/sessions/verify)"
if [ -z "${ACCESS_TOKEN}" ]; then
  echo "[ERROR] access_token이 없어서 토큰 검증을 건너뜁니다."
  SESSION_VERIFY_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_verify_response.json -X GET "${BASE_URL}/api/v1/sessions/verify" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}")
  VERIFY_RESPONSE=$(cat /tmp/session_verify_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    echo "Response: ${VERIFY_RESPONSE}"
    if [ -n "${VERIFY_RESPONSE}" ]; then
      VERIFIED_KEY=$(printf '%s' "${VERIFY_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("global_session_key", ""))' 2>/dev/null || echo "")
      if [ "${VERIFIED_KEY}" = "${GLOBAL_SESSION_KEY}" ]; then
        SESSION_VERIFY_STATUS="OK"
        echo "[INFO] 토큰 검증 성공, global_session_key 일치: ${VERIFIED_KEY}"
      else
        SESSION_VERIFY_STATUS="FAIL"
        echo "[WARN] global_session_key가 일치하지 않습니다: ${VERIFIED_KEY} != ${GLOBAL_SESSION_KEY}"
      fi
    else
      SESSION_VERIFY_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    SESSION_VERIFY_STATUS="FAIL"
    echo "[ERROR] 토큰 검증 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${VERIFY_RESPONSE}"
  fi
fi

# 8. 토큰 갱신 (Refresh Token Rotation)
print_section "토큰 갱신 (POST /api/v1/sessions/refresh)"
if [ -z "${REFRESH_TOKEN}" ]; then
  echo "[ERROR] refresh_token이 없어서 토큰 갱신을 건너뜁니다."
  SESSION_REFRESH_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_refresh_response.json -X POST "${BASE_URL}/api/v1/sessions/refresh" \
    -H "Authorization: Bearer ${REFRESH_TOKEN}" \
    -H "Content-Type: application/json")
  REFRESH_RESPONSE=$(cat /tmp/session_refresh_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    echo "Response: ${REFRESH_RESPONSE}"
    if [ -n "${REFRESH_RESPONSE}" ]; then
      NEW_ACCESS_TOKEN=$(printf '%s' "${REFRESH_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("access_token", ""))' 2>/dev/null || echo "")
      NEW_REFRESH_TOKEN=$(printf '%s' "${REFRESH_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("refresh_token", ""))' 2>/dev/null || echo "")
      if [ -n "${NEW_ACCESS_TOKEN}" ] && [ -n "${NEW_REFRESH_TOKEN}" ]; then
        SESSION_REFRESH_STATUS="OK"
        ACCESS_TOKEN="${NEW_ACCESS_TOKEN}"
        REFRESH_TOKEN="${NEW_REFRESH_TOKEN}"
        echo "[INFO] 토큰 갱신 성공 (새 토큰으로 업데이트됨)"
      else
        SESSION_REFRESH_STATUS="FAIL"
        echo "[WARN] 새 토큰을 응답에서 파싱하지 못했습니다."
      fi
    else
      SESSION_REFRESH_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    SESSION_REFRESH_STATUS="FAIL"
    echo "[ERROR] 토큰 갱신 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${REFRESH_RESPONSE}"
  fi
fi

# 9. SOL API 연동 결과 저장 (Sprint 5: POST /api/v1/sessions/{global_session_key}/api-results)
print_section "SOL API 결과 저장 (POST /api/v1/sessions/${GLOBAL_SESSION_KEY}/api-results)"
if [ -z "${GLOBAL_SESSION_KEY}" ]; then
  echo "[ERROR] global_session_key가 없어서 SOL 결과 저장을 건너뜁니다."
  SOL_TURN_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/sol_turn_response.json -X POST "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/api-results" \
    -H "Content-Type: application/json" \
    -d @- <<EOF
{
  "global_session_key": "${GLOBAL_SESSION_KEY}",
  "turn_id": "turn-unified-001",
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
)
  SOL_TURN_RESPONSE=$(cat /tmp/sol_turn_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 201 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    echo "Response: ${SOL_TURN_RESPONSE}"
    if [ -n "${SOL_TURN_RESPONSE}" ]; then
      SAVED_TURN_ID=$(printf '%s' "${SOL_TURN_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("turn_id", ""))' 2>/dev/null || echo "")
      if [ -n "${SAVED_TURN_ID}" ]; then
        SOL_TURN_STATUS="OK"
        echo "[INFO] Saved turn_id: ${SAVED_TURN_ID}"
      else
        SOL_TURN_STATUS="FAIL"
        echo "[WARN] turn_id를 응답에서 파싱하지 못했습니다."
        echo "[DEBUG] Response: ${SOL_TURN_RESPONSE}"
      fi
    else
      SOL_TURN_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    SOL_TURN_STATUS="FAIL"
    echo "[ERROR] SOL 결과 저장 요청 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${SOL_TURN_RESPONSE}"
  fi
fi

# 10. 실시간 프로파일 업데이트 (POST /api/v1/sessions/realtime-personal-context)
# 참고: cusnoN10은 profile_data 최상위 필드 (선택적, 없어도 저장 가능)
print_section "실시간 프로파일 업데이트 (POST /api/v1/sessions/realtime-personal-context)"
if [ -z "${GLOBAL_SESSION_KEY}" ]; then
  echo "[ERROR] global_session_key가 없어서 실시간 프로파일 업데이트를 건너뜁니다."
  REALTIME_PROFILE_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/realtime_profile_response.json -X POST "${BASE_URL}/api/v1/sessions/realtime-personal-context" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d @- <<EOF
{
  "profile_data": {
    "cusnoN10": "0616001905",
    "cusSungNmS20": "홍길동",
    "hpNoS12": "01031286270",
    "biryrMmddS6": "710115",
    "onlyAgeN3": 55,
    "membGdS2": "02",
    "loginDt": "2026.01.21",
    "loginTimesS6": "14:23:59",
    "ygSexS1": "2",
    "cusSangtaeS2": "OK"
  }
}
EOF
)
  REALTIME_PROFILE_RESPONSE=$(cat /tmp/realtime_profile_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    echo "Response: ${REALTIME_PROFILE_RESPONSE}"
    if [ -n "${REALTIME_PROFILE_RESPONSE}" ]; then
      PROFILE_STATUS=$(printf '%s' "${REALTIME_PROFILE_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("status", ""))' 2>/dev/null || echo "")
      if [ "${PROFILE_STATUS}" = "success" ]; then
        REALTIME_PROFILE_STATUS="OK"
        echo "[INFO] 실시간 프로파일 업데이트 성공"
      else
        REALTIME_PROFILE_STATUS="FAIL"
        echo "[WARN] 프로파일 업데이트 상태가 기대값이 아닙니다: ${PROFILE_STATUS}"
        echo "[DEBUG] Response: ${REALTIME_PROFILE_RESPONSE}"
      fi
    else
      REALTIME_PROFILE_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    REALTIME_PROFILE_STATUS="FAIL"
    echo "[ERROR] 실시간 프로파일 업데이트 요청 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${REALTIME_PROFILE_RESPONSE}"
  fi
fi

# 11. 세션 전체 정보 조회 (세션 + 턴 목록, Sprint 5)
print_section "세션 전체 정보 조회 (GET /api/v1/sessions/${GLOBAL_SESSION_KEY}/full)"
if [ -z "${GLOBAL_SESSION_KEY}" ]; then
  echo "[ERROR] global_session_key가 없어서 세션 전체 정보 조회를 건너뜁니다."
  SESSION_FULL_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_full_response.json "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}/full")
  SESSION_FULL_RESPONSE=$(cat /tmp/session_full_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    echo "Response: ${SESSION_FULL_RESPONSE}"
    if [ -n "${SESSION_FULL_RESPONSE}" ]; then
      TOTAL_TURNS=$(printf '%s' "${SESSION_FULL_RESPONSE}" | python3 -c 'import sys, json; d=json.load(sys.stdin); print(d.get("total_turns", 0))' 2>/dev/null || echo "0")
      if [ "${TOTAL_TURNS}" -gt 0 ]; then
        SESSION_FULL_STATUS="OK"
        echo "[INFO] Total turns: ${TOTAL_TURNS}"
      else
        SESSION_FULL_STATUS="FAIL"
        echo "[WARN] 턴이 없거나 응답 형식이 맞지 않습니다. (total_turns: ${TOTAL_TURNS})"
      fi
    else
      SESSION_FULL_STATUS="FAIL"
      echo "[ERROR] 응답이 비어있습니다."
    fi
  else
    SESSION_FULL_STATUS="FAIL"
    echo "[ERROR] 세션 전체 정보 조회 요청 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${SESSION_FULL_RESPONSE}"
  fi
fi

# 12. 세션 종료 (내부 서비스용, global_session_key 경로 사용)
print_section "세션 종료 (DELETE /api/v1/sessions/${GLOBAL_SESSION_KEY})"
if [ -z "${GLOBAL_SESSION_KEY}" ]; then
  echo "[ERROR] global_session_key가 없어서 세션 종료를 건너뜁니다."
  SESSION_CLOSE_STATUS="SKIP"
else
  HTTP_CODE=$(curl -sS -w "%{http_code}" -o /tmp/session_close_response.json -X DELETE "${BASE_URL}/api/v1/sessions/${GLOBAL_SESSION_KEY}?close_reason=unified-api-test-finished")
  CLOSE_RESPONSE=$(cat /tmp/session_close_response.json 2>/dev/null || echo "")
  if [ "${HTTP_CODE}" -eq 200 ]; then
    echo "HTTP Status: ${HTTP_CODE}"
    SESSION_CLOSE_STATUS="OK"
  else
    SESSION_CLOSE_STATUS="FAIL"
    echo "[ERROR] 세션 종료 실패 (HTTP ${HTTP_CODE})"
    echo "[DEBUG] Response: ${CLOSE_RESPONSE}"
  fi
fi

echo
echo "########## UNIFIED API TEST SUMMARY ##########"
echo "ROOT            : ${ROOT_STATUS}"
echo "SESSION_CREATE  : ${SESSION_CREATE_STATUS}"
echo "SESSION_GET     : ${SESSION_GET_STATUS}"
echo "SESSION_PATCH   : ${SESSION_PATCH_STATUS}"
echo "SESSION_GET_2   : ${SESSION_GET_AFTER_PATCH_STATUS}"
echo "SESSION_PING    : ${SESSION_PING_STATUS}"
echo "SESSION_VERIFY  : ${SESSION_VERIFY_STATUS}"
echo "SESSION_REFRESH : ${SESSION_REFRESH_STATUS}"
echo "SOL_TURN        : ${SOL_TURN_STATUS}"
echo "REALTIME_PROFILE: ${REALTIME_PROFILE_STATUS}"
echo "SESSION_FULL    : ${SESSION_FULL_STATUS}"
echo "SESSION_CLOSE   : ${SESSION_CLOSE_STATUS}"

if [[ "${ROOT_STATUS}" == "OK" && \
  "${SESSION_CREATE_STATUS}" == "OK" && "${SESSION_GET_STATUS}" == "OK" && \
  "${SESSION_PATCH_STATUS}" == "OK" && "${SESSION_GET_AFTER_PATCH_STATUS}" == "OK" && \
  "${SESSION_PING_STATUS}" == "OK" && "${SESSION_VERIFY_STATUS}" == "OK" && \
  "${SESSION_REFRESH_STATUS}" == "OK" && "${SOL_TURN_STATUS}" == "OK" && \
  "${REALTIME_PROFILE_STATUS}" == "OK" && "${SESSION_FULL_STATUS}" == "OK" && \
  "${SESSION_CLOSE_STATUS}" == "OK" ]]; then
  echo "OVERALL         : SUCCESS"
else
  echo "OVERALL         : FAIL"
fi

echo
echo "[DONE] 통합 API 테스트 시퀀스 완료"
