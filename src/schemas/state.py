from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from enum import Enum
from .style import StyleFeatures


class ArcType(str, Enum):
    """人物弧光类型"""
    POSITIVE = "positive"           # 正向成长（如从懦弱到勇敢）
    NEGATIVE = "negative"           # 负向堕落（如从善良到黑化）
    FLAT = "flat"                   # 扁平弧光（坚守信念，影响他人）
    TRANSFORMATION = "transformation"  # 彻底转变（如身份认知颠覆）


class KeyEventType(str, Enum):
    """关键事件类型"""
    TRAUMA = "trauma"               # 创伤事件
    EPIPHANY = "epiphany"           # 顿悟时刻
    DECISION = "decision"           # 重大决定
    LOSS = "loss"                   # 失去（亲人、朋友、信仰）
    GAIN = "gain"                   # 获得（力量、认可、真相）
    BETRAYAL = "betrayal"           # 背叛（被背叛或背叛他人）
    SACRIFICE = "sacrifice"         # 牺牲
    CONFRONTATION = "confrontation" # 直面恐惧/阴影


class AbilityLevel(BaseModel):
    """能力等级模型"""
    model_config = ConfigDict(from_attributes=True)
    level: int = Field(default=1, ge=1, le=10, description="能力等级 1-10")
    proficiency: float = Field(default=0.0, ge=0.0, le=1.0, description="熟练度 0.0-1.0")
    description: str = Field(default="", description="能力描述")
    awakened_at_chapter: Optional[int] = Field(None, description="觉醒于第几章")


class CharacterArcMilestone(BaseModel):
    """人物弧光里程碑"""
    model_config = ConfigDict(from_attributes=True)
    chapter_range: List[int] = Field(description="章节范围 [start, end]")
    description: str = Field(description="里程碑描述")
    trigger_event: Optional[str] = Field(None, description="触发事件类型")
    expected_changes: Dict[str, Any] = Field(default_factory=dict, description="预期变化")
    is_completed: bool = Field(default=False)


class CharacterArcSchema(BaseModel):
    """人物弧光定义"""
    model_config = ConfigDict(from_attributes=True)
    arc_type: ArcType = Field(default=ArcType.POSITIVE, description="弧光类型")
    starting_state: Dict[str, Any] = Field(description="起点状态")
    target_state: Dict[str, Any] = Field(description="目标状态")
    milestones: List[CharacterArcMilestone] = Field(default_factory=list, description="关键里程碑")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="当前进度")
    current_milestone_index: int = Field(default=0)
    status: str = Field(default="active")


class KeyEventSchema(BaseModel):
    """关键事件"""
    model_config = ConfigDict(from_attributes=True)
    event_type: KeyEventType
    chapter_number: int
    description: str
    impact: Dict[str, Any] = Field(default_factory=dict, description="事件影响")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="影响强度")


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


