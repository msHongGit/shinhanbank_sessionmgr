"""
Session Manager - Task Service
"""
import json
from datetime import datetime
from uuid import uuid4

import redis.asyncio as redis

from app.config import settings
from app.schemas.task import (
    TaskEnqueueRequest,
    TaskEnqueueResponse,
    TaskStatusResponse,
    TaskResultResponse,
)
from app.core.exceptions import TaskNotFoundError


class TaskService:
    """Task Queue 관리 서비스"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def _generate_task_id(self) -> str:
        """Task ID 생성"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid4())[:6]
        return f"{settings.TASK_ID_PREFIX}_{timestamp}_{unique_id}"
    
    async def enqueue_task(self, request: TaskEnqueueRequest) -> TaskEnqueueResponse:
        """Task Queue에 작업 적재"""
        task_id = self._generate_task_id()
        now = datetime.utcnow()
        
        # Task 데이터 구성
        task_data = {
            "task_id": task_id,
            "session_id": request.session_id,
            "conversation_id": request.conversation_id,
            "turn_id": request.turn_id,
            "intent": request.intent,
            "priority": request.priority,
            "status": "pending",
            "task_payload": request.task_payload.dict(),
            "created_at": now.isoformat(),
        }
        
        # 1. Sorted Set에 추가 (priority를 score로)
        queue_key = f"task_queue:{request.session_id}"
        await self.redis.zadd(queue_key, {json.dumps(task_data): request.priority})
        
        # 2. Task 상태 Hash 저장
        status_key = f"task:{task_id}"
        await self.redis.hset(
            status_key,
            mapping={
                "session_id": request.session_id,
                "conversation_id": request.conversation_id,
                "intent": request.intent,
                "task_status": "pending",
                "progress": "0",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        )
        await self.redis.expire(status_key, settings.TASK_CACHE_TTL)
        
        # 3. 세션의 task_queue_status 업데이트
        session_key = f"session:{request.session_id}"
        await self.redis.hset(session_key, "task_queue_status", "notnull")
        
        return TaskEnqueueResponse(status="accepted", task_id=task_id)
    
    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Task 상태 조회"""
        status_key = f"task:{task_id}"
        data = await self.redis.hgetall(status_key)
        
        if not data:
            raise TaskNotFoundError(task_id)
        
        return TaskStatusResponse(
            task_id=task_id,
            task_status=data.get("task_status", "pending"),
            progress=int(data.get("progress", 0)),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat())),
        )
    
    async def get_task_result(self, task_id: str) -> TaskResultResponse:
        """Task 결과 조회"""
        status_key = f"task:{task_id}"
        data = await self.redis.hgetall(status_key)
        
        if not data:
            raise TaskNotFoundError(task_id)
        
        task_status = data.get("task_status", "pending")
        
        if task_status not in ["completed", "failed"]:
            raise TaskNotFoundError(f"Task {task_id} is not completed yet")
        
        # result_payload 파싱
        result_payload = None
        if data.get("result_payload"):
            try:
                result_payload = json.loads(data.get("result_payload"))
            except json.JSONDecodeError:
                pass
        
        return TaskResultResponse(
            task_id=task_id,
            task_status=task_status,
            outcome=data.get("outcome", "normal"),
            response_text=data.get("response_text"),
            result_payload=result_payload,
        )
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: int = None,
        outcome: str = None,
        response_text: str = None,
        result_payload: dict = None,
    ) -> None:
        """Task 상태 업데이트 (내부 사용)"""
        status_key = f"task:{task_id}"
        
        update_data = {
            "task_status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if progress is not None:
            update_data["progress"] = str(progress)
        if outcome:
            update_data["outcome"] = outcome
        if response_text:
            update_data["response_text"] = response_text
        if result_payload:
            update_data["result_payload"] = json.dumps(result_payload)
        
        await self.redis.hset(status_key, mapping=update_data)
    
    async def dequeue_task(self, session_id: str) -> dict:
        """Task Queue에서 가장 높은 우선순위 Task 가져오기"""
        queue_key = f"task_queue:{session_id}"
        
        # 가장 낮은 score(높은 우선순위) 가져오기
        tasks = await self.redis.zrange(queue_key, 0, 0)
        
        if not tasks:
            return None
        
        task_data = json.loads(tasks[0])
        
        # Queue에서 제거
        await self.redis.zrem(queue_key, tasks[0])
        
        # Queue가 비었으면 세션 상태 업데이트
        remaining = await self.redis.zcard(queue_key)
        if remaining == 0:
            session_key = f"session:{session_id}"
            await self.redis.hset(session_key, "task_queue_status", "null")
        
        return task_data
