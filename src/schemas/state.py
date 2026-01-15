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


class GrowthCurveType(str, Enum):
    """成长曲线类型"""
    LINEAR = "linear"               # 线性成长
    EXPONENTIAL = "exponential"     # 指数成长（大器晚成型）
    LOGARITHMIC = "logarithmic"     # 对数成长（天才早慧型）
    STEP = "step"                   # 阶梯成长（突破型）
    WAVE = "wave"                   # 波动成长（起伏型）


class MasteryStage(str, Enum):
    """技能掌握阶段"""
    UNAWARE = "unaware"             # 未知（不知道自己不会）
    NOVICE = "novice"               # 初学（知道自己不会）
    COMPETENT = "competent"         # 胜任（有意识地会）
    PROFICIENT = "proficient"       # 熟练（无意识地会）
    MASTER = "master"               # 大师（可以教授他人）
    TRANSCENDENT = "transcendent"   # 超凡（开创新境）


class AbilityLevel(BaseModel):
    """能力等级模型（增强版）"""
    model_config = ConfigDict(from_attributes=True)
    
    # 基础属性
    level: int = Field(default=1, ge=1, le=10, description="能力等级 1-10")
    proficiency: float = Field(default=0.0, ge=0.0, le=1.0, description="熟练度 0.0-1.0")
    description: str = Field(default="", description="能力描述")
    awakened_at_chapter: Optional[int] = Field(None, description="觉醒于第几章")
    
    # ========== 新增：成长系统 ==========
    
    # 掌握阶段
    mastery_stage: MasteryStage = Field(
        default=MasteryStage.NOVICE,
        description="当前掌握阶段"
    )
    
    # 成长曲线类型
    growth_curve: GrowthCurveType = Field(
        default=GrowthCurveType.LINEAR,
        description="成长曲线类型"
    )
    
    # 天赋系数（影响成长速度，0.5-2.0）
    talent_modifier: float = Field(
        default=1.0, ge=0.5, le=2.0,
        description="天赋系数"
    )
    
    # 成长瓶颈
    bottleneck: Optional[Dict[str, Any]] = Field(
        None,
        description="当前瓶颈，如：{'type': 'insight', 'description': '需要顿悟', 'chapter_stuck': 5}"
    )
    
    # 成长条件
    growth_conditions: List[str] = Field(
        default_factory=list,
        description="成长所需条件，如：['实战经验', '名师指点', '资源辅助']"
    )
    
    # 成长历史
    growth_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="成长历史记录"
    )
    
    # 关联能力（前置技能）
    prerequisites: List[str] = Field(
        default_factory=list,
        description="前置技能列表"
    )
    
    # 可解锁能力（后继技能）
    unlocks: List[str] = Field(
        default_factory=list,
        description="可解锁的后继技能"
    )
    
    def calculate_growth_rate(self, event_intensity: float = 0.5) -> float:
        """
        根据成长曲线计算成长速率
        
        Args:
            event_intensity: 事件强度 0.0-1.0
            
        Returns:
            成长速率
        """
        base_rate = event_intensity * self.talent_modifier
        
        if self.growth_curve == GrowthCurveType.LINEAR:
            return base_rate * 0.1
        elif self.growth_curve == GrowthCurveType.EXPONENTIAL:
            # 等级越高成长越快
            return base_rate * 0.05 * (1 + self.level * 0.1)
        elif self.growth_curve == GrowthCurveType.LOGARITHMIC:
            # 等级越高成长越慢
            import math
            return base_rate * 0.2 / (1 + math.log(self.level + 1))
        elif self.growth_curve == GrowthCurveType.STEP:
            # 只有达到阈值才成长
            return base_rate * 0.3 if self.proficiency >= 0.9 else 0
        else:  # WAVE
            # 波动成长
            import math
            return base_rate * 0.1 * (1 + math.sin(self.proficiency * math.pi))
        
        return base_rate * 0.1
    
    def can_level_up(self) -> bool:
        """检查是否可以升级"""
        if self.bottleneck:
            return False
        return self.proficiency >= 1.0 and self.level < 10
    
    def get_stage_description(self) -> str:
        """获取阶段描述"""
        stage_desc = {
            MasteryStage.UNAWARE: "尚未接触",
            MasteryStage.NOVICE: "初窥门径",
            MasteryStage.COMPETENT: "略有小成",
            MasteryStage.PROFICIENT: "驾轻就熟",
            MasteryStage.MASTER: "登堂入室",
            MasteryStage.TRANSCENDENT: "超凡入圣",
        }
        return stage_desc.get(self.mastery_stage, "未知")


