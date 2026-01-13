from typing import List
from sqlalchemy.orm import Session
from src.db.models import CharacterRelationship, Character

class RelationshipService:
    @staticmethod
    def get_relationships_by_novel(db: Session, novel_id: int) -> List[CharacterRelationship]:
        return db.query(CharacterRelationship).join(
            CharacterRelationship.character_a
        ).filter(
            CharacterRelationship.character_a.has(novel_id=novel_id)
        ).all()
