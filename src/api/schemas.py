from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ChapterBase(BaseModel):
    title: Optional[str] = None
    chapter_number: int
    summary: Optional[str] = None
    branch_id: str = "main"

class ChapterCreate(ChapterBase):
    content: str
    novel_id: int

class ChapterResponse(ChapterBase):
    id: int
    content: Optional[str] = None
    created_at: Optional[datetime] = None
    scene_tags: Optional[List[str]] = None

    class Config:
        orm_mode = True

class CharacterBase(BaseModel):
    name: str
    role: Optional[str] = None
    current_mood: Optional[str] = None

class CharacterResponse(CharacterBase):
    id: int
    personality_traits: Optional[Any] = None
    skills: Optional[Any] = None
    assets: Optional[Any] = None
    status: Optional[Any] = None
    
    class Config:
        orm_mode = True

class OutlineBase(BaseModel):
    chapter_number: int
    scene_description: Optional[str] = None
    status: str = "pending"

class OutlineResponse(OutlineBase):
    id: int
    branch_id: str
    
    class Config:
        orm_mode = True
