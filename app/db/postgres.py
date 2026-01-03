"""
Session Manager - PostgreSQL Connection (Sync)
v3.0: 모든 연동 Sync 방식
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import DATABASE_URL, DB_ECHO, DB_MAX_OVERFLOW, DB_POOL_SIZE

engine = create_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    echo=DB_ECHO,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Initialize database"""
    Base.metadata.create_all(bind=engine)
    print("✅ PostgreSQL connected (Sync)")


def close_db() -> None:
    """Close database connection"""
    engine.dispose()
    print("❌ PostgreSQL disconnected")


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
