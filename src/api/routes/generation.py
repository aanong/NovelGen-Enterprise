from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from src.services.generation_service import GenerationService
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
    return await GenerationService.trigger_generation(request.novel_id, request.branch_id)

@router.get("/status/{task_id}")
def get_task_status(task_id: str):
    return GenerationService.get_task_status(task_id)

@router.get("/stream/{task_id}")
async def stream_generation(task_id: str, request: Request):
    """
    SSE 端点：实时推送生成进度和内容
    """
    return EventSourceResponse(
        GenerationService.stream_generation_events(task_id, request.is_disconnected)
    )

