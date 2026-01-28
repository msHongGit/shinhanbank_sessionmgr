"""Session Manager - Authentication Service (Async).

인증 및 토큰 관리 서비스
"""

import logging
from uuid import uuid4

from fastapi import HTTPException

from app.config import JWT_SECRET_KEY, SESSION_CACHE_TTL
from app.core.jwt import create_access_token, create_refresh_token, verify_token
from app.core.jwt_auth import get_global_session_key_from_token
from app.db.redis import RedisHelper, get_redis_client
from app.schemas.common import (
    SessionCloseRequest,
    SessionCloseResponse,
    SessionPingResponse,
    SessionVerifyResponse,
    TokenRefreshResponse,
)

logger = logging.getLogger(__name__)


class AuthService:
    """인증 및 토큰 관리 서비스 (Async)"""

    def __init__(self, session_repo):
        """AuthService 초기화

        Args:
            session_repo: 세션 저장소 (RedisSessionRepository)
        """
        self.session_repo = session_repo

    async def create_tokens(self, user_id: str, global_session_key: str) -> dict[str, str]:
        """JWT 토큰 생성 및 JTI 매핑 저장

        Args:
            user_id: 사용자 ID
            global_session_key: Global 세션 키

        Returns:
            dict: access_token, refresh_token, jti 포함
        """
        # jti 생성
        jti = str(uuid4())

        # Redis에 jti -> global_session_key 매핑 저장
        redis_client = get_redis_client()
        helper = RedisHelper(redis_client)
        await helper.set_jti_mapping(jti, global_session_key, SESSION_CACHE_TTL)

        # Access Token 및 Refresh Token 발급
        access_token = create_access_token(jti, user_id, JWT_SECRET_KEY)
        refresh_token = create_refresh_token(jti, user_id, JWT_SECRET_KEY)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "jti": jti,
        }

    async def verify_token_and_get_session(self, token: str) -> SessionVerifyResponse:
        """토큰 검증 및 세션 정보 조회

        Args:
            token: Access Token 문자열

        Returns:
            SessionVerifyResponse: 세션 정보
        """
        from datetime import datetime

        # 1. 토큰 검증
        try:
            payload = verify_token(token, JWT_SECRET_KEY)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e

        # 2. 토큰 타입 확인
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        # 3. jti 추출 및 global_session_key 조회
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token: jti not found")

        redis_client = get_redis_client()
        helper = RedisHelper(redis_client)
        global_session_key = await helper.get_global_session_key_by_jti(jti)

        if not global_session_key:
            raise HTTPException(status_code=401, detail="Token expired or invalid")

        # 4. 세션 조회
        session = await self.session_repo.get(global_session_key)
        if not session:
            return SessionVerifyResponse(
                global_session_key=global_session_key,
                session_state="",
                is_alive=False,
                expires_at=None,
            )

        # 5. 만료 시각 파싱
        expires_at = None
        expires_raw = session.get("expires_at")
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None

        return SessionVerifyResponse(
            global_session_key=global_session_key,
            session_state=session.get("session_state", ""),
            is_alive=True,
            expires_at=expires_at,
        )

    async def refresh_token(self, refresh_token: str) -> TokenRefreshResponse:
        """토큰 갱신

        Args:
            refresh_token: Refresh Token 문자열

        Returns:
            TokenRefreshResponse: 새 토큰 및 세션 정보
        """
        # 1. Refresh Token 검증
        try:
            payload = verify_token(refresh_token, JWT_SECRET_KEY)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e)) from e

        # 2. 토큰 타입 확인
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        # 3. jti 추출 및 global_session_key 조회
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=401, detail="Invalid token: jti not found")

        redis_client = get_redis_client()
        helper = RedisHelper(redis_client)
        global_session_key = await helper.get_global_session_key_by_jti(jti)

        if not global_session_key:
            raise HTTPException(status_code=401, detail="Token expired or invalid")

        # 4. 세션 TTL 연장 (Refresh Token 갱신은 사용자 활동의 일부)
        await self.session_repo.refresh_ttl(global_session_key)

        # 5. 새 jti 생성 (Refresh Token Rotation)
        new_jti = str(uuid4())

        # 6. 새 토큰 발급 (새 jti 사용)
        user_id = payload.get("sub", "")
        new_access_token = create_access_token(new_jti, user_id, JWT_SECRET_KEY)
        new_refresh_token = create_refresh_token(new_jti, user_id, JWT_SECRET_KEY)

        # 7. 기존 jti 매핑 삭제 및 새 jti 매핑 저장
        await redis_client.delete(f"jti:{jti}")
        await helper.set_jti_mapping(new_jti, global_session_key, SESSION_CACHE_TTL)

        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            global_session_key=global_session_key,
            jti=new_jti,
        )

    async def ping_session_by_token(self, token: str) -> SessionPingResponse:
        """토큰 기반 세션 Ping (TTL 연장 없음)

        Args:
            token: Access Token 문자열

        Returns:
            SessionPingResponse: 세션 생존 여부 및 현재 만료 시각

        Raises:
            HTTPException: 토큰이 유효하지 않은 경우 401 반환
        """
        from datetime import datetime

        # 1. 토큰에서 global_session_key 조회
        try:
            global_session_key = await get_global_session_key_from_token(token)
        except HTTPException as e:
            raise e

        # 2. 세션 조회
        session = await self.session_repo.get(global_session_key)
        if not session:
            return SessionPingResponse(is_alive=False, expires_at=None)

        # 3. 만료 시각 반환 (TTL 연장 안 함)
        expires_at = None
        expires_raw = session.get("expires_at")
        if isinstance(expires_raw, str):
            try:
                expires_at = datetime.fromisoformat(expires_raw)
            except ValueError:
                expires_at = None

        return SessionPingResponse(is_alive=True, expires_at=expires_at)

    async def close_session_by_token(self, token: str, close_reason: str | None = None) -> SessionCloseResponse:
        """토큰 기반 세션 종료

        Args:
            token: Access Token 문자열
            close_reason: 종료 사유

        Returns:
            SessionCloseResponse: 세션 종료 응답
        """
        from datetime import UTC, datetime

        from app.core.exceptions import SessionNotFoundError
        from app.core.utils import datetime_to_iso
        from app.schemas.common import SessionState

        # 1. 토큰에서 global_session_key 조회
        global_session_key = await get_global_session_key_from_token(token)

        # 2. 세션 조회 및 종료 처리
        session = await self.session_repo.get(global_session_key)
        if not session:
            raise SessionNotFoundError(global_session_key)

        now = datetime.now(UTC)

        updates = {
            "session_state": SessionState.END.value,
            "close_reason": close_reason,
            "ended_at": datetime_to_iso(now),
        }

        await self.session_repo.update(global_session_key, **updates)

        # conversation_id 없이 세션 기준 아카이브 ID 생성
        archived_id = f"arch_{global_session_key}"

        return SessionCloseResponse(
            status="success",
            closed_at=now,
            archived_conversation_id=archived_id,
            cleaned_local_sessions=0,
        )
