"""JWT 인증 의존성 및 헬퍼"""

from fastapi import Depends, HTTPException, Request

from app.config import JWT_SECRET_KEY
from app.core.jwt import verify_token
from app.db.redis import get_redis_client


def extract_token_from_request(request: Request) -> str | None:
    """요청에서 Access Token 추출 (헤더 우선, 없으면 쿠키)

    Args:
        request: FastAPI Request 객체

    Returns:
        Access Token 문자열 또는 None
    """
    # 헤더에서 추출
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    # 쿠키에서 추출
    access_token = request.cookies.get("access_token")
    if access_token:
        return access_token

    return None


async def get_global_session_key_from_token(token: str) -> str:
    """토큰에서 global_session_key 조회

    Args:
        token: Access Token 문자열

    Returns:
        global_session_key

    Raises:
        HTTPException: 토큰이 유효하지 않거나 만료된 경우
    """
    # 1. 토큰 검증 및 jti 추출
    try:
        payload = verify_token(token, JWT_SECRET_KEY)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Invalid token: jti not found")

    # 2. Redis에서 global_session_key 조회
    from app.db.redis import RedisHelper

    redis_client = get_redis_client()
    helper = RedisHelper(redis_client)
    global_session_key = await helper.get_global_session_key_by_jti(jti)

    if not global_session_key:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    return global_session_key


def verify_jwt_token(request: Request) -> dict:
    """JWT 토큰 검증 의존성

    FastAPI Dependency로 사용하여 토큰 검증 및 global_session_key 조회

    Args:
        request: FastAPI Request 객체

    Returns:
        토큰 정보 및 global_session_key를 포함한 dict

    Raises:
        HTTPException: 토큰이 없거나 유효하지 않은 경우
    """
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")

    # 토큰 검증
    try:
        payload = verify_token(token, JWT_SECRET_KEY)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e

    # 토큰 타입 확인
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # jti 추출 및 global_session_key 조회
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(status_code=401, detail="Invalid token: jti not found")

    redis_client = get_redis_client()
    global_session_key = redis_client.get(f"jti:{jti}")

    if not global_session_key:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    global_session_key = global_session_key if isinstance(global_session_key, str) else global_session_key.decode()

    return {
        "jti": jti,
        "user_id": payload.get("sub"),
        "global_session_key": global_session_key,
        "token": token,
    }
