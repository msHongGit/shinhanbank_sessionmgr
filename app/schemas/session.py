"""
Session Manager - Session Schemas (Pydantic Models)
"""
from datetime import datetime
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


# ============ Common ============

class SessionKey(BaseModel):
    """세션 키 구조"""
    scope: Literal["global", "local"] = Field(..., description="세션 키 범위")
    key: str = Field(..., description="세션 키 값")


class LastEvent(BaseModel):
    """마지막 이벤트 정보"""
    event_type: str = Field(..., description="이벤트 타입")
    task_id: Optional[str] = Field(None, description="Task ID")
    subagent_id: Optional[str] = Field(None, description="SubAgent ID")
    updated_at: datetime = Field(..., description="업데이트 시각")


# ============ CreateInitialSession ============

class SessionCreateRequest(BaseModel):
    """세션 생성 요청 (AGW-SM-01)"""
    user_id: str = Field(..., description="사용자 ID", example="user_1084756")
    channel: str = Field(..., description="채널", example="mobile")
    session_key: SessionKey = Field(..., description="세션 키")
    request_id: str = Field(..., description="요청 추적 ID", example="req_20250316_001")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_1084756",
                "channel": "mobile",
                "session_key": {"scope": "global", "key": "user_1084756_mobile"},
                "request_id": "req_20250316_001"
            }
        }


class SessionCreateResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str = Field(..., description="세션 ID")
    conversation_id: str = Field(..., description="대화 ID")
    session_state: Literal["start", "talk", "end"] = Field(..., description="세션 상태")
    expires_at: datetime = Field(..., description="만료 시각")
    policy_profile_ref: Optional[str] = Field(None, description="정책 프로파일 참조")


# ============ ResolveSession ============

class SessionResolveRequest(BaseModel):
    """세션 조회 요청 (MA-SM-01)"""
    session_key: SessionKey = Field(..., description="세션 키")
    channel: str = Field(..., description="채널")
    conversation_id: Optional[str] = Field(None, description="대화 ID")
    user_id_ref: Optional[str] = Field(None, description="사용자 ID 참조")


class SessionResolveResponse(BaseModel):
    """세션 조회 응답"""
    session_id: str = Field(..., description="세션 ID")
    conversation_id: str = Field(..., description="대화 ID")
    session_state: Literal["start", "talk", "end"] = Field(..., description="세션 상태")
    is_first_call: bool = Field(..., description="최초 호출 여부")
    task_queue_status: Literal["null", "notnull"] = Field(..., description="Task Queue 상태")
    subagent_status: Literal["undefined", "continue", "end"] = Field(..., description="SubAgent 상태")
    last_event: Optional[LastEvent] = Field(None, description="마지막 이벤트")
    customer_profile_ref: Optional[str] = Field(None, description="고객 프로파일 참조")


# ============ PatchSessionState ============

class StatePatch(BaseModel):
    """세션 상태 패치 데이터"""
    step: Optional[str] = Field(None, description="현재 스텝")
    slots: Optional[Dict[str, Any]] = Field(None, description="슬롯 데이터")
    flags: Optional[Dict[str, bool]] = Field(None, description="플래그")
    action_owner: Optional[str] = Field(None, description="액션 소유자")
    reference_information: Optional[Dict[str, Any]] = Field(None, description="참조 정보")
    cushion_message: Optional[str] = Field(None, description="쿠션 메시지")
    subagent_status: Optional[Literal["undefined", "continue", "end"]] = Field(None, description="SubAgent 상태")


class SessionPatchRequest(BaseModel):
    """세션 상태 업데이트 요청 (MA-SM-02)"""
    conversation_id: str = Field(..., description="대화 ID")
    turn_id: str = Field(..., description="턴 ID")
    session_state: Literal["start", "talk", "end"] = Field(..., description="세션 상태")
    state_patch: StatePatch = Field(..., description="상태 패치 데이터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv_20250316_0019_001",
                "turn_id": "turn_003",
                "session_state": "talk",
                "state_patch": {
                    "subagent_status": "continue",
                    "action_owner": "master-agent",
                    "reference_information": {"intent": "이체내역_확인"},
                    "cushion_message": "확인 중입니다."
                }
            }
        }


class SessionPatchResponse(BaseModel):
    """세션 상태 업데이트 응답"""
    status: Literal["success", "error"] = Field(..., description="처리 상태")
    updated_at: datetime = Field(..., description="업데이트 시각")


# ============ CloseSession ============

class SessionCloseRequest(BaseModel):
    """세션 종료 요청 (MA-SM-03)"""
    conversation_id: str = Field(..., description="대화 ID")
    close_reason: Literal["user_exit", "timeout", "transfer"] = Field(..., description="종료 사유")
    final_summary: Optional[str] = Field(None, description="최종 요약")


class SessionCloseResponse(BaseModel):
    """세션 종료 응답"""
    status: Literal["success", "error"] = Field(..., description="처리 상태")
    closed_at: datetime = Field(..., description="종료 시각")
    archived_conversation_id: str = Field(..., description="아카이브된 대화 ID")
