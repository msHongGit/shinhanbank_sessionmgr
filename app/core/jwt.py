"""JWT 토큰 생성 및 검증 유틸리티"""

from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError

from app.config import (
    JWT_ACCESS_TOKEN_EXPIRE_SECONDS,
    JWT_REFRESH_TOKEN_EXPIRE_SECONDS,
    JWT_SECRET_KEY,
)


def create_access_token(jti: str, user_id: str, secret_key: str) -> str:
    """Access Token 생성

    Args:
        jti: JWT ID (UUID)
        user_id: 사용자 ID
        secret_key: JWT Secret Key

    Returns:
        Access Token (JWT 문자열)
    """
    expire = datetime.now(UTC) + timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRE_SECONDS)
    payload = {
        "jti": jti,
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def create_refresh_token(jti: str, user_id: str, secret_key: str) -> str:
    """Refresh Token 생성

    Args:
        jti: JWT ID (UUID)
        user_id: 사용자 ID
        secret_key: JWT Secret Key

    Returns:
        Refresh Token (JWT 문자열)
    """
    expire = datetime.now(UTC) + timedelta(seconds=JWT_REFRESH_TOKEN_EXPIRE_SECONDS)
    payload = {
        "jti": jti,
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_token(token: str, secret_key: str) -> dict:
    """토큰 검증

    Args:
        token: JWT 토큰 문자열
        secret_key: JWT Secret Key

    Returns:
        토큰 Payload (dict)

    Raises:
        ValueError: 토큰이 만료되었거나 유효하지 않은 경우
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except ExpiredSignatureError:
        raise ValueError("Token has expired") from None
    except DecodeError:
        raise ValueError("Invalid token format") from None
    except InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}") from e


def extract_jti_from_token(token: str, secret_key: str) -> str | None:
    """토큰에서 jti 추출

    Args:
        token: JWT 토큰 문자열
        secret_key: JWT Secret Key

    Returns:
        jti (UUID 문자열) 또는 None
    """
    try:
        payload = verify_token(token, secret_key)
        return payload.get("jti")
    except ValueError:
        return None
