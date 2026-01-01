"""
Session Manager - Custom Exceptions (v3.0)
"""


class SessionManagerError(Exception):
    """Base exception"""

    def __init__(
        self,
        code: str,
        message: str,
        detail: str | None = None,
        status_code: int = 500,
    ):
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


class SessionNotFoundError(SessionManagerError):
    """Session not found"""

    def __init__(self, session_key: str):
        super().__init__(
            code="SM001",
            message="Session not found",
            detail=f"Session with key '{session_key}' does not exist",
            status_code=404,
        )


class SessionExpiredError(SessionManagerError):
    """Session expired"""

    def __init__(self, session_key: str):
        super().__init__(
            code="SM002",
            message="Session expired",
            detail=f"Session '{session_key}' has expired",
            status_code=410,
        )


class LocalSessionNotFoundError(SessionManagerError):
    """Local session not found"""

    def __init__(self, global_key: str, agent_id: str):
        super().__init__(
            code="SM003",
            message="Local session not found",
            detail=f"No local session mapping for global='{global_key}', agent='{agent_id}'",
            status_code=404,
        )


class ContextNotFoundError(SessionManagerError):
    """Context not found"""

    def __init__(self, context_id: str):
        super().__init__(
            code="SM004",
            message="Context not found",
            detail=f"Context '{context_id}' does not exist",
            status_code=404,
        )


class ProfileNotFoundError(SessionManagerError):
    """Profile not found"""

    def __init__(self, user_id: str):
        super().__init__(
            code="SM005",
            message="Profile not found",
            detail=f"Profile for user '{user_id}' does not exist",
            status_code=404,
        )


class RedisConnectionError(SessionManagerError):
    """Redis connection error"""

    def __init__(self, detail: str = None):
        super().__init__(
            code="SM010",
            message="Redis connection failed",
            detail=detail,
            status_code=503,
        )


class DatabaseConnectionError(SessionManagerError):
    """Database connection error"""

    def __init__(self, detail: str = None):
        super().__init__(
            code="SM011",
            message="Database connection failed",
            detail=detail,
            status_code=503,
        )
