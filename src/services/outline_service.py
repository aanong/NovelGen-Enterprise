from typing import List, Optional
from sqlalchemy.orm import Session
from src.db.models import PlotOutline

class OutlineService:
    @staticmethod
    def get_outlines(db: Session, novel_id: int, branch_id: str = "main", skip: int = 0, limit: int = 100) -> List[PlotOutline]:
        return db.query(PlotOutline).filter(
            PlotOutline.novel_id == novel_id,
            PlotOutline.branch_id == branch_id
        ).order_by(PlotOutline.chapter_number).offset(skip).limit(limit).all()
