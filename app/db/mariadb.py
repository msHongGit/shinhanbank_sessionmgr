"""MariaDB 연결 및 연결 풀 관리 (Async)"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import (
    MARIADB_DATABASE,
    MARIADB_HOST,
    MARIADB_MAX_OVERFLOW,
    MARIADB_PASSWORD,
    MARIADB_POOL_SIZE,
    MARIADB_PORT,
    MARIADB_USER,
)

_engine = None
_AsyncSessionLocal = None


def init_mariadb():
    """MariaDB 연결 초기화 (Async)"""
    global _engine, _AsyncSessionLocal
    if not _engine and MARIADB_HOST:
        database_url = f"mysql+aiomysql://{MARIADB_USER}:{MARIADB_PASSWORD}@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}"
        _engine = create_async_engine(
            database_url,
            pool_size=MARIADB_POOL_SIZE,
            max_overflow=MARIADB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        _AsyncSessionLocal = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )


@asynccontextmanager
async def get_mariadb_session():
    """MariaDB 세션 반환 (Async Context Manager)"""
    if not _AsyncSessionLocal:
        init_mariadb()
    if not _AsyncSessionLocal:
        raise RuntimeError("MariaDB connection not initialized")
    session = _AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
