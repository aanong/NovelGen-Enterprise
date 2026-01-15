"""
文风与写作技法模型
提供完整的文笔控制能力
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from enum import Enum


class PerspectiveType(str, Enum):
    """视角类型枚举"""
    FIRST_PERSON = "first_person"           # 第一人称
    THIRD_LIMITED = "third_limited"         # 第三人称限制视角
    THIRD_OMNISCIENT = "third_omniscient"   # 第三人称全知视角
    MULTIPLE_POV = "multiple_pov"           # 多视角切换


class DescriptionType(str, Enum):
    """描写类型枚举"""
    ENVIRONMENT = "environment"     # 环境描写
    ACTION = "action"               # 动作描写
    PSYCHOLOGY = "psychology"       # 心理描写
    DIALOGUE = "dialogue"           # 对话描写
    APPEARANCE = "appearance"       # 外貌描写
    SENSORY = "sensory"             # 感官描写


class AtmosphereType(str, Enum):
    """氛围类型枚举"""
    TENSE = "tense"                 # 紧张
    HORROR = "horror"               # 恐怖
    WARM = "warm"                   # 温馨
    MELANCHOLY = "melancholy"       # 忧郁
    EPIC = "epic"                   # 史诗
    MYSTERIOUS = "mysterious"       # 神秘
    ROMANTIC = "romantic"           # 浪漫
    PEACEFUL = "peaceful"           # 平静


class WritingTechnique(BaseModel):
    """
    写作技法模型
    定义具体的写作手法和使用指导
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 技法类型（如：白描、细描、蒙太奇、意识流、留白等）
    technique_type: str = Field(description="写作技法类型")
    
    # 适用场景
    applicable_scenes: List[str] = Field(
        default_factory=list,
        description="适用场景列表，如：['战斗', '离别', '顿悟']"
    )
    
    # 技法说明
    description: str = Field(default="", description="技法详细说明")
    
    # 使用示例
    example: str = Field(default="", description="使用示例")
    
    # 禁忌模式
    avoid_patterns: List[str] = Field(
        default_factory=list,
        description="使用此技法时应避免的模式"
    )
    
    # 配合技法
    complementary_techniques: List[str] = Field(
        default_factory=list,
        description="可配合使用的其他技法"
    )


class DescriptionBalance(BaseModel):
    """
    描写平衡模型
    控制不同描写类型的比例
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 环境描写比例（0.0-1.0）
    environment_ratio: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="环境描写建议占比"
    )
    
    # 动作描写比例
    action_ratio: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="动作描写建议占比"
    )
    
    # 心理描写比例
    psychology_ratio: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="心理描写建议占比"
    )
    
    # 对话比例
    dialogue_ratio: float = Field(
        default=0.3, ge=0.0, le=1.0,
        description="对话建议占比"
    )
    
    # 场景特定调整
    scene_adjustments: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: {
            "Action": {"action_ratio": 0.5, "dialogue_ratio": 0.2, "psychology_ratio": 0.1},
            "Emotional": {"psychology_ratio": 0.4, "dialogue_ratio": 0.3, "action_ratio": 0.1},
            "Dialogue": {"dialogue_ratio": 0.6, "psychology_ratio": 0.2, "action_ratio": 0.1},
        },
        description="不同场景的描写比例调整"
    )
    
    def get_adjusted_balance(self, scene_type: str) -> Dict[str, float]:
        """根据场景类型获取调整后的描写平衡"""
        base = {
            "environment": self.environment_ratio,
            "action": self.action_ratio,
            "psychology": self.psychology_ratio,
            "dialogue": self.dialogue_ratio,
        }
        
        if scene_type in self.scene_adjustments:
            adjustments = self.scene_adjustments[scene_type]
            for key in ["environment", "action", "psychology", "dialogue"]:
                ratio_key = f"{key}_ratio"
                if ratio_key in adjustments:
                    base[key] = adjustments[ratio_key]
        
        return base


class AtmosphereControl(BaseModel):
    """
    氛围控制模型
    用于渲染特定场景氛围
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 目标氛围
    target_atmosphere: AtmosphereType = Field(
        default=AtmosphereType.PEACEFUL,
        description="目标氛围类型"
    )
    
    # 氛围关键词
    atmosphere_keywords: List[str] = Field(
        default_factory=list,
        description="渲染氛围的推荐关键词"
    )
    
    # 氛围禁忌词
    forbidden_words: List[str] = Field(
        default_factory=list,
        description="破坏氛围的禁忌词"
    )
    
    # 感官强调（五感中强调哪些）
    sensory_emphasis: List[str] = Field(
        default_factory=lambda: ["视觉", "听觉"],
        description="强调的感官描写，如：['视觉', '听觉', '触觉', '嗅觉', '味觉']"
    )
    
    # 色调偏好
    color_palette: List[str] = Field(
        default_factory=list,
        description="氛围色调，如：['暗红', '深蓝', '惨白']"
    )
    
    # 节奏特征
    rhythm_hint: str = Field(
        default="",
        description="氛围节奏提示，如：'急促短句' 或 '悠长舒缓'"
    )


