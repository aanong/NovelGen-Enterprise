from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.db.models import Character
from src.api.schemas import CharacterResponse

router = APIRouter()

@router.get("/", response_model=List[CharacterResponse])
def read_characters(
    novel_id: int,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    characters = db.query(Character).filter(
        Character.novel_id == novel_id
    ).offset(skip).limit(limit).all()
    return characters

@router.get("/{character_id}", response_model=CharacterResponse)
def read_character(character_id: int, db: Session = Depends(get_db)):
    character = db.query(Character).filter(Character.id == character_id).first()
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return character
