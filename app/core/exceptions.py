"""
Session Manager - Custom Exceptions
"""
from typing import Optional


class SessionManagerException(Exception):
    """Base exception for Session Manager"""
    
    def __init__(
        self,
        code: str,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 500,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


class SessionNotFoundError(SessionManagerException):
    """Session not found"""
    
    def __init__(self, session_id: str):
        super().__init__(
            code="SM004",
            message="Session not found",
            detail=f"Session with id '{session_id}' does not exist",
            status_code=404,
        )


class TaskNotFoundError(SessionManagerException):
    """Task not found"""
    
    def __init__(self, task_id: str):
        super().__init__(
            code="SM005",
            message="Task not found",
            detail=f"Task with id '{task_id}' does not exist or is not ready",
            status_code=404,
        )


class SessionAlreadyExistsError(SessionManagerException):
    """Session already exists"""
    
    def __init__(self, session_key: str):
        super().__init__(
            code="SM006",
            message="Session already exists",
            detail=f"Session with key '{session_key}' already exists",
            status_code=409,
        )


class InvalidSessionStateError(SessionManagerException):
    """Invalid session state transition"""
    
    def __init__(self, from_state: str, to_state: str):
        super().__init__(
            code="SM007",
            message="Invalid session state transition",
            detail=f"Cannot transition from '{from_state}' to '{to_state}'",
            status_code=422,
        )


class RedisConnectionError(SessionManagerException):
    """Redis connection error"""
    
    def __init__(self, detail: str = None):
        super().__init__(
            code="SM009",
            message="Redis connection failed",
            detail=detail,
            status_code=503,
        )


class DatabaseConnectionError(SessionManagerException):
    """Database connection error"""
    
    def __init__(self, detail: str = None):
        super().__init__(
            code="SM010",
            message="Database connection failed",
            detail=detail,
            status_code=503,
        )
