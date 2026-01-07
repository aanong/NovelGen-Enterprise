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

class AntigravityContext(BaseModel):
    """反重力规则执行上下文"""
    last_rule_check: str = Field(default="", description="最后一次规则检查的时间戳")
    violated_rules: List[str] = Field(default_factory=list, description="违反的规则列表")
    character_anchors: Dict[str, List[str]] = Field(
        default_factory=dict, 
        description="人物灵魂锚定：{角色名: [禁忌行为列表]}"
    )
    scene_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="当前场景的强制约束（Rule 6）"
    )

class NGEState(BaseModel):
    """
    NovelGen-Enterprise 全局状态 Schema (State Management)
    遵循 Antigravity Rules 治理准则
    """
    novel_bible: NovelBible
    characters: Dict[str, character_state]
    plot_progress: List[PlotPoint]
    current_plot_index: int = 0
    memory_context: MemoryContext
    
    # 反重力规则上下文 (Rule 1-6)
    antigravity_context: AntigravityContext = Field(default_factory=AntigravityContext)
    
    # 运行时临时数据
    next_action: str = "init" # init, plan, write, review, revise, finalize
    current_draft: str = ""
    review_feedback: str = ""
    retry_count: int = 0
    max_retry_limit: int = 3  # Rule 5.1: 循环熔断阈值
    
    # 版本控制与审计
    state_version: str = Field(default="1.0.0", description="状态版本号，用于回滚和调试")
    last_checkpoint: Optional[str] = Field(None, description="最后一次检查点的序列化状态")
