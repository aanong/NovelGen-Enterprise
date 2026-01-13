from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import ChapterResponse
from src.services.chapter_service import ChapterService

router = APIRouter()

@router.get("/", response_model=List[ChapterResponse])
def read_chapters(
    novel_id: int,
    skip: int = 0, 
    limit: int = 100, 
    branch_id: str = "main",
    db: Session = Depends(get_db)
):
    return ChapterService.get_chapters(db, novel_id, branch_id, skip, limit)

@router.get("/{chapter_id}", response_model=ChapterResponse)
def read_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = ChapterService.get_chapter(db, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