class SpeechStyle(BaseModel):
    """
    人物语言风格模型
    用于控制角色对话的独特性
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 说话风格（如：文雅、粗犷、阴阳怪气、冷淡、热情、学究气）
    speech_pattern: Optional[str] = Field(None, description="说话风格")
    
    # 口头禅/语言习惯
    verbal_tics: List[str] = Field(
        default_factory=list, 
        description="口头禅列表，如：['有趣', '哼，愚蠢']"
    )
    
    # 语气修饰词偏好
    tone_modifiers: Dict[str, Any] = Field(
        default_factory=dict,
        description="语气特点，如：{'常用语气词': ['嘛', '呢'], '句式特点': '喜欢用反问句'}"
    )
    
    # 对话风格详细描述
    dialogue_style_description: Optional[str] = Field(
        None, 
        description="对话风格的详细描述，供 LLM 参考"
    )
    
    def to_prompt_text(self, character_name: str) -> str:
        """
        将语言风格转换为提示词文本
        
        Args:
            character_name: 角色名称
            
        Returns:
            格式化的提示词文本
        """
        parts = []
        
        if self.speech_pattern:
            parts.append(f"说话风格：{self.speech_pattern}")
        
        if self.verbal_tics:
            parts.append(f"口头禅：{', '.join(self.verbal_tics)}")
        
        if self.tone_modifiers:
            if "常用语气词" in self.tone_modifiers:
                parts.append(f"常用语气词：{', '.join(self.tone_modifiers['常用语气词'])}")
            if "句式特点" in self.tone_modifiers:
                parts.append(f"句式特点：{self.tone_modifiers['句式特点']}")
            if "称呼习惯" in self.tone_modifiers:
                parts.append(f"称呼习惯：{self.tone_modifiers['称呼习惯']}")
        
        if self.dialogue_style_description:
            parts.append(f"对话风格：{self.dialogue_style_description}")
        
        if not parts:
            return ""
        
        return f"【{character_name}的语言风格】" + "；".join(parts)


class CharacterPsychology(BaseModel):
    """
    人物心理描写增强模型
    用于深层心理状态的表达
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 内心冲突列表（如：责任与情感的矛盾、理想与现实的冲突）
    inner_conflicts: List[str] = Field(
        default_factory=list,
        description="当前面临的内心冲突"
    )
    
    # 潜意识恐惧
    subconscious_fears: List[str] = Field(
        default_factory=list,
        description="潜意识中的恐惧，如：'被抛弃'、'失去控制'"
    )
    
    # 心理防御机制
    defense_mechanisms: List[str] = Field(
        default_factory=list,
        description="心理防御机制，如：'否认'、'投射'、'合理化'、'升华'"
    )
    
    # 心理创伤
    psychological_wounds: List[str] = Field(
        default_factory=list,
        description="心理创伤，如：'童年被遗弃'、'信任被背叛'"
    )
    
    # 当前心理主题
    current_psychological_theme: Optional[str] = Field(
        None,
        description="当前章节的心理主题，如：'自我怀疑'、'寻求认同'"
    )
    
    def to_prompt_text(self, character_name: str) -> str:
        """将心理状态转换为提示词文本"""
        parts = []
        
        if self.inner_conflicts:
            parts.append(f"内心冲突：{', '.join(self.inner_conflicts)}")
        
        if self.subconscious_fears:
            parts.append(f"潜意识恐惧：{', '.join(self.subconscious_fears)}")
        
        if self.defense_mechanisms:
            parts.append(f"防御机制：{', '.join(self.defense_mechanisms)}")
        
        if self.current_psychological_theme:
            parts.append(f"当前心理主题：{self.current_psychological_theme}")
        
        if not parts:
            return ""
        
        return f"【{character_name}的心理状态】" + "；".join(parts)


class CharacterState(BaseModel):
    """
    角色状态模型
    支持动态性格演化、能力成长、价值观变迁
    """
    model_config = ConfigDict(from_attributes=True)
    name: str
    
    # 基础属性
    personality_traits: Dict[str, Any] = Field(
        default_factory=dict, 
        description="静态性格特征（MBTI, BigFive, 核心动机）"
    )
    
    # 动态性格维度（可随剧情演化，0.0-1.0）
    personality_dynamics: Dict[str, float] = Field(
        default_factory=lambda: {
            "courage": 0.5,      # 勇气（vs 恐惧）
            "rationality": 0.5, # 理性（vs 冲动）
            "empathy": 0.5,     # 同理心（vs 冷漠）
            "openness": 0.5,    # 开放性（vs 保守）
            "trust": 0.5,       # 信任（vs 多疑）
        },
        description="动态性格维度，可随剧情变化"
    )
    
    # 价值观/信念系统（0.0-1.0 表示坚定程度）
    core_values: Dict[str, float] = Field(
        default_factory=dict,
        description="核心价值观，如 {'正义': 0.8, '家族': 0.9, '复仇': 0.3}"
    )
    
    # 能力系统（带等级和熟练度）
    skills: List[str] = Field(default_factory=list, description="角色掌握的技能/功法名称列表")
    ability_levels: Dict[str, AbilityLevel] = Field(
        default_factory=dict,
        description="能力等级详情，键为技能名"
    )
    
    # 核心内在驱动
    core_need: Optional[str] = Field(None, description="核心需求（如'被认可'、'自我救赎'）")
    core_flaw: Optional[str] = Field(None, description="核心缺陷（如'傲慢'、'恐惧亲密'）")
    
    # 人物弧光
    character_arc: Optional[CharacterArcSchema] = Field(None, description="人物弧光规划")
    
    # 关键事件历史
    key_events: List[KeyEventSchema] = Field(default_factory=list, description="经历的关键事件")
    
    # ========== 人物语言风格系统（新增）==========
    speech_style: SpeechStyle = Field(
        default_factory=SpeechStyle,
        description="人物语言风格"
    )
    
    # ========== 人物心理描写系统（新增）==========
    psychology: CharacterPsychology = Field(
        default_factory=CharacterPsychology,
        description="人物心理状态"
    )
    
    # 原有字段
    assets: Dict[str, Any] = Field(default_factory=dict, description="角色拥有的非实物资产")
    inventory: List[WorldItemSchema] = Field(default_factory=list, description="角色携带的物品")
    relationships: Dict[str, str] = Field(default_factory=dict)
    evolution_log: List[str] = Field(default_factory=list)
    current_mood: str = Field(default="平静")
    status: Dict[str, Any] = Field(default_factory=lambda: {"is_active": True, "reason": "Active"})

class PlotPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    description: str
    key_events: List[str]
    is_completed: bool = False
    chapter_index: Optional[int] = None

class ForeshadowingStatus(str, Enum):
    """伏笔状态枚举"""
    PLANTED = "planted"         # 已埋设
    ADVANCED = "advanced"       # 已推进
    RESOLVED = "resolved"       # 已回收
    ABANDONED = "abandoned"     # 已放弃


class ForeshadowingType(str, Enum):
    """伏笔类型枚举"""
    CHARACTER = "character"     # 人物伏笔
    PLOT = "plot"               # 剧情伏笔
    ITEM = "item"               # 道具伏笔
    MYSTERY = "mystery"         # 谜团伏笔
    PROPHECY = "prophecy"       # 预言伏笔


class ForeshadowingSchema(BaseModel):
    """
    结构化伏笔模型
    用于 State 中的伏笔管理
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: Optional[int] = Field(None, description="数据库 ID")
    content: str = Field(description="伏笔内容描述")
    hint_text: Optional[str] = Field(None, description="埋设时的暗示文本")
    
    # 时间线
    created_at_chapter: int = Field(description="埋设章节")
    expected_resolve_chapter: Optional[int] = Field(None, description="预期回收章节")
    
    # 状态与类型
    status: ForeshadowingStatus = Field(default=ForeshadowingStatus.PLANTED)
    foreshadowing_type: ForeshadowingType = Field(default=ForeshadowingType.PLOT)
    importance: int = Field(default=5, ge=1, le=10, description="重要性 1-10")
    
    # 关联
    related_characters: List[str] = Field(default_factory=list)
    related_items: List[str] = Field(default_factory=list)
    
    # 回收条件
    resolve_condition: Optional[str] = Field(None, description="回收条件描述")
    resolve_strategy: Optional[str] = Field(None, description="回收策略建议")
    
    # 推进记录
    advancement_log: List[Dict[str, Any]] = Field(default_factory=list)


class MemoryContext(BaseModel):
    recent_summaries: List[str] = Field(default_factory=list, description="最近N章的摘要")
    global_foreshadowing: List[str] = Field(default_factory=list, description="全局关键伏笔（兼容旧格式）")
    
    # 结构化伏笔管理（新增）
    structured_foreshadowing: List[ForeshadowingSchema] = Field(
        default_factory=list, 
        description="结构化伏笔列表"
    )
    
    def get_active_foreshadowing(self) -> List[ForeshadowingSchema]:
        """获取活跃的伏笔"""
        return [
            f for f in self.structured_foreshadowing 
            if f.status in [ForeshadowingStatus.PLANTED, ForeshadowingStatus.ADVANCED]
        ]
    
    def get_overdue_foreshadowing(self, current_chapter: int) -> List[ForeshadowingSchema]:
        """获取过期未回收的伏笔"""
        return [
            f for f in self.get_active_foreshadowing()
            if f.expected_resolve_chapter and f.expected_resolve_chapter < current_chapter
        ]
    
    def get_due_soon_foreshadowing(
        self, 
        current_chapter: int, 
        lookahead: int = 3
    ) -> List[ForeshadowingSchema]:
        """获取即将到期的伏笔"""
        return [
            f for f in self.get_active_foreshadowing()
            if f.expected_resolve_chapter 
            and current_chapter <= f.expected_resolve_chapter <= current_chapter + lookahead
        ]

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
