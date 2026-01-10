"""Session Manager - Contexts API Router.

Sprint 3+: Context CRUD/조회 API 제거,
session_id, turn_id 기반 실시간 API 연동 결과 저장 전용.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.sessions import get_session_service
from app.repositories import ContextRepositoryInterface, RedisContextRepository
from app.schemas.contexts import SolApiResultRequest, TurnResponse
from app.services.session_service import SessionService

router = APIRouter(prefix="/contexts", tags=["Contexts"])


def get_context_repo() -> ContextRepositoryInterface:
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
    repo: ContextRepositoryInterface = Depends(get_context_repo),
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

    # 3) 턴 메타데이터로 저장 (RedisContextRepository)
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

    repo.add_turn(context_id, turn_data)

    return TurnResponse(**turn_data)
