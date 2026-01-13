from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from typing import List
from src.api.deps import get_db
from src.db.models import Novel
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from src.services.novel_service import NovelService

router = APIRouter()

class NovelBase(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    status: str = "ongoing"

class NovelCreate(NovelBase):
    pass

class NovelResponse(NovelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

@router.post("/", response_model=NovelResponse)
def create_novel(novel: NovelCreate, db: Session = Depends(get_db)):
    return NovelService.create_novel(db, novel.dict())

@router.get("/", response_model=List[NovelResponse])
def read_novels(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return NovelService.get_novels(db, skip, limit)

@router.get("/{novel_id}", response_model=NovelResponse)
def read_novel(novel_id: int, db: Session = Depends(get_db)):
    novel = NovelService.get_novel(db, novel_id)
    if novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return novel

@router.put("/{novel_id}", response_model=NovelResponse)
def update_novel(novel_id: int, novel: NovelCreate, db: Session = Depends(get_db)):
    updated_novel = NovelService.update_novel(db, novel_id, novel.dict())
    if updated_novel is None:
        raise HTTPException(status_code=404, detail="Novel not found")
    return updated_novel

@router.delete("/{novel_id}")
def delete_novel(novel_id: int, db: Session = Depends(get_db)):
    success = NovelService.delete_novel(db, novel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Novel not found")
    return {"message": "Novel deleted successfully"}

@router.get("/{novel_id}/export")
def export_novel_endpoint(novel_id: int, branch_id: str = "main", db: Session = Depends(get_db)):
    result = NovelService.export_novel(db, novel_id, branch_id)
    if not result:
        raise HTTPException(status_code=404, detail="Novel not found")
    
    filename, full_text = result
    
    # Encode filename for URL
    from urllib.parse import quote
    encoded_filename = quote(filename)
    
    return Response(
        content=full_text,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )
