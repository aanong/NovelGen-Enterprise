from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.main import run_generation_task
import asyncio

router = APIRouter()

class GenerationRequest(BaseModel):
    novel_id: int
    branch_id: str = "main"

class GenerationResponse(BaseModel):
    message: str
    status: str

# In-memory lock per novel_id
generation_locks = {}

async def background_generation_task(novel_id: int, branch_id: str):
    """Runs the generation task and releases the lock."""
    try:
        await run_generation_task(novel_id=novel_id, branch_id=branch_id)
    finally:
        if novel_id in generation_locks:
            del generation_locks[novel_id]

@router.post("/", response_model=GenerationResponse)
async def trigger_generation(
    request: GenerationRequest, 
    background_tasks: BackgroundTasks
):
    if request.novel_id in generation_locks:
        raise HTTPException(status_code=409, detail=f"Generation for novel {request.novel_id} is already in progress")
    
    generation_locks[request.novel_id] = True
    background_tasks.add_task(background_generation_task, request.novel_id, request.branch_id)
    
    return {
        "message": f"Generation task for novel {request.novel_id} started",
        "status": "started"
    }

@router.get("/status/{novel_id}")
def get_status(novel_id: int):
    return {"is_generating": novel_id in generation_locks}
