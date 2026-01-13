from typing import List
from sqlalchemy.orm import Session
from src.db.outline_repository import OutlineRepository
from src.api.schemas import OutlineResponse, OutlineCreate
from src.db.models import PlotOutline

class OutlineService:
    def __init__(self, db: Session):
        self.outline_repository = OutlineRepository(db)

    def get_outlines_by_novel(self, novel_id: int, branch_id: str = "main", skip: int = 0, limit: int = 100) -> List[OutlineResponse]:
        outlines = self.outline_repository.get_by_novel_id(novel_id, branch_id, skip, limit)
        return [OutlineResponse.from_orm(outline) for outline in outlines]

    def create_outline(self, outline: OutlineCreate) -> OutlineResponse:
        db_outline = PlotOutline(**outline.dict())
        created_outline = self.outline_repository.add(db_outline)
        return OutlineResponse.from_orm(created_outline)
