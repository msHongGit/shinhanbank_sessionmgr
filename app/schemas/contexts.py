"""Context 및 Turn 관련 스키마.

Sprint 3 이후: Context CRUD/조회 API는 제거하고,
session_id, turn_id 기반 실시간 API 연동 결과 저장에만 사용한다.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TurnResponse(BaseModel):
    """턴 응답 (메타데이터 전용)"""

    turn_id: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SolDBSTransactionPayload(BaseModel):
    """DBS 트랜잭션 요청 페이로드 (trxCd, dataBody)."""

    trx_cd: str = Field(..., alias="trxCd")
    data_body: str | dict[str, Any] = Field(..., alias="dataBody")

    model_config = ConfigDict(populate_by_name=True)


class SolDBSTransactionResult(BaseModel):
    """DBS 트랜잭션 응답 결과 (trxCd, responseData)."""

    trx_cd: str = Field(..., alias="trxCd")
    response_data: str | dict[str, Any] = Field(..., alias="responseData")

    model_config = ConfigDict(populate_by_name=True)


class SolApiResultRequest(BaseModel):
    """실시간 API 연동 결과 저장 요청.

    - sol_api.md 의 `/api/v1/sol/transaction`(RequestParam)
      + `/api/v1/sol/transaction/result`(DBSTrxResponse) 구조를 합친다.
    - 필드명은 SOL 측 스펙에 맞춰 camelCase alias를 사용한다.
    """

    # 필수 값
    session_id: str = Field(..., alias="sessionId", description="세션 ID (Session Manager global_session_key)")
    turn_id: str = Field(..., alias="turnId", description="턴 ID")

    # 선택 값 (SOL 측에서 상황에 따라 포함될 수도, 생략될 수도 있음)
    agent_id: str | None = Field(
        None,
        alias="agent",
        description="호출한 업무 Agent ID (다른 API의 agent_id 와 동일 의미)",
    )
    transaction_payload: list[SolDBSTransactionPayload] | None = Field(
        None,
        alias="transactionPayload",
        description="요청 시 사용된 DBS 전문 페이로드 목록 (없으면 생략 가능)",
    )

    glob_id: str | None = Field(None, alias="globId", description="GLOBALID (BXM 이벤트 ID, 옵션)")
    request_id: str | None = Field(None, alias="requestId", description="요청 식별자 (옵션)")
    result: str | None = Field(None, description="성공/실패 SUCCESS/FAIL (옵션)")
    result_code: str | None = Field(None, alias="resultCode", description="실패 코드 (옵션)")
    result_msg: str | None = Field(None, alias="resultMsg", description="실패 메시지 (옵션)")
    transaction_result: list[SolDBSTransactionResult] | None = Field(
        None,
        alias="transactionResult",
        description="DBS 전문 응답 결과 목록 (없으면 생략 가능)",
    )

    model_config = ConfigDict(populate_by_name=True)


class SessionFullResponse(BaseModel):
    """세션 전체 정보 응답 (세션 메타데이터 + 턴 목록)."""

    session: dict[str, Any] = Field(..., description="세션 메타데이터 (SessionResolveResponse 구조)")
    turns: list[dict[str, Any]] = Field(default_factory=list, description="턴 메타데이터 목록")
    total_turns: int = Field(..., description="전체 턴 수")
