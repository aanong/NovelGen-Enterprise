from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.db.models import PlotOutline
from src.api.schemas import OutlineResponse

router = APIRouter()

@router.get("/", response_model=List[OutlineResponse])
def read_outlines(
    skip: int = 0, 
    limit: int = 100, 
    branch_id: str = "main",
    db: Session = Depends(get_db)
):
    outlines = db.query(PlotOutline).filter(
        PlotOutline.branch_id == branch_id
    ).order_by(PlotOutline.chapter_number).offset(skip).limit(limit).all()
    return outlines
