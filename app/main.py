"""
Session Manager - Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.router import api_router
from app.db.postgres import init_db, close_db
from app.db.redis import init_redis, close_redis
from app.core.exceptions import SessionManagerException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await init_db()
    await init_redis()
    yield
    # Shutdown
    await close_db()
    await close_redis()


app = FastAPI(
    title="Session Manager API",
    description="세션 생명주기, Task Queue, 고객 프로파일 관리 API",
    version="1.0.0",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(SessionManagerException)
async def session_manager_exception_handler(request, exc: SessionManagerException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            }
        },
    )


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "session-manager"}


# Readiness check
@app.get("/ready")
async def readiness_check():
    # TODO: Add Redis and PostgreSQL connection checks
    return {"status": "ready"}


# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
