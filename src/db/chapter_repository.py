from typing import List
from sqlalchemy.orm import Session
from src.db.models import Chapter
from src.db.repository import Repository

class ChapterRepository(Repository[Chapter]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get(self, id: int) -> Chapter:
        return self.db.query(Chapter).filter(Chapter.id == id).first()

    def get_all(self) -> List[Chapter]:
        return self.db.query(Chapter).all()

    def add(self, entity: Chapter) -> Chapter:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: Chapter):
        self.db.delete(entity)
        self.db.commit()

    def get_by_novel_id(self, novel_id: int, branch_id: str = "main", skip: int = 0, limit: int = 100) -> List[Chapter]:
        return self.db.query(Chapter).filter(
            Chapter.novel_id == novel_id,
            Chapter.branch_id == branch_id
        ).offset(skip).limit(limit).all()
