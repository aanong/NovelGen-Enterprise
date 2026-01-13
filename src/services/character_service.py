from typing import List
from sqlalchemy.orm import Session
from src.db.character_repository import CharacterRepository
from src.api.schemas import CharacterResponse, CharacterCreate
from src.db.models import Character

class CharacterService:
    def __init__(self, db: Session):
        self.character_repository = CharacterRepository(db)

    def get_characters_by_novel(self, novel_id: int, skip: int = 0, limit: int = 100) -> List[CharacterResponse]:
        characters = self.character_repository.get_by_novel_id(novel_id, skip, limit)
        return [CharacterResponse.from_orm(character) for character in characters]

    def get_character(self, character_id: int) -> CharacterResponse:
        character = self.character_repository.get(character_id)
        if character:
            return CharacterResponse.from_orm(character)
        return None

    def create_character(self, character: CharacterCreate) -> CharacterResponse:
        db_character = Character(**character.dict())
        created_character = self.character_repository.add(db_character)
        return CharacterResponse.from_orm(created_character)
