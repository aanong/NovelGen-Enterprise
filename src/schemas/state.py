from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from .style import StyleFeatures

class NovelBible(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    world_view: str = Field(description="世界观设定")
    core_settings: Dict[str, str] = Field(default_factory=dict, description="核心设定（如功法、等级、地理等）")
    style_vector: Optional[List[float]] = Field(None, description="文风特征向量")
    style_description: Optional[StyleFeatures] = Field(None, description="文风详细特征描述")

class WorldItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    description: Optional[str] = ""
    rarity: str = "Common"
    powers: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[str] = None

class CharacterState(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    personality_traits: Dict[str, Any] # MBTI, BigFive
    skills: List[str] = Field(default_factory=list, description="角色掌握的技能/功法")
    assets: Dict[str, Any] = Field(default_factory=dict, description="角色拥有的非实物资产")
    inventory: List[WorldItemSchema] = Field(default_factory=list, description="角色携带的物品")
    relationships: Dict[str, str]
    evolution_log: List[str]
    current_mood: str
    status: str = "Active"

class PlotPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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
    characters: Dict[str, CharacterState]
    world_items: List[WorldItemSchema] = Field(default_factory=list, description="世界中的关键物品（含在野和已领用的）")
    plot_progress: List[PlotPoint]
    current_plot_index: int = 0
    current_branch: str = Field(default="main", description="当前剧情分支 ID")
    current_novel_id: int = Field(description="当前小说 ID")
    last_chapter_id: Optional[int] = Field(None, description="上一章的数据库 ID，用于构建链表")
    branch_options: Optional[List[Dict[str, Any]]] = Field(None, description="当前节点的可选分支走向")
    memory_context: MemoryContext
    
    # 反重力规则上下文 (Rule 1-6)
    antigravity_context: AntigravityContext = Field(default_factory=AntigravityContext)
    
    # 运行时临时数据
    next_action: str = "init" # init, plan, write, review, revise, finalize
    current_draft: str = ""
    review_feedback: str = ""
    retry_count: int = 0
    max_retry_limit: int = 3  # Rule 5.1: 循环熔断阈值
    refined_context: List[str] = Field(default_factory=list, description="本章动态检索精炼后的上下文（RAG）")
    
    # 版本控制与审计
    state_version: str = Field(default="1.0.0", description="状态版本号，用于回滚和调试")
    last_checkpoint: Optional[str] = Field(None, description="最后一次检查点的序列化状态")
