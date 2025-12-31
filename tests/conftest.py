"""
Session Manager - Test Configuration and Fixtures
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from typing import AsyncGenerator

from app.main import app
from app.config import settings


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client fixture"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def api_headers() -> dict:
    """API headers with valid API key"""
    return {
        "X-API-Key": "agw-api-key",
        "Content-Type": "application/json",
    }


@pytest.fixture
def sample_session_create_request() -> dict:
    """Sample session create request"""
    return {
        "user_id": "user_test_001",
        "channel": "mobile",
        "session_key": {
            "scope": "global",
            "key": "user_test_001_mobile"
        },
        "request_id": "req_test_001"
    }


@pytest.fixture
def sample_task_enqueue_request() -> dict:
    """Sample task enqueue request"""
    return {
        "session_id": "sess_test_001",
        "conversation_id": "conv_test_001",
        "turn_id": "turn_001",
        "intent": "이체내역_확인",
        "priority": 1,
        "session_state": "talk",
        "task_payload": {
            "masked": True,
            "data": {
                "query": "이전 내역을 확인하고 싶어요",
                "skill": "계좌_거래_기록확인"
            }
        }
    }
