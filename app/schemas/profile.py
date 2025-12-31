"""
Session Manager - Profile Schemas (Pydantic Models)
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============ GetCustomerProfile ============

class ProfileAttribute(BaseModel):
    """프로파일 속성"""
    key: str = Field(..., description="속성 키")
    value: str = Field(..., description="속성 값")
    source_system: str = Field(..., description="소스 시스템")
    valid_from: Optional[date] = Field(None, description="유효 시작일")
    valid_to: Optional[date] = Field(None, description="유효 종료일")


class ProfileGetRequest(BaseModel):
    """프로파일 조회 요청 (MA-SM-07)"""
    session_id: str = Field(..., description="세션 ID")
    user_id: str = Field(..., description="사용자 ID")
    attribute_keys: Optional[List[str]] = Field(None, description="조회할 속성 키 목록")


class ProfileGetResponse(BaseModel):
    """프로파일 조회 응답"""
    user_id: str = Field(..., description="사용자 ID")
    attributes: List[ProfileAttribute] = Field(..., description="속성 목록")
    computed_at: datetime = Field(..., description="계산 시각")


# ============ BatchUpsertCustomerProfiles ============

class BatchProfileAttribute(BaseModel):
    """배치 프로파일 속성"""
    attribute_key: str = Field(..., description="속성 키")
    attribute_value: str = Field(..., description="속성 값")
    valid_from: Optional[date] = Field(None, description="유효 시작일")
    valid_to: Optional[date] = Field(None, description="유효 종료일")


class BatchProfileRecord(BaseModel):
    """배치 프로파일 레코드"""
    user_id: str = Field(..., description="사용자 ID")
    attributes: List[BatchProfileAttribute] = Field(..., description="속성 목록")


class BatchProfileRequest(BaseModel):
    """배치 프로파일 요청 (VDB-SM-01)"""
    batch_id: str = Field(..., description="배치 ID")
    source_system: str = Field(..., description="소스 시스템")
    computed_at: datetime = Field(..., description="계산 시각")
    records: List[BatchProfileRecord] = Field(..., description="레코드 목록")
    
    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_20250316_001",
                "source_system": "vertica_db",
                "computed_at": "2025-03-16T00:00:00Z",
                "records": [
                    {
                        "user_id": "user_1084756",
                        "attributes": [
                            {
                                "attribute_key": "전세여부",
                                "attribute_value": "Y",
                                "valid_from": "2024-01-01",
                                "valid_to": "2025-12-31"
                            }
                        ]
                    }
                ]
            }
        }


class BatchProfileError(BaseModel):
    """배치 처리 에러"""
    user_id: str = Field(..., description="사용자 ID")
    error: str = Field(..., description="에러 메시지")


class BatchProfileResponse(BaseModel):
    """배치 프로파일 응답"""
    batch_id: str = Field(..., description="배치 ID")
    accepted: bool = Field(..., description="처리 성공 여부")
    processed_count: int = Field(..., description="처리된 레코드 수")
    failed_count: int = Field(..., description="실패한 레코드 수")
    errors: Optional[List[BatchProfileError]] = Field(None, description="에러 목록")
