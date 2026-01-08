"""
Session Manager - Authentication & Authorization
통합 인증 계층: API Key 기반 호출자 검증
"""

from enum import Enum

from fastapi import Header, HTTPException, status

from app.config import (
    AGW_API_KEY,
    CLIENT_API_KEY,
    ENABLE_API_KEY_AUTH,
    EXTERNAL_API_KEY,
    MA_API_KEY,
    PORTAL_API_KEY,
    VDB_API_KEY,
)


class APIKeyType(str, Enum):
    """API 호출자 타입"""

    AGW = "agw"
    MA = "ma"
    PORTAL = "portal"
    VDB = "vdb"
    CLIENT = "client"
    EXTERNAL = "external"  # Sprint 3: 외부 서비스 (DBS API 등)


# API Key 매핑
API_KEYS = {
    APIKeyType.AGW: AGW_API_KEY,
    APIKeyType.MA: MA_API_KEY,
    APIKeyType.PORTAL: PORTAL_API_KEY,
    APIKeyType.VDB: VDB_API_KEY,
    APIKeyType.CLIENT: CLIENT_API_KEY,
    APIKeyType.EXTERNAL: EXTERNAL_API_KEY,
}


def require_api_key(allowed_types: list[APIKeyType]):
    """
    API Key 검증 의존성

    Args:
        allowed_types: 허용할 호출자 타입 리스트

    Returns:
        검증된 호출자 타입

    Raises:
        HTTPException: API Key가 유효하지 않거나 권한이 없는 경우
    """

    async def _verify(x_api_key: str | None = Header(None, alias="X-API-Key")) -> APIKeyType:
        # API Key 인증 비활성화 모드 (테스트/로컬 개발용)
        if not ENABLE_API_KEY_AUTH:
            # 기본값으로 첫 번째 허용 타입 반환
            return allowed_types[0] if allowed_types else APIKeyType.CLIENT

        # API Key 검증
        if not x_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH001", "message": "API Key is required"},
            )

        # 허용된 타입 중 하나와 매칭되는지 확인
        for key_type in allowed_types:
            expected_key = API_KEYS.get(key_type)
            if expected_key and x_api_key == expected_key:
                return key_type

        # 권한 없음
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AUTH002", "message": "Invalid or unauthorized API Key"},
        )

    return _verify
