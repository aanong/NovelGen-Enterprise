from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import WorldItemResponse, NovelBibleResponse
from src.services.world_service import WorldService

router = APIRouter()

@router.get("/items", response_model=List[WorldItemResponse])
def read_world_items(novel_id: int, db: Session = Depends(get_db)):
    world_service = WorldService(db)
    return world_service.get_world_items(novel_id)

@router.get("/bible", response_model=List[NovelBibleResponse])
def read_bible_entries(novel_id: int, db: Session = Depends(get_db)):
    world_service = WorldService(db)
    return world_service.get_bible_entries(novel_id)
