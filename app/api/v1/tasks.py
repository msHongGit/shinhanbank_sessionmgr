"""
Session Manager - Task Queue API Endpoints
"""
from fastapi import APIRouter, Depends

from app.schemas.task import (
    TaskEnqueueRequest,
    TaskEnqueueResponse,
    TaskStatusResponse,
    TaskResultResponse,
)
from app.services.task_service import TaskService
from app.api.deps import get_task_service, verify_api_key

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskEnqueueResponse,
    status_code=201,
    summary="Task 적재",
    description="Task Queue에 작업을 적재합니다. (MA-SM-04)"
)
async def enqueue_task(
    request: TaskEnqueueRequest,
    service: TaskService = Depends(get_task_service),
    api_key: str = Depends(verify_api_key),
):
    """
    Task 적재 API
    
    - **session_id**: 세션 ID
    - **intent**: 발화 의도
    - **priority**: 우선순위 (1=highest)
    - **task_payload**: 작업 페이로드 (마스킹)
    """
    return await service.enqueue_task(request)


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="Task 상태 조회",
    description="Task의 실행 상태를 조회합니다. (MA-SM-05)"
)
async def get_task_status(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    api_key: str = Depends(verify_api_key),
):
    """
    Task 상태 조회 API
    
    - **task_id**: 조회할 Task ID
    """
    return await service.get_task_status(task_id)


@router.get(
    "/{task_id}/result",
    response_model=TaskResultResponse,
    summary="Task 결과 조회",
    description="Task의 실행 결과를 조회합니다. (MA-SM-06)"
)
async def get_task_result(
    task_id: str,
    service: TaskService = Depends(get_task_service),
    api_key: str = Depends(verify_api_key),
):
    """
    Task 결과 조회 API
    
    - **task_id**: 조회할 Task ID
    - Task가 완료 상태일 때만 결과 반환
    """
    return await service.get_task_result(task_id)
