from typing import List
from sqlalchemy.orm import Session
from src.db.models import WorldItem, NovelBible
from src.db.repository import Repository

class WorldItemRepository(Repository[WorldItem]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get(self, id: int) -> WorldItem:
        return self.db.query(WorldItem).filter(WorldItem.id == id).first()

    def get_all(self) -> List[WorldItem]:
        return self.db.query(WorldItem).all()

    def add(self, entity: WorldItem) -> WorldItem:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: WorldItem):
        self.db.delete(entity)
        self.db.commit()

    def get_by_novel_id(self, novel_id: int) -> List[WorldItem]:
        return self.db.query(WorldItem).filter(WorldItem.novel_id == novel_id).all()

class NovelBibleRepository(Repository[NovelBible]):
    def __init__(self, db: Session):
        super().__init__(db)

    def get(self, id: int) -> NovelBible:
        return self.db.query(NovelBible).filter(NovelBible.id == id).first()

    def get_all(self) -> List[NovelBible]:
        return self.db.query(NovelBible).all()

    def add(self, entity: NovelBible) -> NovelBible:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: NovelBible):
        self.db.delete(entity)
        self.db.commit()

    def get_by_novel_id(self, novel_id: int) -> List[NovelBible]:
        return self.db.query(NovelBible).filter(NovelBible.novel_id == novel_id).all()
