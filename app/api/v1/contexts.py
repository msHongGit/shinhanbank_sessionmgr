"""Session Manager - Contexts API Router.

Sprint 3+: Context CRUD/조회 API 제거,
session_id, turn_id 기반 실시간 API 연동 결과 저장 전용.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.v1.sessions import get_session_service
from app.db.mariadb import SessionLocal
from app.repositories import RedisContextRepository
from app.repositories.mariadb_context_repository import MariaDBContextRepository
from app.schemas.common import SessionResolveRequest
from app.schemas.contexts import SessionFullResponse, SolApiResultRequest, TurnResponse
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contexts", tags=["Contexts"])


def get_context_repo():
    """ContextRepository 의존성 - Redis 사용 (실시간 턴 메타데이터 관리)."""

    return RedisContextRepository()


@router.post(
    "/turn-results",
    response_model=TurnResponse,
    status_code=201,
    summary="실시간 API 연동 결과 저장",
    description="""
    DBS 등 외부 실시간 API 호출 결과를
    sessionId, turnId 기반으로 세션 컨텍스트에 저장합니다.

    필수 요청 필드:
    - sessionId: Session Manager의 global_session_key 와 동일한 세션 ID
    - turnId: 이 호출에 대응하는 턴 ID

    선택 요청 필드(SOL 스펙 기준, 상황에 따라 생략 가능):
    - agent: 호출한 업무 Agent ID (다른 API의 agent_id 와 동일 의미)
    - transactionPayload: 요청 Payload 배열 (각 항목에 trxCd, dataBody 포함 가능)
    - globId, requestId: SOL 트랜잭션 식별자
    - result, resultCode, resultMsg: SOL 처리 결과 코드/메시지
    - transactionResult: 응답 Payload 배열 (각 항목에 trxCd, responseData 포함 가능)

    주요 응답 필드:
    - turn_id: 저장된 턴 ID (요청의 turnId)
    - timestamp: 서버 기준 저장 시각
    - metadata.sol_api: SOL 요청/응답 전체가 들어있는 메타데이터 블록
    """,
)
async def save_sol_api_result(
    request: SolApiResultRequest,
    background_tasks: BackgroundTasks,
    repo=Depends(get_context_repo),
    service: SessionService = Depends(get_session_service),
):
    """실시간 API 연동 결과를 컨텍스트 턴 메타데이터로 저장한다."""

    # 1) 세션 조회 (sessionId -> context_id 매핑)
    session = service.session_repo.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")

    context_id = session.get("context_id")
    if not context_id:
        raise HTTPException(status_code=400, detail="Context ID not found in session")

    global_session_key = request.session_id

    # 2) SOL API 요청/응답 메타데이터 구성 (SOL 스펙 필드명을 그대로 유지)
    request_payloads = [p.model_dump(by_alias=True) for p in request.transaction_payload] if request.transaction_payload else []
    response_results = [r.model_dump(by_alias=True) for r in request.transaction_result] if request.transaction_result else []

    sol_metadata: dict[str, Any] = {
        "sessionId": request.session_id,
        "turnId": request.turn_id,
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
        "timestamp": now,
        "metadata": {"sol_api": sol_metadata},
    }

    # context_id가 존재해야만 저장
    context = repo.get(context_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"Context not found: {context_id}")

    # Redis에 즉시 저장
    repo.add_turn(context_id, turn_data)

    # MariaDB에 비동기 저장
    background_tasks.add_task(
        _save_turn_to_mariadb,
        turn_id=request.turn_id,
        context_id=context_id,
        global_session_key=global_session_key,
        agent_id=request.agent_id,
        metadata={"sol_api": sol_metadata},
    )

    return TurnResponse(**turn_data)


def _save_turn_to_mariadb(
    turn_id: str,
    context_id: str,
    global_session_key: str,
    agent_id: str | None,
    metadata: dict[str, Any],
) -> None:
    """턴 데이터를 MariaDB에 비동기 저장

    BackgroundTasks에서 호출되어 API 응답 후 실행된다.
    MariaDB 연결이 없거나 에러가 발생해도 로깅만 하고 예외를 발생시키지 않는다.
    """
    if SessionLocal is None:
        logger.debug(f"MariaDB not configured, skipping turn save for {turn_id}")
        return

    try:
        db = SessionLocal()
        try:
            mariadb_repo = MariaDBContextRepository(db)

            # Context에서 turn_count 조회하여 turn_number 결정
            context = mariadb_repo.get_context(context_id)
            if context:
                turn_number = context.turn_count + 1
            else:
                # Context가 없으면 생성
                context = mariadb_repo.create_context(context_id, global_session_key)
                turn_number = 1

            # Turn 저장
            mariadb_repo.create_turn(
                turn_id=turn_id,
                context_id=context_id,
                global_session_key=global_session_key,
                turn_number=turn_number,
                role="assistant",  # SOL API 결과는 assistant 역할
                agent_id=agent_id,
                agent_type=None,  # SOL API 결과에는 agent_type이 없을 수 있음
                metadata=metadata,
            )

            # turn_count 증가
            mariadb_repo.increment_turn_count(context_id)

            logger.debug(f"Turn saved to MariaDB: {turn_id}")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to save turn to MariaDB: {turn_id}, error: {e}", exc_info=True)


@router.get(
    "/sessions/{global_session_key}/full",
    response_model=SessionFullResponse,
    summary="세션 전체 정보 조회 (세션 + 턴 목록)",
    description="""
    세션 메타데이터와 해당 세션의 모든 턴 메타데이터를 한 번에 조회합니다.

    필수 경로 변수:
    - global_session_key: 조회할 세션 키

    주요 응답 필드:
    - session: 세션 메타데이터 전체 (GET /api/v1/sessions/{key} 와 동일한 구조)
    - turns: 턴 메타데이터 목록 (POST /api/v1/contexts/turn-results 로 저장된 데이터)
    - total_turns: 전체 턴 수

    사용 사례:
    - 관리자/Portal이 특정 세션의 전체 이력 조회
    - 디버깅/모니터링 시 세션 상태 + SOL API 호출 이력 확인
    """,
)
async def get_session_full(
    global_session_key: str,
    repo=Depends(get_context_repo),
    service: SessionService = Depends(get_session_service),
):
    """세션 메타데이터 + 모든 턴 메타데이터를 한 번에 조회합니다."""

    # 1) 세션 조회 (SessionResolveResponse)
    session_response = service.resolve_session(SessionResolveRequest(global_session_key=global_session_key))

    # 2) Context ID로 턴 목록 조회
    session = service.session_repo.get(global_session_key)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {global_session_key}")

    context_id = session.get("context_id")

    turns = []
    if context_id:
        context = repo.get(context_id)
        if context:
            turns = repo.get_turns(context_id)

    return SessionFullResponse(
        session=session_response.model_dump(),
        turns=turns,
        total_turns=len(turns),
    )
