from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class NovelBase(BaseModel):
    title: str
    description: Optional[str] = None
    author: Optional[str] = None

class NovelCreate(NovelBase):
    pass

class NovelResponse(NovelBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

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
        from_attributes = True

class CharacterBase(BaseModel):
    name: str
    role: Optional[str] = None
    current_mood: Optional[str] = None

class CharacterCreate(CharacterBase):
    novel_id: int

class CharacterResponse(CharacterBase):
    id: int
    personality_traits: Optional[Any] = None
    skills: Optional[Any] = None
    assets: Optional[Any] = None
    status: Optional[Any] = None
    
    class Config:
        from_attributes = True

class OutlineBase(BaseModel):
    chapter_number: int
    scene_description: Optional[str] = None
    status: str = "pending"

class OutlineCreate(OutlineBase):
    novel_id: int
    branch_id: str = "main"

class OutlineResponse(OutlineBase):
    id: int
    branch_id: str
    
    class Config:
        from_attributes = True

class RelationshipBase(BaseModel):
    char_a_id: int
    char_b_id: int
    relation_type: str
    intimacy: float = 0.0

class RelationshipCreate(RelationshipBase):
    pass

class RelationshipResponse(RelationshipBase):
    id: int
    
    class Config:
        from_attributes = True

class WorldItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rarity: Optional[str]
    powers: Optional[Any]
    location: Optional[str]
    
    class Config:
        from_attributes = True

class NovelBibleResponse(BaseModel):
    id: int
    category: str
    key: str
    content: str
    importance: int
    
    class Config:
        from_attributes = True
