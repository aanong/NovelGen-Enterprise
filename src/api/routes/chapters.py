from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import ChapterResponse, ChapterCreate
from src.services.chapter_service import ChapterService

router = APIRouter()

@router.post("/", response_model=ChapterResponse)
def create_chapter(chapter: ChapterCreate, db: Session = Depends(get_db)):
    chapter_service = ChapterService(db)
    return chapter_service.create_chapter(chapter)

@router.get("/", response_model=List[ChapterResponse])
def read_chapters(
    novel_id: int,
    skip: int = 0, 
    limit: int = 100, 
    branch_id: str = "main",
    db: Session = Depends(get_db)
):
    chapter_service = ChapterService(db)
    return chapter_service.get_chapters_by_novel(novel_id, branch_id, skip, limit)

@router.get("/{chapter_id}", response_model=ChapterResponse)
def read_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter_service = ChapterService(db)
    chapter = chapter_service.get_chapter(chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
