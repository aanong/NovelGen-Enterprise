from typing import List
from sqlalchemy.orm import Session
from src.db.chapter_repository import ChapterRepository
from src.api.schemas import ChapterResponse, ChapterCreate
from src.db.models import Chapter

class ChapterService:
    def __init__(self, db: Session):
        self.chapter_repository = ChapterRepository(db)

    def get_chapters_by_novel(self, novel_id: int, branch_id: str = "main", skip: int = 0, limit: int = 100) -> List[ChapterResponse]:
        chapters = self.chapter_repository.get_by_novel_id(novel_id, branch_id, skip, limit)
        return [ChapterResponse.from_orm(chapter) for chapter in chapters]

    def get_chapter(self, chapter_id: int) -> ChapterResponse:
        chapter = self.chapter_repository.get(chapter_id)
        if chapter:
            return ChapterResponse.from_orm(chapter)
        return None

    def create_chapter(self, chapter: ChapterCreate) -> ChapterResponse:
        db_chapter = Chapter(**chapter.dict())
        created_chapter = self.chapter_repository.add(db_chapter)
        return ChapterResponse.from_orm(created_chapter)
