"""
Session Manager
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from app.core.jwt_auth import extract_token_from_request, get_global_session_key_from_token
from app.schemas.common import (
    AgentType,
    RealtimePersonalContextRequest,
    RealtimePersonalContextResponse,
    SessionCloseRequest,
    SessionCloseResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionFullResponse,
    SessionPatchRequest,
    SessionPatchResponse,
    SessionPingResponse,
    SessionResolveRequest,
    SessionResolveResponse,
    SessionVerifyResponse,
    SolApiResultRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TurnResponse,
)
from app.services.session_service import SessionService, get_session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


# ============ 세션 생성 ============


@router.post(
    "",
    response_model=SessionCreateResponse,
    status_code=201,
    summary="세션 생성",
    description="""
    선택 요청 필드:
    - userId: 세션을 식별할 사용자 ID (선택, 없으면 빈 문자열로 저장)
    - channel: 이벤트/채널 정보 딕셔너리 (옵션)
        - eventType: 세션 진입 유형 (예: ICON_ENTRY)
        - eventChannel: 호출 채널 (예: web, kiosk 등)

    주요 응답 필드:
    - global_session_key: Global 세션 키
    - access_token: Access Token (JWT)
    - refresh_token: Refresh Token (JWT)
    - jti: JWT ID
    
    참고:
    - AGW는 이 정보를 받아 Client에는 토큰만 전달
    - userId는 세션 생성 시 임시값으로 저장되며, 실제 고객번호(cusno)는
      실시간 프로파일 저장 API 호출 시 cusnoN10에서 추출되어 세션에 저장
      (cusnoN10이 없으면 세션에 cusno가 저장되지 않으며, 실시간 프로파일은 세션 키 기반으로 저장)
    """,
)
async def create_session(
    request: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    service: SessionService = Depends(get_session_service),
):
    """
    세션 생성 API - JWT 토큰 발급 포함

    - AGW: Agent Gateway가 초기 세션 생성
    - JWT 토큰 발급: Access Token 및 Refresh Token 자동 발급
    """
    user_id_display = request.user_id or "(empty)"
    logger.info(f"Creating session for user_id: {user_id_display}")
    try:
        result = await service.create_session(request, background_tasks)
        logger.info(f"Session created: global_session_key={result.global_session_key}")
        return result
    except Exception as e:
        logger.error(f"Failed to create session for user_id={user_id_display}: {e}", exc_info=True)
        raise


# ============ JWT Token Verification & Refresh (구체적인 경로를 먼저 정의) ============
# 주의: FastAPI는 라우트를 등록한 순서대로 매칭하므로,
# 구체적인 경로(/ping, /verify, /refresh)를 동적 경로(/{global_session_key})보다 먼저 정의해야 합니다.


@router.get(
    "/ping",
    response_model=SessionPingResponse,
    summary="세션 생존 확인",
    description="""
    세션이 살아있는지 확인, 토큰에서 추출
    
    요청:
    - 헤더: Authorization: Bearer <access_token> 또는 쿠키의 access_token

    주요 응답 필드:
    - is_alive: 세션 존재 여부 (false면 세션이 없거나 만료됨)
    - expires_at: 현재 만료 시각 (is_alive=false이면 null, TTL 연장 안 함)
    """,
)
async def ping_session(
    request: Request,
    service: SessionService = Depends(get_session_service),
):
    """세션 Ping API (토큰 기반, TTL 연장 없음)"""
    token = extract_token_from_request(request)
    if not token:
        logger.warning("Ping request without access token")
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        result = await service.auth_service.ping_session_by_token(token)
        logger.info(f"Session ping: is_alive={result.is_alive}")
        return result
    except Exception as e:
        logger.error(f"Failed to ping session: {e}", exc_info=True)
        raise


@router.get(
    "/verify",
    response_model=SessionVerifyResponse,
    summary="토큰 검증 및 세션 정보 조회",
    description="""
    Access Token을 검증하고 global_session_key 및 세션 정보를 반환
        
    요청:
    - 헤더: Authorization: Bearer <access_token> 또는 쿠키의 access_token
    
    응답:
    - global_session_key: Global 세션 키
    - session_state: 세션 상태
    - is_alive: 세션 생존 여부
    - expires_at: 만료 시각
    """,
)
async def verify_token_and_get_session(
    request: Request,
    service: SessionService = Depends(get_session_service),
):
    """토큰 검증 및 세션 정보 조회 API"""
    token = extract_token_from_request(request)
    if not token:
        logger.warning("Verify request without access token")
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        result = await service.auth_service.verify_token_and_get_session(token)
        logger.info(f"Token verified: global_session_key={result.global_session_key}")
        return result
    except Exception as e:
        logger.error(f"Failed to verify token: {e}", exc_info=True)
        raise


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="토큰 갱신",
    description="""
    Refresh Token으로 새 Access Token과 Refresh Token을 발급
    세션 TTL도 함께 연장
    
    요청:
    - 헤더: Authorization: Bearer <refresh_token> 또는 쿠키의 refresh_token
    - 또는 요청 body에 refresh_token 포함
    
    응답:
    - access_token: 새 Access Token
    - refresh_token: 새 Refresh Token (Refresh Token Rotation)
    - global_session_key: Global 세션 키 (AGW에만 전달)
    - jti: JWT ID
    """,
)
async def refresh_token(
    request: Request,
    refresh_request: TokenRefreshRequest | None = None,
    service: SessionService = Depends(get_session_service),
):
    """토큰 갱신 API"""
    # Refresh Token 추출 (쿠키 우선, 없으면 요청 body)
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token and refresh_request:
        refresh_token = refresh_request.refresh_token

    if not refresh_token:
        # 헤더에서도 시도
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header[7:]

    if not refresh_token:
        logger.warning("Refresh request without refresh token")
        raise HTTPException(status_code=401, detail="Refresh token required")

    try:
        result = await service.auth_service.refresh_token(refresh_token)
        logger.info(f"Token refreshed: global_session_key={result.global_session_key}")
        return result
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}", exc_info=True)
        raise


# ============ 세션 조회 ============


@router.get(
    "/{global_session_key}",
    response_model=SessionResolveResponse,
    summary="세션 조회",
    description="""
    필수 경로 변수:
    - global_session_key: 조회할 세션 키

    선택 쿼리 파라미터:
    - agent_type, agent_id: 업무 Agent용 로컬 세션 키 조회에 사용

    주요 응답 필드:
    - global_session_key: 조회된 세션 키
    - channel: 세션 채널/이벤트 정보 (옵션)
        - eventType: 세션 진입 유형 (기존 startType)
        - eventChannel: 세션 채널 (기존 channel, web/kiosk 등)
    - session_state: 현재 세션 상태 (start/talk/end)
    - is_first_call: start 상태인지 여부
    - task_queue_status, subagent_status: 백엔드 작업/서브에이전트 상태
    - agent_session_key: (옵션) 업무 Agent 로컬 세션 키 매핑 결과
    - customer_profile: 세션에 저장된 고객 프로파일 (없으면 null)
    """,
)
async def get_session(
    global_session_key: str,
    agent_type: AgentType | None = Query(None, description="Agent 유형 (옵션)"),
    agent_id: str | None = Query(None, description="Agent ID (옵션)"),
    service: SessionService = Depends(get_session_service),
):
    """
    세션 조회 API

    - MA: 세션 상태, SubAgent 상태 조회
    - Portal: 관리자 조회
    - Client: 사용자 세션 조회
    """
    logger.info(f"Getting session: global_session_key={global_session_key}, agent_type={agent_type}, agent_id={agent_id}")
    try:
        request = SessionResolveRequest(
            global_session_key=global_session_key,
            agent_type=agent_type,
            agent_id=agent_id,
        )
        result = await service.resolve_session(request)
        logger.info(f"Session retrieved: global_session_key={global_session_key}, state={result.session_state}")
        return result
    except Exception as e:
        logger.error(f"Failed to get session: global_session_key={global_session_key}, error={e}", exc_info=True)
        raise


# ============ 세션 상태 업데이트 ============


@router.patch(
    "/{global_session_key}/state",
    response_model=SessionPatchResponse,
    summary="세션 상태 업데이트",
    description="""
        필수 경로 변수:
        - global_session_key: 상태를 변경할 세션 키

        필수 요청 필드:
        - global_session_key: Path 변수와 동일해야 함

        선택 요청 필드 (Patch 방식):
        - session_state: 세션 상태 (start/talk/end) - 전송 시에만 변경
        - turn_id: 이 업데이트가 대응하는 턴 ID (이벤트 추적용)
        - state_patch: 업데이트할 세부 상태(서브에이전트 상태, 마지막 이벤트, session_attributes 등)

        session_state 값:
        - start: 세션 시작 상태
        - talk: 대화 진행 중 상태
        - end: 세션 종료 상태

        주요 동작:
        - SubAgent 상태, 마지막 이벤트, 세션 메타데이터(session_attributes) 업데이트
        - state_patch.agent_session_key + last_agent_id 가 함께 오면
            해당 Agent에 대한 Global↔Local 세션 매핑을 Redis에 등록
    """,
)
async def update_session_state(
    global_session_key: str,
    request: SessionPatchRequest,
    background_tasks: BackgroundTasks,
    service: SessionService = Depends(get_session_service),
):
    """
    세션 상태 업데이트 API

    - 세션 상태 전이 (Policy 검증 포함)
    - SubAgent 상태 업데이트
    """
    # global_session_key는 path에서도 받고 body에도 있어야 하므로 검증
    if request.global_session_key != global_session_key:
        logger.warning(f"Session key mismatch: path={global_session_key}, body={request.global_session_key}")
        raise HTTPException(status_code=400, detail="global_session_key mismatch")

    logger.info(f"Updating session state: global_session_key={global_session_key}, state={request.session_state}")
    try:
        result = await service.patch_session_state(request, background_tasks)
        logger.info(f"Session state updated: global_session_key={global_session_key}, status={result.status}")
        return result
    except Exception as e:
        logger.error(f"Failed to update session state: global_session_key={global_session_key}, error={e}", exc_info=True)
        raise


# ============ 세션 종료 ============


@router.delete(
    "/{global_session_key}",
    response_model=SessionCloseResponse,
    summary="세션 종료 (내부 서비스용)",
    description="""
    필수 경로 변수:
    - global_session_key: 종료할 세션 키

    선택 쿼리 파라미터:
    - close_reason: 종료 사유 (user_exit, timeout 등)

    주요 응답 필드:
    - status: 처리 결과 (success)
    - closed_at: 세션 종료 시각
    - archived_conversation_id: 세션 기준 아카이브 ID (arch_{global_session_key})
    """,
)
async def close_session_by_key(
    global_session_key: str,
    close_reason: str | None = Query(None, description="종료 사유 (옵션)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: SessionService = Depends(get_session_service),
):
    """
    세션 종료 API (Master Agent 전용, global_session_key 경로 사용)
    """
    logger.info(f"Closing session: global_session_key={global_session_key}, reason={close_reason}")
    try:
        request = SessionCloseRequest(
            global_session_key=global_session_key,
            close_reason=close_reason,
        )
        result = await service.close_session(request, background_tasks)
        logger.info(f"Session closed: global_session_key={global_session_key}")
        return result
    except Exception as e:
        logger.error(f"Failed to close session: global_session_key={global_session_key}, error={e}", exc_info=True)
        raise


@router.delete(
    "",
    response_model=SessionCloseResponse,
    summary="세션 종료 (토큰 기반)",
    description="""
    요청:
    - 헤더: Authorization: Bearer <access_token> 또는 쿠키의 access_token

    선택 쿼리 파라미터:
    - close_reason: 종료 사유 (user_exit, timeout 등)

    주요 응답 필드:
    - status: 처리 결과 (success)
    - closed_at: 세션 종료 시각
    - archived_conversation_id: 세션 기준 아카이브 ID
    """,
)
async def close_session(
    request: Request,
    close_reason: str | None = Query(None, description="종료 사유 (옵션)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    service: SessionService = Depends(get_session_service),
):
    """
    세션 종료 API (토큰 기반)

    - Client: 사용자가 앱 종료 시 호출
    """
    token = extract_token_from_request(request)
    if not token:
        logger.warning("Close session request without access token")
        raise HTTPException(status_code=401, detail="Access token required")

    try:
        result = await service.auth_service.close_session_by_token(token, close_reason)
        logger.info(f"Session closed by token: reason={close_reason}")
        return result
    except Exception as e:
        logger.error(f"Failed to close session by token: error={e}", exc_info=True)
        raise


# ============ 실시간 API 연동 결과 저장 ============


@router.post(
    "/{global_session_key}/api-results",
    response_model=TurnResponse,
    status_code=201,
    summary="실시간 API 연동 결과 저장",
    description="""
    DBS 등 외부 실시간 API 호출 결과를
    global_session_key, turn_id 기반으로 세션 컨텍스트에 저장

    필수 경로 변수:
    - global_session_key: 세션 키

    필수 요청 필드:
    - global_session_key
    - turn_id: 이 호출에 대응하는 턴 ID

    선택 요청 필드(SOL 스펙 기준, 상황에 따라 생략 가능):
    - agent: 호출한 업무 Agent ID
    - transactionPayload: 요청 Payload 배열 (각 항목에 trxCd, dataBody 포함 가능)
    - globId, requestId: SOL 트랜잭션 식별자
    - result, resultCode, resultMsg: SOL 처리 결과 코드/메시지
    - transactionResult: 응답 Payload 배열 (각 항목에 trxCd, responseData 포함 가능)

    주요 응답 필드:
    - turn_id: 저장된 턴 ID (요청의 turnId)
    - global_session_key: 세션 키 (최상위 레벨에 명시적 포함)
    - timestamp: 서버 기준 저장 시각
    - metadata.sol_api: SOL 요청/응답 전체가 들어있는 메타데이터 블록 (내부에 global_session_key, turn_id 포함)
    """,
)
async def save_api_result(
    global_session_key: str,
    request: SolApiResultRequest,
    service: SessionService = Depends(get_session_service),
):
    """실시간 API 연동 결과를 턴 메타데이터로 저장한다."""

    logger.info(f"Saving API result: global_session_key={global_session_key}, turn_id={request.turn_id}, agent={request.agent_id}")

    # 경로 변수와 요청 body의 global_session_key 일치 확인
    if request.global_session_key != global_session_key:
        logger.warning(f"API result key mismatch: path={global_session_key}, body={request.global_session_key}")
        raise HTTPException(status_code=400, detail="global_session_key mismatch")

    try:
        # 1) 세션 조회
        session = await service.session_repo.get(global_session_key)
        if not session:
            logger.warning(f"Session not found for API result: global_session_key={global_session_key}")
            raise HTTPException(status_code=404, detail=f"Session not found: {global_session_key}")

        # 2) SOL API 요청/응답 메타데이터 구성 (SOL 스펙 필드명을 그대로 유지)
        request_payloads = [p.model_dump(by_alias=True) for p in request.transaction_payload] if request.transaction_payload else []
        response_results = [r.model_dump(by_alias=True) for r in request.transaction_result] if request.transaction_result else []

        sol_metadata: dict[str, Any] = {
            "global_session_key": request.global_session_key,
            "turn_id": request.turn_id,
        }

        if request.agent_id is not None:
            sol_metadata["agent"] = request.agent_id

        # 요청/응답 블록은 존재하는 값만 포함하여 구성
        request_block: dict[str, Any] = {}
        if request_payloads:
            request_block["transactionPayload"] = request_payloads

        response_block: dict[str, Any] = {}
        if request.glob_id is not None:
            response_block["globId"] = request.glob_id
        if request.request_id is not None:
            response_block["requestId"] = request.request_id
        if request.result is not None:
            response_block["result"] = request.result
        if request.result_code is not None:
            response_block["resultCode"] = request.result_code
        if request.result_msg is not None:
            response_block["resultMsg"] = request.result_msg
        if response_results:
            response_block["transactionResult"] = response_results

        if request_block:
            sol_metadata["request"] = request_block
        if response_block:
            sol_metadata["response"] = response_block

        # 3) 턴 메타데이터로 저장 (Redis에 즉시 저장)
        now = datetime.now(UTC).isoformat()
        turn_data = {
            "turn_id": request.turn_id,
            "global_session_key": request.global_session_key,
            "timestamp": now,
            "metadata": {"sol_api": sol_metadata},
        }

        # Redis에 즉시 저장 (SessionRepository의 Turn 메서드 사용)
        await service.session_repo.add_turn(global_session_key, turn_data)

        logger.info(f"API result saved: global_session_key={global_session_key}, turn_id={request.turn_id}")
        return TurnResponse(**turn_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to save API result: global_session_key={global_session_key}, turn_id={request.turn_id}, error={e}", exc_info=True
        )
        raise


# ============ 세션 전체 정보 조회 ============


@router.get(
    "/{global_session_key}/full",
    response_model=SessionFullResponse,
    summary="세션 전체 정보 조회 (세션 + 턴 목록)",
    description="""
    세션 메타데이터와 해당 세션의 모든 턴 메타데이터를 한 번에 조회

    필수 경로 변수:
    - global_session_key: 조회할 세션 키

    주요 응답 필드:
    - session: 세션 메타데이터 전체 (GET /api/v1/sessions/{key} 와 동일한 구조)
    - turns: 턴 메타데이터 목록 (POST /api/v1/sessions/{key}/api-results 로 저장된 데이터)
    - total_turns: 전체 턴 수

    사용 사례:
    - 관리자/Portal이 특정 세션의 전체 이력 조회
    - 디버깅/모니터링 시 세션 상태 + SOL API 호출 이력 확인
    """,
)
async def get_session_full(
    global_session_key: str,
    service: SessionService = Depends(get_session_service),
):
    """세션 메타데이터 + 모든 턴 메타데이터를 한 번에 조회"""

    logger.info(f"Getting full session: global_session_key={global_session_key}")
    try:
        # 1) 세션 조회 (SessionResolveResponse)
        session_response = await service.resolve_session(SessionResolveRequest(global_session_key=global_session_key))

        # 2) 세션의 턴 목록 조회 (resolve_session에서 이미 세션 존재 확인됨)
        turns = await service.session_repo.get_turns(global_session_key)

        logger.info(f"Full session retrieved: global_session_key={global_session_key}, total_turns={len(turns)}")
        return SessionFullResponse(
            session=session_response.model_dump(),
            turns=turns,
            total_turns=len(turns),
        )
    except Exception as e:
        logger.error(f"Failed to get full session: global_session_key={global_session_key}, error={e}", exc_info=True)
        raise


# ============ 실시간 프로파일 업데이트 ============


@router.post(
    "/realtime-personal-context",
    response_model=RealtimePersonalContextResponse,
    status_code=200,
    summary="실시간 프로파일 업데이트",
    description="""
        Access Token 기반으로 실시간 프로파일을 Redis에 저장합니다.
    
        - 인증: Authorization 헤더의 Access Token에서 global_session_key 추출
        - 요청 필드: profile_data (redis_data.md 구조 그대로 사용)
        - 선택 필드: profile_data.responseData.cusnoN10 (있으면 CUSNO 기준으로 배치/실시간 프로파일 저장)
    """,
)
async def update_realtime_personal_context(
    request: Request,
    body: RealtimePersonalContextRequest,
    service: SessionService = Depends(get_session_service),
):
    """실시간 프로파일 업데이트 API"""
    token = extract_token_from_request(request)
    if not token:
        logger.warning("Realtime profile update request without access token")
        raise HTTPException(status_code=401, detail="Access token required")

    # 토큰에서 global_session_key 추출
    global_session_key = await get_global_session_key_from_token(token)

    profile_data = body.profile_data
    response_data = profile_data.get("responseData") or {}
    cusno_raw = response_data.get("cusnoN10")

    cusno = str(cusno_raw).strip() if cusno_raw else None
    # if not cusno:
    #     cusno = None

    cusno_display = cusno if cusno else "(no cusnoN10)"
    logger.info(f"Updating realtime profile: global_session_key={global_session_key}, cusno={cusno_display}")

    try:
        result = await service.profile_service.update_realtime_personal_context(
            global_session_key,
            body,
        )
        logger.info(
            "Realtime profile updated: global_session_key=%s, cusno=%s",
            global_session_key,
            cusno,
        )
        return result
    except Exception as e:
        logger.error(
            "Failed to update realtime profile: global_session_key=%s, cusno=%s, error=%s",
            global_session_key,
            cusno,
            e,
            exc_info=True,
        )
        raise
