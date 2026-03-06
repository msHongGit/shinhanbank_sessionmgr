"""Session Manager - Profile Service (Async).

사용자 프로필 관리 서비스
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status

from app.core.exceptions import ProfileNotFoundError, SessionNotFoundError
from app.db.redis import RedisHelper, get_redis_client
from app.logger_config import LoggerExtraData
from app.services.batch_profile_utils import normalize_cusno
from app.schemas.common import (
    CustomerProfile,
    ProfileAttribute,
    RealtimePersonalContextRequest,
    RealtimePersonalContextResponse,
)

logger = logging.getLogger(__name__)


class ProfileService:
    """사용자 프로필 관리 서비스 (Async)"""

    def __init__(self, session_repo, profile_repo=None):
        """ProfileService 초기화

        Args:
            session_repo: 세션 저장소 (RedisSessionRepository)
            profile_repo: 프로파일 저장소 (MariaDBBatchProfileRepository, 선택)
        """
        self.session_repo = session_repo
        self.profile_repo = profile_repo

    @staticmethod
    def _merge_profiles(
        batch_profile: CustomerProfile | None,
        realtime_profile: dict[str, Any] | None,
    ) -> CustomerProfile | None:
        """배치 프로파일과 실시간 프로파일 통합 (실시간 우선)

        Args:
            batch_profile: 배치 프로파일
            realtime_profile: 실시간 프로파일 (dict, redis_data.md 구조)

        Returns:
            통합된 CustomerProfile 또는 None
        """
        if not batch_profile and not realtime_profile:
            return None

        # 실시간 프로파일이 있으면 우선 사용
        if realtime_profile:
            # 실시간 프로파일의 모든 필드를 속성으로 변환
            attributes = []
            segment = None

            for key, value in realtime_profile.items():
                if value is not None and value != "":
                    attributes.append(
                        ProfileAttribute(
                            key=key,
                            value=str(value),
                            source_system="REALTIME",
                        )
                    )

                    # 세그먼트 관련 필드 추출 (membGdS2 등)
                    if key == "membGdS2":
                        segment = str(value)

            return CustomerProfile(
                user_id=realtime_profile.get("cusnoN10", batch_profile.user_id if batch_profile else ""),
                attributes=attributes,
                segment=segment,
                preferences={"source": "realtime"},
            )

        # 실시간 프로파일이 없으면 배치 프로파일 사용
        return batch_profile

    async def get_merged_profile(self, user_id: str) -> CustomerProfile | None:
        """배치 + 실시간 프로파일 통합 조회

        Args:
            user_id: 사용자 ID

        Returns:
            통합된 CustomerProfile (실시간 우선)
        """
        # 배치 프로파일 조회
        batch_profile = None
        if self.profile_repo:
            batch_profile = await self.profile_repo.get_profile(user_id=user_id, context_id=None)

        # 실시간 프로파일 조회
        redis_client = get_redis_client()
        helper = RedisHelper(redis_client)
        realtime_profile = await helper.get_realtime_profile(user_id)

        # 통합
        return self._merge_profiles(batch_profile, realtime_profile)

    async def get_batch_and_realtime_profiles_by_user_id(self, user_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """user_id로 배치 프로파일과 실시간 프로파일을 분리하여 조회

        Args:
            user_id: 사용자 ID (세션의 user_id)

        Returns:
            tuple: (batch_profile_data, realtime_profile_data)

        처리 흐름:
            1. user_id로 실시간 프로파일 조회 시도
            2. 실시간 프로파일에서 cusnoN10 추출 (CUSNO)
            3. 실시간 프로파일이 없으면 user_id를 CUSNO로 사용 (fallback)
            4. CUSNO로 배치/실시간 프로파일 조회
        """
        redis_client = get_redis_client()
        helper = RedisHelper(redis_client)

        # 실시간 프로파일에서 CUSNO 추출 시도
        realtime_profile_temp = await helper.get_realtime_profile(user_id)
        cusno = None

        if realtime_profile_temp and "cusnoN10" in realtime_profile_temp:
            # 실시간 프로파일에서 cusnoN10 추출
            cusno = str(realtime_profile_temp["cusnoN10"]).strip()
        elif user_id:
            # 실시간 프로파일이 없으면 user_id를 CUSNO로 사용 (fallback)
            cusno = str(user_id).strip()

        if not cusno:
            # CUSNO를 찾을 수 없으면 None 반환
            return None, None

        # CUSNO로 배치/실시간 프로파일 조회
        return await self.get_batch_and_realtime_profiles(cusno)

    async def get_batch_and_realtime_profiles(self, cusno: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """배치 프로파일과 실시간 프로파일을 분리하여 조회

        Args:
            cusno: 고객번호 (CUSNO) - 실시간 프로파일의 cusnoN10 값

        Returns:
            tuple: (batch_profile_data, realtime_profile_data)

        참고:
            - 실시간 프로파일 저장 시 이미 Redis에 저장되므로 MariaDB 재조회 불필요
            - Redis에서만 조회 (없으면 None 반환)
        """
        redis_client = get_redis_client()
        helper = RedisHelper(redis_client)

        # Redis에서 배치 프로파일 조회 (이미 저장되어 있음)
        batch_profile_data = await helper.get_batch_profile(cusno)

        # 실시간 프로파일 조회
        realtime_profile_data = await helper.get_realtime_profile(cusno)

        return batch_profile_data, realtime_profile_data

    async def update_realtime_personal_context(
        self,
        global_session_key: str,
        request: RealtimePersonalContextRequest,
    ) -> RealtimePersonalContextResponse:
        """실시간 프로파일 업데이트

        Args:
            global_session_key: 세션 키
            request: 실시간 프로파일 요청

        Returns:
            RealtimePersonalContextResponse

        처리 흐름:
        1. 실시간 프로파일에서 cusnoN10 추출 시도 (CUSNO)
        2. cusnoN10이 있으면:
           - 세션에 cusno 매핑 저장
           - Redis에 실시간 프로파일 저장 (CUSNO를 키로 사용)
           - MariaDB에서 배치 프로파일 조회 및 Redis에 저장
        3. cusnoN10이 없으면:
           - 세션에 cusno 저장하지 않음
           - Redis에 실시간 프로파일 저장 (global_session_key를 키로 사용)
           - 배치 프로파일 조회하지 않음 (CUSNO 없음)
        """
        # 1. 세션 존재 확인
        session = await self.session_repo.get(global_session_key)
        if not session:
            raise SessionNotFoundError(global_session_key)

        # 2. 실시간 프로파일에서 CUSNO 추출 시도 (cusnoN10 컬럼, 선택적)
        cusno = None

        profile_data = request.profile_data
        cusno_raw = profile_data.get("cusnoN10")

        if not cusno_raw:
            response_data = profile_data.get("responseData", {})
            cusno_raw = response_data.get("cusnoN10")
        if cusno_raw:
            cusno = normalize_cusno(cusno_raw)  # 앞자리 0 제거 (MinIO 숫자형 저장 형식 맞춤)

        redis_client = get_redis_client()
        helper = RedisHelper(redis_client)

        batch_profile_fetched = False
        batch_daily_fetched = False
        batch_monthly_fetched = False
        saved_realtime_key: str | None = None

        if cusno:
            # cusnoN10이 있는 경우: 정상적인 프로파일 저장 플로우
            # 3. 세션에 cusno 매핑 저장 (세션 정보와 cusno 연결)
            await self.session_repo.update(global_session_key, cusno=cusno)

            # 4. Redis에 실시간 프로파일 저장 (CUSNO를 키로 사용)
            await helper.set_realtime_profile(cusno, request.profile_data)
            saved_realtime_key = cusno

            # 5. 배치 프로파일 조회 (MinIO/MariaDB 등) 및 Redis에 저장
            if self.profile_repo:
                batch_profile_data = await self.profile_repo.get_batch_profile(cusno)
                if batch_profile_data:
                    # Redis에 배치 프로파일 저장 (CUSNO를 키로 사용)
                    await helper.set_batch_profile(cusno, batch_profile_data)
                    batch_profile_fetched = True
                    batch_daily_fetched = "daily" in batch_profile_data
                    batch_monthly_fetched = "monthly" in batch_profile_data
        else:
            # cusnoN10이 없는 경우: 실시간 프로파일만 저장 (세션 키 기반)
            # 세션에 cusno 저장하지 않음
            # Redis에 실시간 프로파일 저장 (global_session_key를 키로 사용)
            await helper.set_realtime_profile(global_session_key, request.profile_data)
            saved_realtime_key = global_session_key
            # 배치 프로파일은 조회하지 않음 (CUSNO 없음)

        # ES 로그: 실시간/배치 프로파일 업데이트
        logger.eslog(
            LoggerExtraData(
                logType="REALTIME_BATCH_PROFILE_UPDATE",
                custNo=cusno or "-",
                sessionId=global_session_key,
                turnId="-",
                agentId="-",
                transactionId="-",
                payload={
                    "hasCusno": bool(cusno),
                    "savedRealtimeKey": saved_realtime_key,
                    "batchProfileFetched": batch_profile_fetched,
                    "batchDailyFetched": batch_daily_fetched,
                    "batchMonthlyFetched": batch_monthly_fetched,
                    "redisKeys": {
                        "realtime": f"profile:realtime:{saved_realtime_key}",
                        "batch": f"profile:batch:{cusno}" if cusno else None,
                    },
                },
            )
        )

        return RealtimePersonalContextResponse(
            status="success",
            updated_at=datetime.now(UTC),
        )