class MindsetDimension(BaseModel):
    """
    思想维度模型
    表示角色的认知和思维方式
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 思维开放度（0.0-1.0）
    openness: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="思维开放度，接受新观念的程度"
    )
    
    # 思维深度（0.0-1.0）
    depth: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="思维深度，思考问题的深入程度"
    )
    
    # 情绪成熟度（0.0-1.0）
    emotional_maturity: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="情绪成熟度，情绪管理能力"
    )
    
    # 共情能力（0.0-1.0）
    empathy: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="共情能力"
    )
    
    # 决断力（0.0-1.0）
    decisiveness: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="决断力"
    )
    
    # 抗压能力（0.0-1.0）
    resilience: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="抗压能力"
    )
    
    # 领悟力（影响技能成长）
    insight: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="领悟力"
    )
    
    def get_overall_maturity(self) -> float:
        """计算整体成熟度"""
        return (
            self.openness + self.depth + self.emotional_maturity + 
            self.empathy + self.decisiveness + self.resilience + self.insight
        ) / 7
    
    def to_prompt_text(self) -> str:
        """转换为提示词文本"""
        maturity = self.get_overall_maturity()
        
        if maturity < 0.3:
            return "思想稚嫩，冲动易怒，缺乏深思"
        elif maturity < 0.5:
            return "思想初熟，有一定判断力，但仍有盲点"
        elif maturity < 0.7:
            return "思想成熟，能理性分析，懂得权衡"
        else:
            return "思想通达，洞察人心，从容应对"


class GrowthMilestone(BaseModel):
    """
    成长里程碑模型
    记录角色的重要成长节点
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 里程碑类型
    milestone_type: str = Field(
        description="类型：skill_awakening/level_up/insight/mindset_shift/value_change"
    )
    
    # 章节
    chapter: int = Field(description="发生章节")
    
    # 描述
    description: str = Field(description="里程碑描述")
    
    # 触发事件
    trigger_event: str = Field(default="", description="触发事件")
    
    # 影响
    impact: Dict[str, Any] = Field(
        default_factory=dict,
        description="对角色的影响"
    )
    
    # 是否为关键里程碑
    is_major: bool = Field(default=False)


