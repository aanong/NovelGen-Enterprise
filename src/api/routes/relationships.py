from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.api.schemas import RelationshipResponse
from src.services.relationship_service import RelationshipService

router = APIRouter()

@router.get("/", response_model=List[RelationshipResponse])
def read_relationships(
    novel_id: int, 
    db: Session = Depends(get_db)
):
    return RelationshipService.get_relationships_by_novel(db, novel_id)

