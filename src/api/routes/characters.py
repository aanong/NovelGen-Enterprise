from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import CharacterResponse, CharacterCreate
from src.services.character_service import CharacterService

router = APIRouter()

@router.post("/", response_model=CharacterResponse)
def create_character(character: CharacterCreate, db: Session = Depends(get_db)):
    character_service = CharacterService(db)
    return character_service.create_character(character)

@router.get("/", response_model=List[CharacterResponse])
def read_characters(
    novel_id: int,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    character_service = CharacterService(db)
    return character_service.get_characters_by_novel(novel_id, skip, limit)

@router.get("/{character_id}", response_model=CharacterResponse)
def read_character(character_id: int, db: Session = Depends(get_db)):
    character_service = CharacterService(db)
    character = character_service.get_character(character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character
