from typing import List
from sqlalchemy.orm import Session
from src.db.models import CharacterRelationship, Character
from src.db.repository import Repository

class RelationshipRepository(Repository[CharacterRelationship]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get(self, id: int) -> CharacterRelationship:
        return self.db.query(CharacterRelationship).filter(CharacterRelationship.id == id).first()

    def get_all(self) -> List[CharacterRelationship]:
        return self.db.query(CharacterRelationship).all()

    def add(self, entity: CharacterRelationship) -> CharacterRelationship:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: CharacterRelationship):
        self.db.delete(entity)
        self.db.commit()

    def get_by_character_id(self, character_id: int) -> List[CharacterRelationship]:
        return self.db.query(CharacterRelationship).filter(
            (CharacterRelationship.char_a_id == character_id) | (CharacterRelationship.char_b_id == character_id)
        ).all()

    def get_by_novel_id(self, novel_id: int) -> List[CharacterRelationship]:
        return self.db.query(CharacterRelationship).join(Character, CharacterRelationship.char_a_id == Character.id).filter(Character.novel_id == novel_id).all()
