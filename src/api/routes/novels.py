from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import NovelCreate, NovelResponse
from src.services.novel_service import NovelService

router = APIRouter()

@router.post("/", response_model=NovelResponse)
def create_novel(novel: NovelCreate, db: Session = Depends(get_db)):
    novel_service = NovelService(db)
    return novel_service.create_novel(novel)

@router.get("/", response_model=List[NovelResponse])
def read_novels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    novel_service = NovelService(db)
    return novel_service.get_novels(skip=skip, limit=limit)

@router.get("/{novel_id}", response_model=NovelResponse)
def read_novel(novel_id: int, db: Session = Depends(get_db)):
    novel_service = NovelService(db)
    novel = novel_service.get_novel(novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return novel

# The update, delete, and export endpoints also need to be implemented in the service
