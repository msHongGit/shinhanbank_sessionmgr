"""MariaDB 연결 및 연결 풀 관리"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import (
    MARIADB_HOST,
    MARIADB_PORT,
    MARIADB_USER,
    MARIADB_PASSWORD,
    MARIADB_DATABASE,
    MARIADB_POOL_SIZE,
    MARIADB_MAX_OVERFLOW,
)

_engine = None
_SessionLocal = None


def init_mariadb():
    """MariaDB 연결 초기화"""
    global _engine, _SessionLocal
    if not _engine and MARIADB_HOST:
        database_url = f"mariadb+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}"
        _engine = create_engine(
            database_url,
            pool_size=MARIADB_POOL_SIZE,
            max_overflow=MARIADB_MAX_OVERFLOW,
            pool_pre_ping=True,
        )
        _SessionLocal = sessionmaker(bind=_engine)


def get_mariadb_session():
    """MariaDB 세션 반환"""
    if not _SessionLocal:
        init_mariadb()
    if not _SessionLocal:
        raise RuntimeError("MariaDB connection not initialized")
    return _SessionLocal()
