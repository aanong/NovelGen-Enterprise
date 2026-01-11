from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.db.models import CharacterRelationship
from src.api.schemas import RelationshipResponse

router = APIRouter()

@router.get("/", response_model=List[RelationshipResponse])
def read_relationships(
    novel_id: int, 
    db: Session = Depends(get_db)
):
    # This might need a join if we want to filter by novel_id directly, 
    # but CharacterRelationship links to Character which links to Novel.
    # So we join Character.
    relationships = db.query(CharacterRelationship).join(
        CharacterRelationship.character_a
    ).filter(
        CharacterRelationship.character_a.has(novel_id=novel_id)
    ).all()
    
    return relationships
