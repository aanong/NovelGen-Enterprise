from typing import List
from sqlalchemy.orm import Session
from src.db.models import WorldItem, NovelBible

class WorldService:
    @staticmethod
    def get_world_items(db: Session, novel_id: int) -> List[WorldItem]:
        return db.query(WorldItem).filter(WorldItem.novel_id == novel_id).all()

    @staticmethod
    def get_bible_entries(db: Session, novel_id: int) -> List[NovelBible]:
        return db.query(NovelBible).filter(NovelBible.novel_id == novel_id).all()
