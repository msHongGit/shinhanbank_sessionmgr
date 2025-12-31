"""
Session Manager - Task Schemas (Pydantic Models)
"""
from datetime import datetime
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# ============ EnqueueTask ============

class TaskPayload(BaseModel):
    """Task 페이로드"""
    masked: bool = Field(True, description="마스킹 여부")
    data: Dict[str, Any] = Field(..., description="작업 데이터")


class TaskEnqueueRequest(BaseModel):
    """Task 적재 요청 (MA-SM-04)"""
    session_id: str = Field(..., description="세션 ID")
    conversation_id: str = Field(..., description="대화 ID")
    turn_id: str = Field(..., description="턴 ID")
    intent: str = Field(..., description="발화 의도")
    priority: int = Field(..., ge=1, le=10, description="우선순위 (1=highest)")
    session_state: Literal["start", "talk", "end"] = Field(..., description="세션 상태")
    task_payload: TaskPayload = Field(..., description="작업 페이로드")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_20250316_0019",
                "conversation_id": "conv_20250316_0019_001",
                "turn_id": "turn_003",
                "intent": "이체내역_확인",
                "priority": 1,
                "session_state": "talk",
                "task_payload": {
                    "masked": True,
                    "data": {
                        "query": "이전 내역을 확인하고 싶어요",
                        "skill": "계좌_거래_기록확인"
                    }
                }
            }
        }


class TaskEnqueueResponse(BaseModel):
    """Task 적재 응답"""
    status: Literal["accepted", "rejected"] = Field(..., description="처리 상태")
    task_id: str = Field(..., description="생성된 Task ID")


# ============ GetTaskStatus ============

class TaskStatusResponse(BaseModel):
    """Task 상태 조회 응답 (MA-SM-05)"""
    task_id: str = Field(..., description="Task ID")
    task_status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        ..., description="Task 상태"
    )
    progress: Optional[int] = Field(None, ge=0, le=100, description="진행률 (0-100)")
    updated_at: datetime = Field(..., description="마지막 업데이트 시각")


# ============ GetTaskResult ============

class TaskResultResponse(BaseModel):
    """Task 결과 조회 응답 (MA-SM-06)"""
    task_id: str = Field(..., description="Task ID")
    task_status: Literal["completed", "failed"] = Field(..., description="Task 상태")
    outcome: Literal["normal", "fallback", "continue"] = Field(..., description="결과 유형")
    response_text: Optional[str] = Field(None, description="응답 텍스트")
    result_payload: Optional[Dict[str, Any]] = Field(None, description="결과 데이터")


# ============ Task Queue Item (Internal) ============

class TaskQueueItem(BaseModel):
    """Task Queue 아이템 (Redis 저장용)"""
    task_id: str
    session_id: str
    conversation_id: str
    turn_id: str
    intent: str
    priority: int
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    task_payload: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
