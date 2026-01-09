from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.tasks import generate_chapter_task
from celery.result import AsyncResult
from sse_starlette.sse import EventSourceResponse
from src.services.redis_stream import redis_stream
import json

router = APIRouter()

class GenerationRequest(BaseModel):
    novel_id: int
    branch_id: str = "main"

class GenerationResponse(BaseModel):
    message: str
    task_id: str
    status: str

@router.post("/", response_model=GenerationResponse)
async def trigger_generation(request: GenerationRequest):
    # 使用 Celery 异步调用
    task = generate_chapter_task.delay(request.novel_id, request.branch_id)
    
    return {
        "message": f"Generation task for novel {request.novel_id} queued",
        "task_id": task.id,
        "status": "queued"
    }

@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    task_result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None
    }

@router.get("/stream/{task_id}")
async def stream_generation(task_id: str, request: Request):
    """
    SSE 端点：实时推送生成进度和内容
    """
    async def event_generator():
        # 检查任务是否存在
        task_result = AsyncResult(task_id)
        if task_result.state == 'FAILURE':
             yield {
                "event": "error",
                "data": json.dumps({"message": "Task failed before streaming started"})
            }
             return

        # 订阅 Redis
        try:
            async for message in redis_stream.listen_to_task(task_id):
                # 如果客户端断开连接，停止生成器
                if await request.is_disconnected():
                    break
                
                # message 是一个 dict，包含 type 和 data
                # 我们将其转换为 SSE 格式
                yield {
                    "event": message.get("type", "message"),
                    "data": json.dumps(message.get("data", {}))
                }
                
                # 如果收到 done 或 error，结束流
                if message.get("type") in ["done", "error"]:
                    break
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            }

    return EventSourceResponse(event_generator())
