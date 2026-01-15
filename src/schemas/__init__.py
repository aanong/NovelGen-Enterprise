"""
Schemas 模块
提供小说生成系统的数据模型
"""

from .state import (
    # 核心状态
    NGEState,
    CharacterState,
    PlotPoint,
    MemoryContext,
    NovelBible,
    AntigravityContext,
    
    # 人物相关
    SpeechStyle,
    CharacterPsychology,
    CharacterArcSchema,
    AbilityLevel,
    
    # 价值观系统（新增）
    ValueBelief,
    ValueConflict,
    ValueSystem,
    
    # 成长系统（新增）
    GrowthCurveType,
    MasteryStage,
    MindsetDimension,
    GrowthMilestone,
    CharacterGrowthSystem,
    
    # 伏笔系统
    ForeshadowingSchema,
    
    # 关键事件
    KeyEventType,
    KeyEventSchema,
    
    # 弧光类型
    ArcType,
)

from .style import (
    # 文风特征
    StyleFeatures,
    WritingTechnique,
    DescriptionBalance,
    AtmosphereControl,
    PerspectiveControl,
    RhetoricInstruction,
    SceneWritingTemplate,
    
    # 枚举
    PerspectiveType,
    DescriptionType,
    AtmosphereType,
    
    # 预定义模板
    SCENE_TEMPLATES,
)

from .literary import (
    # 文学元素
    LiteraryElement,
    LiteraryElementType,
    AllusionDetail,
    PoetryQuote,
    NarrativeMotif,
    AllusionUsageValidation,
    
    # 分类枚举
    EmotionalCategory,
    CulturalContext,
    
    # 预置库
    PRESET_ALLUSIONS,
    PRESET_POETRY,
    PRESET_MOTIFS,
)

__all__ = [
    # 核心状态
    "NGEState",
    "CharacterState",
    "PlotPoint",
    "MemoryContext",
    "NovelBible",
    "AntigravityContext",
    
    # 人物模型
    "SpeechStyle",
    "CharacterPsychology",
    "CharacterArcSchema",
    "AbilityLevel",
    
    # 价值观系统
    "ValueBelief",
    "ValueConflict",
    "ValueSystem",
    
    # 成长系统
    "GrowthCurveType",
    "MasteryStage",
    "MindsetDimension",
    "GrowthMilestone",
    "CharacterGrowthSystem",
    
    # 伏笔与事件
    "ForeshadowingSchema",
    "KeyEventType",
    "KeyEventSchema",
    "ArcType",
    
    # 文风模型
    "StyleFeatures",
    "WritingTechnique",
    "DescriptionBalance",
    "AtmosphereControl",
    "PerspectiveControl",
    "RhetoricInstruction",
    "SceneWritingTemplate",
    "PerspectiveType",
    "DescriptionType",
    "AtmosphereType",
    "SCENE_TEMPLATES",
    
    # 文学元素
    "LiteraryElement",
    "LiteraryElementType",
    "AllusionDetail",
    "PoetryQuote",
    "NarrativeMotif",
    "AllusionUsageValidation",
    "EmotionalCategory",
    "CulturalContext",
    "PRESET_ALLUSIONS",
    "PRESET_POETRY",
    "PRESET_MOTIFS",
]
