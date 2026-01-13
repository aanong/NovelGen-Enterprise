from typing import List
from sqlalchemy.orm import Session
from src.db.models import Character
from src.db.repository import Repository

class CharacterRepository(Repository[Character]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get(self, id: int) -> Character:
        return self.db.query(Character).filter(Character.id == id).first()

    def get_all(self) -> List[Character]:
        return self.db.query(Character).all()

    def add(self, entity: Character) -> Character:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: Character):
        self.db.delete(entity)
        self.db.commit()

    def get_by_novel_id(self, novel_id: int, skip: int = 0, limit: int = 100) -> List[Character]:
        return self.db.query(Character).filter(Character.novel_id == novel_id).offset(skip).limit(limit).all()
