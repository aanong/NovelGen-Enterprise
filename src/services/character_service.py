from typing import List, Optional
from sqlalchemy.orm import Session
from src.db.models import Character

class CharacterService:
    @staticmethod
    def get_characters(db: Session, novel_id: int, skip: int = 0, limit: int = 100) -> List[Character]:
        return db.query(Character).filter(
            Character.novel_id == novel_id
        ).offset(skip).limit(limit).all()

    @staticmethod
    def get_character(db: Session, character_id: int) -> Optional[Character]:
        return db.query(Character).filter(Character.id == character_id).first()
