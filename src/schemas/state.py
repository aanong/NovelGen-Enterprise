from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from .style import StyleFeatures

class NovelBible(BaseModel):
    world_view: str = Field(description="世界观设定")
    core_settings: Dict[str, str] = Field(default_factory=dict, description="核心设定（如功法、等级、地理等）")
    style_vector: Optional[List[float]] = Field(None, description="文风特征向量")
    style_description: Optional[StyleFeatures] = Field(None, description="文风详细特征描述")

class character_state(BaseModel):
    name: str
    personality_traits: Dict[str, Any] # MBTI, BigFive
    relationships: Dict[str, str]
    evolution_log: List[str]
    current_mood: str
    status: str = "Active"

class PlotPoint(BaseModel):
    id: str
    title: str
    description: str
    key_events: List[str]
    is_completed: bool = False
    chapter_index: Optional[int] = None

class MemoryContext(BaseModel):
    recent_summaries: List[str] = Field(default_factory=list, description="最近N章的摘要")
    global_foreshadowing: List[str] = Field(default_factory=list, description="全局关键伏笔")

class NGEState(BaseModel):
    """
    NovelGen-Enterprise 全局状态 Schema (State Management)
    """
    novel_bible: NovelBible
    characters: Dict[str, character_state]
    plot_progress: List[PlotPoint]
    current_plot_index: int = 0
    memory_context: MemoryContext
    
    # 运行时临时数据
    next_action: str = "init" # init, plan, write, review, revise, finalize
    current_draft: str = ""
    review_feedback: str = ""
    retry_count: int = 0