class CharacterGrowthSystem(BaseModel):
    """
    角色成长系统
    统一管理技能、思想、价值观的成长
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 思想维度
    mindset: MindsetDimension = Field(
        default_factory=MindsetDimension,
        description="思想维度"
    )
    
    # 成长里程碑
    milestones: List[GrowthMilestone] = Field(
        default_factory=list,
        description="成长里程碑记录"
    )
    
    # 当前成长主题
    current_growth_theme: Optional[str] = Field(
        None,
        description="当前成长主题，如：'学会信任'、'克服恐惧'"
    )
    
    # 成长潜力（剩余可成长空间）
    growth_potential: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="成长潜力"
    )
    
    # 成长阻碍
    growth_blockers: List[str] = Field(
        default_factory=list,
        description="成长阻碍，如：'创伤未愈'、'执念太深'"
    )
    
    # 成长加速器
    growth_accelerators: List[str] = Field(
        default_factory=list,
        description="成长加速因素，如：'良师益友'、'逆境磨练'"
    )
    
    # 驾驭曲线（技能熟练度随时间的变化）
    proficiency_curve: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="各技能的熟练度变化曲线"
    )
    
    def record_milestone(
        self,
        milestone_type: str,
        chapter: int,
        description: str,
        trigger: str = "",
        impact: Dict[str, Any] = None,
        is_major: bool = False
    ):
        """记录成长里程碑"""
        self.milestones.append(GrowthMilestone(
            milestone_type=milestone_type,
            chapter=chapter,
            description=description,
            trigger_event=trigger,
            impact=impact or {},
            is_major=is_major
        ))
    
    def update_proficiency_curve(self, skill_name: str, new_value: float):
        """更新驾驭曲线"""
        if skill_name not in self.proficiency_curve:
            self.proficiency_curve[skill_name] = []
        self.proficiency_curve[skill_name].append(new_value)
    
    def get_growth_summary(self) -> str:
        """获取成长摘要"""
        maturity = self.mindset.get_overall_maturity()
        major_milestones = [m for m in self.milestones if m.is_major]
        
        summary_parts = [
            f"思想成熟度：{maturity:.0%}",
            f"关键成长节点：{len(major_milestones)}个",
        ]
        
        if self.current_growth_theme:
            summary_parts.append(f"当前成长主题：{self.current_growth_theme}")
        
        if self.growth_blockers:
            summary_parts.append(f"成长阻碍：{', '.join(self.growth_blockers)}")
        
        return "；".join(summary_parts)
    
    def to_prompt_text(self, character_name: str) -> str:
        """转换为提示词文本"""
        parts = [f"【{character_name}的成长状态】"]
        
        # 思想状态
        parts.append(f"思想：{self.mindset.to_prompt_text()}")
        
        # 成长主题
        if self.current_growth_theme:
            parts.append(f"成长主题：{self.current_growth_theme}")
        
        # 阻碍
        if self.growth_blockers:
            parts.append(f"成长阻碍：{', '.join(self.growth_blockers[:2])}")
        
        return "；".join(parts)


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


# ============ 价值观系统增强 ============

class ValueBelief(BaseModel):
    """
    价值信念模型
    表达人物的核心信念及其来源和约束
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 价值观名称
    value_name: str = Field(description="价值观名称，如：正义、家族、生存、自由")
    
    # 坚定程度（0.0-1.0）
    strength: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="坚定程度"
    )
    
    # 信念来源
    origin: str = Field(
        default="",
        description="信念来源，如：'童年经历'、'导师教导'、'亲身体验'、'血脉传承'"
    )
    
    # 是否可动摇
    can_be_shaken: bool = Field(
        default=True,
        description="此信念是否可以被动摇"
    )
    
    # 动摇条件
    shake_conditions: List[str] = Field(
        default_factory=list,
        description="可能动摇此信念的条件"
    )
    
    # 相关行为指导
    related_actions: Dict[str, str] = Field(
        default_factory=lambda: {
            "must_do": "",      # 必须做的事
            "must_not_do": "",  # 绝不能做的事
            "will_sacrifice": "", # 愿意为之牺牲的
        },
        description="此价值观导致的行为约束"
    )
    
    # 对立价值观
    opposing_values: List[str] = Field(
        default_factory=list,
        description="与此价值观对立的其他价值观"
    )
    
    # 历史变化记录
    change_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="价值观强度变化历史"
    )
    
    def to_prompt_text(self) -> str:
        """转换为提示词文本"""
        strength_desc = "坚定" if self.strength > 0.7 else "动摇" if self.strength < 0.3 else "中等"
        parts = [f"{self.value_name}({strength_desc})"]
        
        if self.related_actions.get("must_not_do"):
            parts.append(f"绝不{self.related_actions['must_not_do']}")
        
        return "；".join(parts)


