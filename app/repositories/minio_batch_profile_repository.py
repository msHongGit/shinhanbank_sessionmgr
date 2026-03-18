"""MinIO 배치 프로파일 Repository (Async).

외부 배치 시스템에서 제공하는 batch_profile_minio_retrieve 모듈을 thin wrapper로 감싸서
CUSNO 기준으로 일별/월별 배치 프로파일을 조회한다.

설계 원칙:
- MariaDBBatchProfileRepository.get_batch_profile 와 동일한 async 시그니처 유지
- MinIO / 접근키 / 시크릿 / 버킷은 모두 환경변수(app.config)를 통해 주입
- MinIO 조회 오류나 설정 누락 시 None 반환 (크래시 방지)
- Python용 MinIO/인덱스 로직은 별도 모듈(batch_profile_minio_retrieve)에 위임
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app import config

logger = logging.getLogger(__name__)


class MinioBatchProfileRepository:
    """MinIO 배치 프로파일 Repository (Async)."""

    async def _retrieve_single_profile(self, data_type: str, cusno: str) -> dict[str, Any] | None:
        """단일 타입(daily/monthly) 배치 프로파일 조회.

        실제 MinIO 조회는 batch_profile_minio_retrieve.retrieve_cusno 에 위임한다.
        이 함수는 동기 함수이므로 asyncio.to_thread 로 오프로드한다.
        """
        if not config.MINIO_ENDPOINT:
            logger.error("MINIO_ENDPOINT is not set; skip MinIO batch profile fetch.")
            return None

        if not config.MINIO_ACCESS_KEY or not config.MINIO_SECRET_KEY:
            logger.error("MINIO_ACCESS_KEY or MINIO_SECRET_KEY is not set; skip MinIO batch profile fetch.")
            return None

        try:
            # 동일 프로젝트 내 MinIO 단건 조회 헬퍼
            from app.services.batch_profile_minio_retrieve import retrieve_cusno  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover - 환경에 따라 달라질 수 있음
            logger.error("retrieve_cusno is not available in batch_profile_minio_retrieve: %s", exc)
            return None

        cusno_str = cusno.strip()
        if not cusno_str:
            return None

        async def _run() -> dict[str, Any] | None:
            try:
                return await asyncio.to_thread(
                    retrieve_cusno,
                    endpoint=config.MINIO_ENDPOINT,
                    access_key=config.MINIO_ACCESS_KEY,
                    secret_key=config.MINIO_SECRET_KEY,
                    data_type=data_type,
                    cusno=cusno_str,
                )
            except (OSError, RuntimeError) as exc:  # pragma: no cover - 외부 시스템 오류 방어
                logger.error(
                    "Failed to retrieve %s batch profile from MinIO for CUSNO %s: %s",
                    data_type,
                    cusno_str,
                    exc,
                )
                return None

        return await _run()

    async def get_batch_profile(self, user_id: str) -> dict[str, Any] | None:
        """배치 프로파일 조회 (일별+월별).

        Args:
            user_id: 고객번호(CUSNO)

        Returns:
            {
                "daily": {...},
                "monthly": {...},
            } 또는 None
        """
        cusno = str(user_id).strip()
        if not cusno:
            return None

        # 일별/월별을 병렬로 조회 (가능한 경우)
        try:
            daily_profile, monthly_profile = await asyncio.gather(
                self._retrieve_single_profile("daily", cusno),
                self._retrieve_single_profile("monthly", cusno),
            )
        except (OSError, RuntimeError) as exc:  # pragma: no cover - 안전장치
            logger.error("Failed to fetch batch profile from MinIO for user %s: %s", user_id, exc)
            return None

        result: dict[str, Any] = {}
        if daily_profile:
            result["daily"] = daily_profile
        if monthly_profile:
            result["monthly"] = monthly_profile

        return result or None
