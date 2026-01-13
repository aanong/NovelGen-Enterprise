from typing import List
from sqlalchemy.orm import Session
from src.db.models import PlotOutline
from src.db.repository import Repository

class OutlineRepository(Repository[PlotOutline]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get(self, id: int) -> PlotOutline:
        return self.db.query(PlotOutline).filter(PlotOutline.id == id).first()

    def get_all(self) -> List[PlotOutline]:
        return self.db.query(PlotOutline).all()

    def add(self, entity: PlotOutline) -> PlotOutline:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: PlotOutline):
        self.db.delete(entity)
        self.db.commit()

    def get_by_novel_id(self, novel_id: int, branch_id: str = "main", skip: int = 0, limit: int = 100) -> List[PlotOutline]:
        return self.db.query(PlotOutline).filter(
            PlotOutline.novel_id == novel_id,
            PlotOutline.branch_id == branch_id
        ).offset(skip).limit(limit).all()