class ValueConflict(BaseModel):
    """
    价值冲突模型
    表示两难抉择的情境
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 冲突的价值观
    values_in_conflict: List[str] = Field(
        description="冲突的价值观列表，如：['正义', '亲情']"
    )
    
    # 冲突情境描述
    situation: str = Field(
        description="触发冲突的情境描述"
    )
    
    # 冲突强度（0.0-1.0）
    intensity: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="冲突的激烈程度"
    )
    
    # 可能的选择
    possible_choices: List[Dict[str, str]] = Field(
        default_factory=list,
        description="可能的选择及其后果"
    )
    
    # 是否已解决
    is_resolved: bool = Field(default=False)
    
    # 解决方式
    resolution: Optional[str] = Field(None, description="解决方式")
    
    # 解决后的影响
    resolution_impact: Dict[str, Any] = Field(
        default_factory=dict,
        description="解决后对价值观的影响"
    )
    
    # 触发章节
    triggered_at_chapter: Optional[int] = Field(None)
    
    # 解决章节
    resolved_at_chapter: Optional[int] = Field(None)


class ValueSystem(BaseModel):
    """
    完整的价值观系统
    管理角色的所有价值信念和冲突
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 核心价值观列表
    beliefs: List[ValueBelief] = Field(
        default_factory=list,
        description="核心价值观列表"
    )
    
    # 当前活跃的价值冲突
    active_conflicts: List[ValueConflict] = Field(
        default_factory=list,
        description="当前未解决的价值冲突"
    )
    
    # 历史冲突记录
    resolved_conflicts: List[ValueConflict] = Field(
        default_factory=list,
        description="已解决的价值冲突历史"
    )
    
    # 价值观优先级（在冲突时的默认倾向）
    priority_order: List[str] = Field(
        default_factory=list,
        description="价值观优先级顺序"
    )
    
    # 道德底线（绝对不可违背的）
    moral_absolutes: List[str] = Field(
        default_factory=list,
        description="绝对不可违背的道德底线"
    )
    
    def get_belief(self, value_name: str) -> Optional[ValueBelief]:
        """获取指定的价值信念"""
        for belief in self.beliefs:
            if belief.value_name == value_name:
                return belief
        return None
    
    def get_dominant_value(self) -> Optional[ValueBelief]:
        """获取当前最强的价值观"""
        if not self.beliefs:
            return None
        return max(self.beliefs, key=lambda b: b.strength)
    
    def check_action_violation(self, action: str) -> List[str]:
        """
        检查某个行为是否违反价值观
        
        Args:
            action: 行为描述
            
        Returns:
            违反的价值观列表
        """
        violations = []
        action_lower = action.lower()
        
        for belief in self.beliefs:
            must_not = belief.related_actions.get("must_not_do", "")
            if must_not and must_not.lower() in action_lower:
                violations.append(belief.value_name)
        
        for absolute in self.moral_absolutes:
            if absolute.lower() in action_lower:
                violations.append(f"道德底线：{absolute}")
        
        return violations
    
    def detect_potential_conflict(
        self, 
        situation: str
    ) -> Optional[ValueConflict]:
        """
        检测情境中可能的价值冲突
        
        Args:
            situation: 情境描述
            
        Returns:
            检测到的价值冲突
        """
        # 简单的冲突检测逻辑
        conflicting_pairs = [
            (["正义", "亲情"], ["亲人犯罪", "家人作恶"]),
            (["忠诚", "真相"], ["隐瞒", "欺骗上级"]),
            (["生存", "荣誉"], ["苟活", "屈辱求生"]),
            (["爱情", "责任"], ["私奔", "抛下责任"]),
            (["复仇", "宽恕"], ["放下仇恨", "以德报怨"]),
        ]
        
        situation_lower = situation.lower()
        
        for values, triggers in conflicting_pairs:
            # 检查是否拥有这些价值观
            has_values = all(
                self.get_belief(v) for v in values
            )
            
            if has_values:
                for trigger in triggers:
                    if trigger in situation_lower:
                        return ValueConflict(
                            values_in_conflict=values,
                            situation=situation,
                            intensity=0.7
                        )
        
        return None
    
    def to_prompt_text(self, character_name: str) -> str:
        """转换为提示词文本"""
        parts = [f"【{character_name}的价值观系统】"]
        
        # 核心价值观
        if self.beliefs:
            beliefs_text = ", ".join([b.to_prompt_text() for b in self.beliefs[:3]])
            parts.append(f"核心信念：{beliefs_text}")
        
        # 道德底线
        if self.moral_absolutes:
            parts.append(f"道德底线：{', '.join(self.moral_absolutes)}")
        
        # 当前冲突
        if self.active_conflicts:
            conflict = self.active_conflicts[0]
            parts.append(f"当前冲突：{' vs '.join(conflict.values_in_conflict)}")
        
        return "；".join(parts)


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
    
    # 价值观/信念系统（0.0-1.0 表示坚定程度）- 保留向后兼容
    core_values: Dict[str, float] = Field(
        default_factory=dict,
        description="核心价值观，如 {'正义': 0.8, '家族': 0.9, '复仇': 0.3}"
    )
    
    # ========== 新增：完整价值观系统 ==========
    value_system: ValueSystem = Field(
        default_factory=ValueSystem,
        description="完整的价值观系统（包含信念详情和冲突管理）"
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
    
    # ========== 人物心理描写系统 ==========
    psychology: CharacterPsychology = Field(
        default_factory=CharacterPsychology,
        description="人物心理状态"
    )
    
    # ========== 新增：综合成长系统 ==========
    growth_system: CharacterGrowthSystem = Field(
        default_factory=CharacterGrowthSystem,
        description="角色成长系统（思想、技能、价值观）"
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
