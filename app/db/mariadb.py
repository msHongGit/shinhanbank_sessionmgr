"""Session Manager - MariaDB Connection.

Sprint 3: Azure MariaDB 연결 설정.
"""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

# ============================================================================
# MariaDB 연결 설정
# ============================================================================

MARIADB_HOST = os.getenv("MARIADB_HOST", "localhost")
MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_USER = os.getenv("MARIADB_USER", "test_user")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "test_password")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "session_manager")

# MariaDB가 구축되지 않은 경우 None으로 설정 (테스트 환경)
if MARIADB_USER == "test_user" and MARIADB_PASSWORD == "test_password":
    engine = None
    SessionLocal = None
else:
    # SQLAlchemy 엔진 생성 (동기)
    DATABASE_URL = f"mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}?charset=utf8mb4"

    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,  # True로 설정하면 SQL 로깅
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
