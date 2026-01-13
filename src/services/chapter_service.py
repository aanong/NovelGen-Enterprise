from typing import List, Optional
from sqlalchemy.orm import Session
from src.db.models import Chapter

class ChapterService:
    @staticmethod
    def get_chapters(db: Session, novel_id: int, branch_id: str = "main", skip: int = 0, limit: int = 100) -> List[Chapter]:
        return db.query(Chapter).filter(
            Chapter.novel_id == novel_id,
            Chapter.branch_id == branch_id
        ).order_by(Chapter.chapter_number).offset(skip).limit(limit).all()

    @staticmethod
    def get_chapter(db: Session, chapter_id: int) -> Optional[Chapter]:
        return db.query(Chapter).filter(Chapter.id == chapter_id).first()
