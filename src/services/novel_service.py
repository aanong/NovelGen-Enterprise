from typing import List
from sqlalchemy.orm import Session
from src.db.novel_repository import NovelRepository
from src.api.schemas import NovelResponse, NovelCreate
from src.db.models import Novel

class NovelService:
    def __init__(self, db: Session):
        self.novel_repository = NovelRepository(db)

    def get_novels(self, skip: int = 0, limit: int = 100) -> List[NovelResponse]:
        novels = self.novel_repository.get_all(skip=skip, limit=limit)
        return [NovelResponse.from_orm(novel) for novel in novels]

    def get_novel(self, novel_id: int) -> NovelResponse:
        novel = self.novel_repository.get(novel_id)
        if novel:
            return NovelResponse.from_orm(novel)
        return None

    def create_novel(self, novel: NovelCreate) -> NovelResponse:
        db_novel = Novel(**novel.dict())
        created_novel = self.novel_repository.add(db_novel)
        return NovelResponse.from_orm(created_novel)
