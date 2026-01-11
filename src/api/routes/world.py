from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.db.models import WorldItem, NovelBible
from src.api.schemas import WorldItemResponse, NovelBibleResponse

router = APIRouter()

@router.get("/items", response_model=List[WorldItemResponse])
def read_world_items(novel_id: int, db: Session = Depends(get_db)):
    items = db.query(WorldItem).filter(WorldItem.novel_id == novel_id).all()
    return items

@router.get("/bible", response_model=List[NovelBibleResponse])
def read_bible_entries(novel_id: int, db: Session = Depends(get_db)):
    entries = db.query(NovelBible).filter(NovelBible.novel_id == novel_id).all()
    return entries
