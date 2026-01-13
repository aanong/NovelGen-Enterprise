from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import CharacterResponse
from src.services.character_service import CharacterService

router = APIRouter()

@router.get("/", response_model=List[CharacterResponse])
def read_characters(
    novel_id: int,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    return CharacterService.get_characters(db, novel_id, skip, limit)

@router.get("/{character_id}", response_model=CharacterResponse)
def read_character(character_id: int, db: Session = Depends(get_db)):
    character = CharacterService.get_character(db, character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character

