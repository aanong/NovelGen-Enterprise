from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import OutlineResponse, OutlineCreate
from src.services.outline_service import OutlineService

router = APIRouter()

@router.post("/", response_model=OutlineResponse)
def create_outline(outline: OutlineCreate, db: Session = Depends(get_db)):
    outline_service = OutlineService(db)
    return outline_service.create_outline(outline)

@router.get("/", response_model=List[OutlineResponse])
def read_outlines(
    novel_id: int,
    skip: int = 0, 
    limit: int = 100, 
    branch_id: str = "main",
    db: Session = Depends(get_db)
):
    outline_service = OutlineService(db)
    return outline_service.get_outlines_by_novel(novel_id, branch_id, skip, limit)
