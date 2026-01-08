"""Session Manager - Contexts API Router.

Sprint 3: Context & Turn 엔드포인트
"""

from fastapi import APIRouter, Depends

from app.repositories import ContextRepositoryInterface, MariaDBContextRepository
from app.schemas.contexts import (
    ContextCreate,
    ContextResponse,
    ContextUpdate,
    TurnCreate,
    TurnCreateWithAPI,
    TurnListResponse,
    TurnResponse,
)

router = APIRouter(prefix="/contexts", tags=["Contexts"])


# ============ 의존성 ============


def get_context_repo() -> ContextRepositoryInterface:
    """ContextRepository 의존성 - MariaDB 사용"""
    return MariaDBContextRepository()


# ============ Context CRUD ============


@router.post(
    "",
    response_model=ContextResponse,
    status_code=201,
    summary="컨텍스트 생성",
    description="""
    새로운 컨텍스트를 생성합니다.
    - 세션 생성 시 자동으로 context_id가 발급됨
    - 컨텍스트는 대화 상태, 슬롯, 엔티티 등을 추적
    """,
)
async def create_context(
    request: ContextCreate,
    repo: ContextRepositoryInterface = Depends(get_context_repo),
):
    """컨텍스트 생성 (Mock DB 저장)"""
    context = repo.create(request.context_id, request.global_session_key, request.user_id)
    return ContextResponse(
        context_id=context["context_id"],
        global_session_key=context["global_session_key"],
        user_id=context["user_id"],
        created_at=context["created_at"],
        last_updated_at=context["last_updated_at"],
    )


@router.get(
    "/{context_id}",
    response_model=ContextResponse,
    summary="컨텍스트 조회",
    description="""
    컨텍스트 정보를 조회합니다.
    - 현재 intent, slots, entities 반환
    - turn_count 포함
    """,
)
async def get_context(
    context_id: str,
    repo: ContextRepositoryInterface = Depends(get_context_repo),
):
    """컨텍스트 조회"""
    context = repo.get(context_id)
    if not context:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Context not found: {context_id}")

    return ContextResponse(
        context_id=context["context_id"],
        global_session_key=context["global_session_key"],
        user_id=context["user_id"],
        created_at=context["created_at"],
        last_updated_at=context["last_updated_at"],
    )


@router.patch(
    "/{context_id}",
    response_model=ContextResponse,
    summary="컨텍스트 업데이트",
    description="""
    컨텍스트를 업데이트합니다.
    - intent, slots, entities 업데이트
    - 메타데이터 추가 가능
    """,
)
async def update_context(
    context_id: str,
    request: ContextUpdate,
    repo: ContextRepositoryInterface = Depends(get_context_repo),
):
    """컨텍스트 업데이트"""
    context = repo.get(context_id)
    if not context:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Context not found: {context_id}")

    # summary 업데이트 (간단한 구현)
    if request.summary:
        context["summary"] = request.summary

    return ContextResponse(
        context_id=context["context_id"],
        global_session_key=context["global_session_key"],
        user_id=context["user_id"],
        created_at=context["created_at"],
        last_updated_at=context["last_updated_at"],
        summary=context.get("summary"),
    )


# ============================================================================
# Turn API
# ============================================================================


@router.post(
    "/{context_id}/turns",
    response_model=TurnResponse,
    status_code=201,
    summary="턴 생성",
    description="""
    대화 턴 메타데이터를 생성합니다.
    - 대화 텍스트는 저장하지 않음 (메타데이터만)
    - API 호출 결과를 metadata에 포함 가능
    """,
)
async def create_turn(
    context_id: str,
    request: TurnCreate | TurnCreateWithAPI,
    repo: ContextRepositoryInterface = Depends(get_context_repo),
):
    """턴 생성 (Mock DB 저장)"""
    # Context 존재 확인
    context = repo.get(context_id)
    if not context:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Context not found: {context_id}")

    # 턴 데이터 생성 (텍스트 제외, 메타데이터 전용)
    turn_data = {
        "turn_id": request.turn_id,
        "timestamp": request.timestamp,
    }

    # TurnCreate / TurnCreateWithAPI 공통 metadata 처리
    if hasattr(request, "metadata") and request.metadata:
        turn_data["metadata"] = request.metadata

    repo.add_turn(context_id, turn_data)

    return TurnResponse(**turn_data)


@router.get(
    "/{context_id}/turns",
    response_model=TurnListResponse,
    summary="턴 목록 조회",
    description="""
    컨텍스트의 턴 목록을 조회합니다.
    - 턴 메타데이터 목록 반환
    - limit으로 개수 제한 가능
    """,
)
async def list_turns(
    context_id: str,
    repo: ContextRepositoryInterface = Depends(get_context_repo),
):
    """턴 목록 조회"""
    turns = repo.get_turns(context_id)

    return TurnListResponse(
        context_id=context_id,
        turns=[TurnResponse(**turn) for turn in turns],
        total_count=len(turns),
    )


@router.get(
    "/{context_id}/turns/{turn_id}",
    response_model=TurnResponse,
    summary="턴 조회",
    description="""
    특정 턴의 메타데이터를 조회합니다.
    """,
)
async def get_turn(
    context_id: str,
    turn_id: str,
    repo: ContextRepositoryInterface = Depends(get_context_repo),
):
    """특정 턴 조회"""
    turns = repo.get_turns(context_id)

    for turn in turns:
        if turn.get("turn_id") == turn_id:
            return TurnResponse(**turn)

    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail=f"Turn not found: {turn_id}")
