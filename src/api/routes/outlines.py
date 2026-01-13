from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import OutlineResponse
from src.services.outline_service import OutlineService

router = APIRouter()

@router.get("/", response_model=List[OutlineResponse])
def read_outlines(
    novel_id: int,
    skip: int = 0, 
    limit: int = 100, 
    branch_id: str = "main",
    db: Session = Depends(get_db)
):
    return OutlineService.get_outlines(db, novel_id, branch_id, skip, limit)

