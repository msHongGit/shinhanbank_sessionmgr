"""
Session Manager - Configuration Settings
"""
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # App
    APP_ENV: str = "dev"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 10
    SESSION_CACHE_TTL: int = 3600  # 1 hour
    TASK_CACHE_TTL: int = 86400  # 24 hours
    
    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/session_manager"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    
    # Session
    SESSION_TTL: int = 3600  # 1 hour
    SESSION_ID_PREFIX: str = "sess"
    CONVERSATION_ID_PREFIX: str = "conv"
    TASK_ID_PREFIX: str = "task"
    
    # API Keys (comma-separated)
    VALID_API_KEYS: str = "agw-api-key,ma-api-key,portal-api-key"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
