from typing import Dict, Any, AsyncGenerator, Optional
from celery.result import AsyncResult
from src.tasks import generate_chapter_task
from src.services.redis_stream import redis_stream
import json

class GenerationService:
    @staticmethod
    async def trigger_generation(novel_id: int, branch_id: str = "main") -> Dict[str, Any]:
        """
        Triggers the asynchronous chapter generation task via Celery.
        """
        task = generate_chapter_task.delay(novel_id, branch_id)
        return {
            "message": f"Generation task for novel {novel_id} queued",
            "task_id": task.id,
            "status": "queued"
        }

    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        Retrieves the status of a Celery task.
        """
        task_result = AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": task_result.status,
            "result": task_result.result if task_result.ready() else None
        }

    @staticmethod
    async def stream_generation_events(task_id: str, is_disconnected_func=None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Yields SSE-compatible events from the Redis stream for a specific task.
        """
        # Check task existence
        task_result = AsyncResult(task_id)
        if task_result.state == 'FAILURE':
            yield {
                "event": "error",
                "data": json.dumps({"message": "Task failed before streaming started"})
            }
            return

        # Subscribe to Redis
        try:
            async for message in redis_stream.listen_to_task(task_id):
                # Check for client disconnection if a check function is provided
                if is_disconnected_func and await is_disconnected_func():
                    break
                
                # message is a dict containing type and data
                yield {
                    "event": message.get("type", "message"),
                    "data": json.dumps(message.get("data", {}))
                }
                
                # Stop stream on done or error
                if message.get("type") in ["done", "error"]:
                    break
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            }