class RhetoricInstruction(BaseModel):
    """
    修辞手法指导模型
    提供具体的修辞使用指导
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 修辞类型
    rhetoric_type: str = Field(description="修辞类型，如：比喻、拟人、排比")
    
    # 使用频率建议
    frequency: str = Field(
        default="适度",
        description="使用频率：'高频'/'适度'/'偶尔'"
    )
    
    # 适用场景
    best_for: List[str] = Field(
        default_factory=list,
        description="最适合的场景"
    )
    
    # 使用示例
    example: str = Field(default="", description="使用示例")
    
    # 禁忌场景
    avoid_in: List[str] = Field(
        default_factory=list,
        description="应避免使用的场景"
    )


class PerspectiveControl(BaseModel):
    """
    视角控制模型
    管理叙事视角
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 主要视角
    primary_perspective: PerspectiveType = Field(
        default=PerspectiveType.THIRD_LIMITED,
        description="主要叙事视角"
    )
    
    # 视角人物（第三人称限制视角时）
    pov_character: Optional[str] = Field(
        None,
        description="视角人物名称"
    )
    
    # 是否允许视角切换
    allow_pov_switch: bool = Field(
        default=False,
        description="是否允许章节内视角切换"
    )
    
    # 视角切换规则
    switch_rules: List[str] = Field(
        default_factory=lambda: ["章节分隔线后切换", "不在紧张场景中切换"],
        description="视角切换规则"
    )
    
    # 视角限制
    perspective_constraints: List[str] = Field(
        default_factory=list,
        description="视角限制，如：'不能看到视角人物背后的事物'"
    )


class StyleFeatures(BaseModel):
    """
    文风特征模型（增强版）
    提供完整的文笔控制能力
    """
    model_config = ConfigDict(from_attributes=True)
    
    # ========== 原有字段 ==========
    sentence_length_distribution: Dict[str, float] = Field(
        default_factory=lambda: {"short": 0.3, "medium": 0.5, "long": 0.2},
        description="句式长度分布情况"
    )
    
    common_rhetoric: List[str] = Field(
        default_factory=list,
        description="经常使用的修辞手法"
    )
    
    dialogue_narration_ratio: str = Field(
        default="3:7",
        description="对话与旁白的比例描述"
    )
    
    emotional_tone: str = Field(
        default="中性",
        description="整体的情绪色调"
    )
    
    vocabulary_preference: List[str] = Field(
        default_factory=list,
        description="偏好使用的词汇类型或特定词汇"
    )
    
    rhythm_description: str = Field(
        default="",
        description="文字节奏的描述"
    )
    
    example_sentences: List[str] = Field(
        default_factory=list,
        description="风格示例句子"
    )
    
    # ========== 新增字段 ==========
    
    # 视角控制
    perspective_control: PerspectiveControl = Field(
        default_factory=PerspectiveControl,
        description="叙事视角控制"
    )
    
    # 描写平衡
    description_balance: DescriptionBalance = Field(
        default_factory=DescriptionBalance,
        description="各类描写的比例建议"
    )
    
    # 氛围控制
    atmosphere_control: Optional[AtmosphereControl] = Field(
        None,
        description="氛围渲染控制"
    )
    
    # 修辞指导列表
    rhetoric_instructions: List[RhetoricInstruction] = Field(
        default_factory=list,
        description="修辞手法的具体使用指导"
    )
    
    # 推荐写作技法
    recommended_techniques: List[WritingTechnique] = Field(
        default_factory=list,
        description="推荐使用的写作技法"
    )
    
    # 禁忌表达
    forbidden_expressions: List[str] = Field(
        default_factory=list,
        description="应避免的表达方式"
    )
    
    # 标点风格
    punctuation_style: Dict[str, Any] = Field(
        default_factory=lambda: {
            "prefer_short_sentences": False,
            "allow_sentence_fragments": True,
            "ellipsis_usage": "适度",
        },
        description="标点使用风格"
    )
    
    def to_writer_prompt(self, scene_type: str = "Normal") -> str:
        """
        将文风特征转换为写作提示词
        
        Args:
            scene_type: 场景类型
            
        Returns:
            格式化的写作提示词
        """
        parts = ["【文风规范】"]
        
        # 基础风格
        parts.append(f"情绪基调：{self.emotional_tone}")
        parts.append(f"节奏：{self.rhythm_description}")
        parts.append(f"对话/旁白比例：{self.dialogue_narration_ratio}")
        
        # 视角控制
        pov = self.perspective_control
        pov_map = {
            PerspectiveType.FIRST_PERSON: "第一人称",
            PerspectiveType.THIRD_LIMITED: "第三人称限制视角",
            PerspectiveType.THIRD_OMNISCIENT: "第三人称全知视角",
            PerspectiveType.MULTIPLE_POV: "多视角",
        }
        parts.append(f"叙事视角：{pov_map.get(pov.primary_perspective, '第三人称')}")
        if pov.pov_character:
            parts.append(f"视角人物：{pov.pov_character}")
        
        # 描写平衡
        balance = self.description_balance.get_adjusted_balance(scene_type)
        balance_str = "、".join([
            f"{k}({v:.0%})" for k, v in balance.items()
        ])
        parts.append(f"描写比例：{balance_str}")
        
        # 修辞手法
        if self.common_rhetoric:
            parts.append(f"推荐修辞：{', '.join(self.common_rhetoric)}")
        
        # 氛围关键词
        if self.atmosphere_control:
            atm = self.atmosphere_control
            if atm.atmosphere_keywords:
                parts.append(f"氛围关键词：{', '.join(atm.atmosphere_keywords)}")
            if atm.forbidden_words:
                parts.append(f"氛围禁忌词：{', '.join(atm.forbidden_words)}")
        
        # 禁忌表达
        if self.forbidden_expressions:
            parts.append(f"禁忌表达：{', '.join(self.forbidden_expressions)}")
        
        return "\n".join(parts)


