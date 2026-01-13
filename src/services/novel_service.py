from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from src.db.models import Novel, Chapter
from pydantic import BaseModel
from datetime import datetime

# Define Pydantic models here or import them if they are shared.
# Since they were defined in the router, it's better to move them to a schemas file,
# but for now I'll accept dicts or Pydantic models as input/output to keep it simple
# or assume the service methods return ORM objects or simple types.
# Ideally, services should return ORM objects or DTOs, and the controller handles HTTP responses.

class NovelService:
    @staticmethod
    def create_novel(db: Session, novel_data: dict) -> Novel:
        db_novel = Novel(**novel_data)
        db.add(db_novel)
        db.commit()
        db.refresh(db_novel)
        return db_novel

    @staticmethod
    def get_novels(db: Session, skip: int = 0, limit: int = 100) -> List[Novel]:
        return db.query(Novel).offset(skip).limit(limit).all()

    @staticmethod
    def get_novel(db: Session, novel_id: int) -> Optional[Novel]:
        return db.query(Novel).filter(Novel.id == novel_id).first()

    @staticmethod
    def update_novel(db: Session, novel_id: int, novel_data: dict) -> Optional[Novel]:
        db_novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if db_novel is None:
            return None
        
        for key, value in novel_data.items():
            setattr(db_novel, key, value)
        
        db.commit()
        db.refresh(db_novel)
        return db_novel

    @staticmethod
    def delete_novel(db: Session, novel_id: int) -> bool:
        db_novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if db_novel is None:
            return False
        
        db.delete(db_novel)
        db.commit()
        return True

    @staticmethod
    def export_novel(db: Session, novel_id: int, branch_id: str = "main") -> Optional[Tuple[str, str]]:
        """
        Returns a tuple (filename, content) or None if novel not found.
        """
        novel = db.query(Novel).filter(Novel.id == novel_id).first()
        if not novel:
            return None
        
        chapters = db.query(Chapter).filter(
            Chapter.novel_id == novel_id,
            Chapter.branch_id == branch_id
        ).order_by(Chapter.chapter_number).all()
        
        content_lines = []
        content_lines.append(f"# {novel.title}\n\n")
        content_lines.append(f"**Author:** {novel.author or 'N/A'}\n")
        content_lines.append(f"**Branch:** {branch_id}\n\n")
        
        if not chapters:
            content_lines.append("*No chapters found.*")
        
        for chapter in chapters:
            title = chapter.title or f"Chapter {chapter.chapter_number}"
            text = chapter.content or "*(No Content)*"
            content_lines.append(f"## 第 {chapter.chapter_number} 章: {title}\n\n")
            content_lines.append(f"{text}\n\n")
            content_lines.append("---\n\n")
        
        full_text = "".join(content_lines)
        filename = f"{novel.title}_{branch_id}.md"
        
        return filename, full_text
