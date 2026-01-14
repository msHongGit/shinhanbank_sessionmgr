"""Session Manager - MariaDB Connection.

Sprint 3: Azure MariaDB 연결 설정.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import (
    MARIADB_DATABASE,
    MARIADB_ECHO,
    MARIADB_HOST,
    MARIADB_MAX_OVERFLOW,
    MARIADB_PASSWORD,
    MARIADB_POOL_RECYCLE,
    MARIADB_POOL_SIZE,
    MARIADB_PORT,
    MARIADB_USER,
    USE_MARIADB,
)

# ============================================================================
# MariaDB 연결 설정
# ============================================================================

if not USE_MARIADB:
    # MariaDB가 구축되지 않은 경우 None으로 설정 (테스트 환경)
    engine = None
    SessionLocal = None
else:
    # SQLAlchemy 엔진 생성 (동기)
    DATABASE_URL = f"mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}?charset=utf8mb4"

    engine = create_engine(
        DATABASE_URL,
        pool_size=MARIADB_POOL_SIZE,
        max_overflow=MARIADB_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=MARIADB_POOL_RECYCLE,
        echo=MARIADB_ECHO,
    )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ============================================================================
# 의존성 주입 헬퍼
# ============================================================================


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 의존성으로 사용할 DB 세션 제공

    Usage:
        @router.get("/...")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    if SessionLocal is None:
        # MariaDB가 구축되지 않은 경우 Mock 사용
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
