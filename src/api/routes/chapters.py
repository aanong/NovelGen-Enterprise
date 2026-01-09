from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.db.models import Chapter
from src.api.schemas import ChapterResponse

router = APIRouter()

@router.get("/", response_model=List[ChapterResponse])
def read_chapters(
    skip: int = 0, 
    limit: int = 100, 
    branch_id: str = "main",
    db: Session = Depends(get_db)
):
    chapters = db.query(Chapter).filter(
        Chapter.branch_id == branch_id
    ).order_by(Chapter.chapter_number).offset(skip).limit(limit).all()
    return chapters

@router.get("/{chapter_id}", response_model=ChapterResponse)
def read_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
