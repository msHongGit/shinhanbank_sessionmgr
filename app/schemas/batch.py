"""
Session Manager - Batch Schemas (v3.0)
VDB → SM 배치 요청/응답 스키마
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ProfileAttribute

# ============ 프로파일 배치 업로드 ============

class BatchProfileRecord(BaseModel):
    """배치 프로파일 레코드"""
    user_id: str
    attributes: list[ProfileAttribute]
    segment: str | None = None


class BatchProfileRequest(BaseModel):
    """배치 프로파일 요청 (VDB → SM)"""
    batch_id: str = Field(..., description="배치 ID")
    source_system: str = Field(..., description="소스 시스템")
    computed_at: datetime = Field(..., description="계산 시각")
    records: list[BatchProfileRecord] = Field(..., description="레코드 목록")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "batch_id": "batch_20250316_001",
                "source_system": "crm",
                "computed_at": "2025-03-16T00:00:00Z",
                "records": [
                    {
                        "user_id": "user_001",
                        "attributes": [
                            {"key": "segment", "value": "VIP", "source_system": "crm"}
                        ],
                        "segment": "VIP"
                    }
                ]
            }
        }
    )


class BatchProfileError(BaseModel):
    """배치 처리 에러"""
    user_id: str
    error: str


class BatchProfileResponse(BaseModel):
    """배치 프로파일 응답"""
    batch_id: str
    accepted: bool
    processed_count: int
    failed_count: int
    errors: list[BatchProfileError] | None = None
