from typing import List
from sqlalchemy.orm import Session
from src.db.models import Novel
from src.db.repository import Repository

class NovelRepository(Repository[Novel]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get(self, id: int) -> Novel:
        return self.db.query(Novel).filter(Novel.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Novel]:
        return self.db.query(Novel).offset(skip).limit(limit).all()

    def add(self, entity: Novel) -> Novel:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: Novel):
        self.db.delete(entity)
        self.db.commit()
