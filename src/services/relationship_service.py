from typing import List
from sqlalchemy.orm import Session
from src.db.relationship_repository import RelationshipRepository
from src.api.schemas import RelationshipResponse, RelationshipCreate
from src.db.models import CharacterRelationship

class RelationshipService:
    def __init__(self, db: Session):
        self.relationship_repository = RelationshipRepository(db)

    def get_relationships_by_character(self, character_id: int) -> List[RelationshipResponse]:
        relationships = self.relationship_repository.get_by_character_id(character_id)
        return [RelationshipResponse.from_orm(relationship) for relationship in relationships]

    def get_relationships_by_novel(self, novel_id: int) -> List[RelationshipResponse]:
        relationships = self.relationship_repository.get_by_novel_id(novel_id)
        return [RelationshipResponse.from_orm(relationship) for relationship in relationships]

    def create_relationship(self, relationship: RelationshipCreate) -> RelationshipResponse:
        db_relationship = CharacterRelationship(**relationship.dict())
        created_relationship = self.relationship_repository.add(db_relationship)
        return RelationshipResponse.from_orm(created_relationship)
