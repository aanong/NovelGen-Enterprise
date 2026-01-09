from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.db.models import Novel
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter()

class NovelBase(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    status: str = "ongoing"

class NovelCreate(NovelBase):
    pass

class NovelResponse(NovelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

@router.post("/", response_model=NovelResponse)
def create_novel(novel: NovelCreate, db: Session = Depends(get_db)):
    db_novel = Novel(**novel.dict())
    db.add(db_novel)
    db.commit()
    db.refresh(db_novel)
    return db_novel

@router.get("/", response_model=List[NovelResponse])
def read_novels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    novels = db.query(Novel).offset(skip).limit(limit).all()
    return novels

@router.get("/{novel_id}", response_model=NovelResponse)
def read_novel(novel_id: int, db: Session = Depends(get_db)):
    novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return novel

@router.put("/{novel_id}", response_model=NovelResponse)
def update_novel(novel_id: int, novel: NovelCreate, db: Session = Depends(get_db)):
    db_novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if db_novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    
    for key, value in novel.dict().items():
        setattr(db_novel, key, value)
    
    db.commit()
    db.refresh(db_novel)
    return db_novel

@router.delete("/{novel_id}")
def delete_novel(novel_id: int, db: Session = Depends(get_db)):
    db_novel = db.query(Novel).filter(Novel.id == novel_id).first()
    if db_novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    
    db.delete(db_novel)
    db.commit()
    return {"message": "Novel deleted successfully"}
