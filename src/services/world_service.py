from typing import List
from sqlalchemy.orm import Session
from src.db.world_repository import WorldItemRepository, NovelBibleRepository
from src.api.schemas import WorldItemResponse, NovelBibleResponse

class WorldService:
    def __init__(self, db: Session):
        self.world_item_repository = WorldItemRepository(db)
        self.novel_bible_repository = NovelBibleRepository(db)

    def get_world_items(self, novel_id: int) -> List[WorldItemResponse]:
        items = self.world_item_repository.get_by_novel_id(novel_id)
        return [WorldItemResponse.from_orm(item) for item in items]

    def get_bible_entries(self, novel_id: int) -> List[NovelBibleResponse]:
        entries = self.novel_bible_repository.get_by_novel_id(novel_id)
        return [NovelBibleResponse.from_orm(entry) for entry in entries]