# ============ 场景写作模板 ============

class SceneWritingTemplate(BaseModel):
    """
    场景写作模板
    针对不同场景类型的专业写作指导
    """
    model_config = ConfigDict(from_attributes=True)
    
    scene_type: str = Field(description="场景类型")
    
    # 句式要求
    sentence_requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="句式要求"
    )
    
    # 词汇偏好
    vocabulary_focus: List[str] = Field(
        default_factory=list,
        description="词汇重点"
    )
    
    # 节奏指导
    rhythm_guidance: str = Field(default="", description="节奏指导")
    
    # 描写重点
    description_focus: List[DescriptionType] = Field(
        default_factory=list,
        description="描写重点"
    )
    
    # 技法推荐
    technique_recommendations: List[str] = Field(
        default_factory=list,
        description="推荐技法"
    )
    
    # 禁忌
    taboos: List[str] = Field(
        default_factory=list,
        description="禁忌"
    )
    
    # 示例片段
    example_snippet: str = Field(default="", description="示例片段")


# 预定义的场景模板
SCENE_TEMPLATES: Dict[str, SceneWritingTemplate] = {
    "Action": SceneWritingTemplate(
        scene_type="Action",
        sentence_requirements={
            "max_length": 20,
            "prefer_short": True,
            "allow_fragments": True,
        },
        vocabulary_focus=["动词密集", "力量词汇", "速度词汇"],
        rhythm_guidance="短促有力，句式紧凑，如同心跳加速",
        description_focus=[DescriptionType.ACTION, DescriptionType.SENSORY],
        technique_recommendations=["白描", "蒙太奇", "特写镜头"],
        taboos=["冗长的心理描写", "大段环境描写", "学术化用语"],
        example_snippet="剑光闪过。血溅三尺。他踉跄后退，扶住断壁。"
    ),
    "Emotional": SceneWritingTemplate(
        scene_type="Emotional",
        sentence_requirements={
            "allow_long": True,
            "rhythm_variation": True,
        },
        vocabulary_focus=["情感词汇", "意象化表达", "通感"],
        rhythm_guidance="舒缓悠长，情绪层层递进，如潮水涌动",
        description_focus=[DescriptionType.PSYCHOLOGY, DescriptionType.SENSORY],
        technique_recommendations=["意识流", "内心独白", "象征", "留白"],
        taboos=["过度直白", "情绪标签化", "说教"],
        example_snippet="那一刻，时间仿佛凝固了。她听见自己的心跳声，如鼓槌敲击空洞的胸腔。"
    ),
    "Dialogue": SceneWritingTemplate(
        scene_type="Dialogue",
        sentence_requirements={
            "natural_flow": True,
            "allow_interruption": True,
        },
        vocabulary_focus=["口语化", "人物特色词汇", "潜台词"],
        rhythm_guidance="节奏明快，对话往来，如乒乓球赛",
        description_focus=[DescriptionType.DIALOGUE, DescriptionType.ACTION],
        technique_recommendations=["潜台词", "动作描写穿插", "非语言交流"],
        taboos=["对话过长", "书面语", "角色台词同质化"],
        example_snippet='"你……"他欲言又止，拳头攥紧。"别说了。"她转身，背影僵硬。'
    ),
    "Description": SceneWritingTemplate(
        scene_type="Description",
        sentence_requirements={
            "layer_structure": True,
            "rhythm_variation": True,
        },
        vocabulary_focus=["五感词汇", "空间词汇", "色彩词汇"],
        rhythm_guidance="从远及近，由整体到细节，如镜头推进",
        description_focus=[DescriptionType.ENVIRONMENT, DescriptionType.SENSORY],
        technique_recommendations=["五感描写", "空间层次", "时间流动", "动静结合"],
        taboos=["堆砌辞藻", "静态罗列", "缺乏焦点"],
        example_snippet="暮色四合，远山如黛。晚风携来稻香，掠过青石小巷。老槐树下，一盏昏黄的灯火摇曳。"
    ),
}
