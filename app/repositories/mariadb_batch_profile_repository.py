"""MariaDB 배치 프로파일 Repository (Async)"""

import logging
from typing import Any

from sqlalchemy import text

from app.db.mariadb import get_mariadb_session

logger = logging.getLogger(__name__)


class MariaDBBatchProfileRepository:
    """MariaDB 배치 프로파일 Repository (Async)"""

    async def get_batch_profile(self, user_id: str) -> dict[str, Any] | None:
        """배치 프로파일 조회 (일별+월별)

        IFC_CUS_DD_SMRY_TOT (일별)과 IFC_CUS_MMBY_SMRY_TOT (월별) 테이블에서
        모든 컬럼을 조회하여 dict로 반환

        Args:
            user_id: 고객번호 (CUSNO)

        Returns:
            배치 프로파일 데이터 (dict) 또는 None
            {
                "daily": {...},    # 일별 테이블의 모든 컬럼
                "monthly": {...}   # 월별 테이블의 모든 컬럼
            }
        """
        try:
            session = await get_mariadb_session()
            try:
                # 일별 테이블 조회 (최신 데이터)
                daily_query = text("""
                    SELECT * FROM IFC_CUS_DD_SMRY_TOT
                    WHERE CUSNO = :cusno
                    ORDER BY STD_DT DESC
                    LIMIT 1
                """)
                daily_result = await session.execute(daily_query, {"cusno": user_id})
                daily_row = daily_result.fetchone()

                # 월별 테이블 조회 (최신 데이터)
                monthly_query = text("""
                    SELECT * FROM IFC_CUS_MMBY_SMRY_TOT
                    WHERE CUSNO = :cusno
                    ORDER BY STD_YM DESC
                    LIMIT 1
                """)
                monthly_result = await session.execute(monthly_query, {"cusno": user_id})
                monthly_row = monthly_result.fetchone()

                if not daily_row and not monthly_row:
                    return None

                # 모든 컬럼을 dict로 변환
                batch_data = {}

                if daily_row:
                    daily_dict = dict(daily_row._mapping)
                    # 메타데이터 컬럼 제외
                    daily_dict.pop("CREATED_AT", None)
                    daily_dict.pop("UPDATED_AT", None)
                    batch_data["daily"] = daily_dict

                if monthly_row:
                    monthly_dict = dict(monthly_row._mapping)
                    # 메타데이터 컬럼 제외
                    monthly_dict.pop("CREATED_AT", None)
                    monthly_dict.pop("UPDATED_AT", None)
                    batch_data["monthly"] = monthly_dict

                return batch_data if batch_data else None
            except Exception as e:
                logger.error(f"Failed to fetch batch profile for user {user_id}: {e}")
                return None
            finally:
                await session.close()
        except Exception as e:
            logger.error(f"Failed to get MariaDB session: {e}")
            return None
