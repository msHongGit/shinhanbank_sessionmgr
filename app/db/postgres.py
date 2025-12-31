"""
Session Manager - PostgreSQL Connection
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import Optional, AsyncGenerator

from app.config import settings

Base = declarative_base()

_engine = None
_async_session_factory = None


async def init_db() -> None:
    """Initialize database connection"""
    global _engine, _async_session_factory
    
    _engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        echo=settings.DB_ECHO,
    )
    
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables (개발 환경에서만)
    if settings.APP_ENV == "dev":
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    print("✅ PostgreSQL connected")


async def close_db() -> None:
    """Close database connection"""
    global _engine
    if _engine:
        await _engine.dispose()
        print("❌ PostgreSQL disconnected")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    if not _async_session_factory:
        await init_db()
    
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
