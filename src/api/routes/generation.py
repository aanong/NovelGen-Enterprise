from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.main import run_generation_task
import asyncio

router = APIRouter()

class GenerationRequest(BaseModel):
    branch_id: str = "main"

class GenerationResponse(BaseModel):
    message: str
    status: str

# Simple in-memory lock to prevent concurrent generations
is_generating = False

async def background_generation_task():
    global is_generating
    try:
        await run_generation_task()
    finally:
        is_generating = False

@router.post("/", response_model=GenerationResponse)
async def trigger_generation(
    request: GenerationRequest, 
    background_tasks: BackgroundTasks
):
    global is_generating
    if is_generating:
        raise HTTPException(status_code=409, detail="Generation already in progress")
    
    is_generating = True
    background_tasks.add_task(background_generation_task)
    
    return {
        "message": "Generation task started",
        "status": "started"
    }

@router.get("/status")
def get_status():
    global is_generating
    return {"is_generating": is_generating}
