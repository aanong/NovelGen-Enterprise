from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import RelationshipResponse, RelationshipCreate
from src.services.relationship_service import RelationshipService

router = APIRouter()

@router.post("/", response_model=RelationshipResponse)
def create_relationship(relationship: RelationshipCreate, db: Session = Depends(get_db)):
    relationship_service = RelationshipService(db)
    return relationship_service.create_relationship(relationship)

@router.get("/", response_model=List[RelationshipResponse])
def read_relationships_by_novel(
    novel_id: int, 
    db: Session = Depends(get_db)
):
    relationship_service = RelationshipService(db)
    return relationship_service.get_relationships_by_novel(novel_id)

@router.get("/by_character/{character_id}", response_model=List[RelationshipResponse])
def read_relationships_by_character(
    character_id: int, 
    db: Session = Depends(get_db)
):
    relationship_service = RelationshipService(db)
    return relationship_service.get_relationships_by_character(character_id)
