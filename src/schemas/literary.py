"""
文学元素模型
提供典故、诗词、成语、叙事母题等文学元素的数据模型
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Literal
from enum import Enum


class LiteraryElementType(str, Enum):
    """文学元素类型枚举"""
    ALLUSION = "allusion"           # 典故
    POETRY = "poetry"               # 诗词名句
    IDIOM = "idiom"                 # 成语俗语
    MOTIF = "motif"                 # 叙事母题
    ARCHETYPE = "archetype"         # 人物原型
    TROPE = "trope"                 # 叙事套路


class EmotionalCategory(str, Enum):
    """情感分类"""
    PARTING = "parting"             # 离别
    LONGING = "longing"             # 相思
    AMBITION = "ambition"           # 壮志
    SORROW = "sorrow"               # 悲凉
    NOSTALGIA = "nostalgia"         # 怀旧
    JOY = "joy"                     # 喜悦
    ANGER = "anger"                 # 愤怒
    FEAR = "fear"                   # 恐惧
    REDEMPTION = "redemption"       # 救赎
    REVENGE = "revenge"             # 复仇
    SACRIFICE = "sacrifice"         # 牺牲
    HOPE = "hope"                   # 希望
    DESPAIR = "despair"             # 绝望


class CulturalContext(str, Enum):
    """文化背景"""
    CHINESE_CLASSICAL = "chinese_classical"     # 中国古典
    CHINESE_MODERN = "chinese_modern"           # 中国现代
    WESTERN_CLASSICAL = "western_classical"     # 西方古典
    WESTERN_MODERN = "western_modern"           # 西方现代
    MYTHOLOGY_CHINESE = "mythology_chinese"     # 中国神话
    MYTHOLOGY_GREEK = "mythology_greek"         # 希腊神话
    MYTHOLOGY_NORSE = "mythology_norse"         # 北欧神话
    BUDDHIST = "buddhist"                       # 佛教
    TAOIST = "taoist"                           # 道教
    UNIVERSAL = "universal"                     # 通用


class LiteraryElement(BaseModel):
    """
    文学元素模型
    用于存储和检索各类文学元素
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 基本信息
    element_type: LiteraryElementType = Field(description="元素类型")
    title: str = Field(description="标题/名称")
    content: str = Field(description="具体内容")
    source: str = Field(description="来源（书名/作者）")
    
    # 分类信息
    applicable_emotions: List[EmotionalCategory] = Field(
        default_factory=list,
        description="适用的情感场景"
    )
    applicable_themes: List[str] = Field(
        default_factory=list,
        description="适用的主题，如：'成长'、'复仇'、'爱情'"
    )
    
    # 文化背景
    cultural_context: CulturalContext = Field(
        default=CulturalContext.UNIVERSAL,
        description="文化背景"
    )
    
    # 使用难度（1-5，1最简单）
    difficulty_level: int = Field(
        default=3, ge=1, le=5,
        description="使用难度"
    )
    
    # 使用建议
    usage_tips: List[str] = Field(
        default_factory=list,
        description="使用建议"
    )
    
    # 相关元素
    related_elements: List[str] = Field(
        default_factory=list,
        description="相关元素的标题"
    )
    
    # 禁忌场景
    avoid_in: List[str] = Field(
        default_factory=list,
        description="应避免使用的场景"
    )
    
    # 示例应用
    example_usage: str = Field(
        default="",
        description="应用示例"
    )


class AllusionDetail(BaseModel):
    """
    典故详细模型
    扩展 LiteraryElement，提供更详细的典故信息
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 继承基本信息
    title: str = Field(description="典故名称")
    origin: str = Field(description="典故出处")
    original_story: str = Field(description="原始故事")
    
    # 核心含义
    core_meaning: str = Field(description="核心寓意")
    
    # 人物（如有）
    main_characters: List[str] = Field(
        default_factory=list,
        description="涉及的主要人物"
    )
    
    # 使用方式示例
    usage_examples: Dict[str, str] = Field(
        default_factory=lambda: {
            "direct": "",       # 直接引用
            "adapted": "",      # 改编
            "inverted": "",     # 反用
            "implicit": "",     # 暗用
            "transformed": "",  # 化用
        },
        description="不同使用方式的示例"
    )
    
    # 常见误用
    common_misuses: List[str] = Field(
        default_factory=list,
        description="常见误用"
    )
    
    # 适用情感
    emotions: List[EmotionalCategory] = Field(
        default_factory=list,
        description="适用情感"
    )
    
    # 文化背景
    cultural_context: CulturalContext = Field(
        default=CulturalContext.CHINESE_CLASSICAL
    )


class PoetryQuote(BaseModel):
    """
    诗词名句模型
    """
    model_config = ConfigDict(from_attributes=True)
    
    quote: str = Field(description="诗句/词句")
    full_poem: Optional[str] = Field(None, description="完整诗词")
    author: str = Field(description="作者")
    dynasty: str = Field(default="", description="朝代")
    
    # 意境分类
    mood: EmotionalCategory = Field(description="意境情感")
    
    # 意象
    imagery: List[str] = Field(
        default_factory=list,
        description="包含的意象，如：'月'、'酒'、'柳'"
    )
    
    # 季节（如适用）
    season: Optional[str] = Field(None, description="季节")
    
    # 使用场景
    best_for: List[str] = Field(
        default_factory=list,
        description="最佳使用场景"
    )
    
    # 化用示例
    adaptation_example: str = Field(
        default="",
        description="化用示例"
    )


class NarrativeMotif(BaseModel):
    """
    叙事母题模型
    用于识别和应用经典叙事模式
    """
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(description="母题名称")
    description: str = Field(description="母题描述")
    
    # 典型阶段
    stages: List[str] = Field(
        default_factory=list,
        description="典型阶段，如英雄之旅的各个阶段"
    )
    
    # 核心冲突
    core_conflict: str = Field(
        default="",
        description="核心冲突类型"
    )
    
    # 典型角色
    typical_roles: List[str] = Field(
        default_factory=list,
        description="典型角色配置"
    )
    
    # 经典示例
    classic_examples: List[str] = Field(
        default_factory=list,
        description="经典作品示例"
    )
    
    # 变体
    variations: List[str] = Field(
        default_factory=list,
        description="常见变体"
    )
    
    # 适用题材
    suitable_genres: List[str] = Field(
        default_factory=list,
        description="适用的题材"
    )


class AllusionUsageValidation(BaseModel):
    """
    典故使用验证结果
    用于检验典故是否被正确使用
    """
    model_config = ConfigDict(from_attributes=True)
    
    # 典故标题
    allusion_title: str = Field(description="典故标题")
    
    # 是否正确使用
    is_correct: bool = Field(description="是否正确使用")
    
    # 使用方式
    detected_usage_type: str = Field(description="检测到的使用方式")
    
    # 自然度评分（0.0-1.0）
    naturalness_score: float = Field(
        ge=0.0, le=1.0,
        description="使用自然度评分"
    )
    
    # 契合度评分（0.0-1.0）
    fit_score: float = Field(
        ge=0.0, le=1.0,
        description="与场景契合度评分"
    )
    
    # 问题列表
    issues: List[str] = Field(
        default_factory=list,
        description="发现的问题"
    )
    
    # 改进建议
    suggestions: List[str] = Field(
        default_factory=list,
        description="改进建议"
    )


# ============ 预置文学元素库 ============

PRESET_ALLUSIONS: List[AllusionDetail] = [
    AllusionDetail(
        title="卧薪尝胆",
        origin="《史记·越王勾践世家》",
        original_story="越王勾践被吴王夫差打败后，卧薪尝胆，忍辱负重，最终复国灭吴。",
        core_meaning="忍辱负重，发愤图强，以图东山再起",
        main_characters=["勾践", "夫差", "范蠡", "文种"],
        usage_examples={
            "direct": "他立志效仿勾践卧薪尝胆，誓要一雪前耻。",
            "adapted": "这十年蛰伏，便是他的卧薪尝胆。",
            "inverted": "他不屑卧薪尝胆，选择直接决战。",
            "implicit": "每夜，他都会在那把旧剑前静坐片刻。",
            "transformed": "苦涩的药汁入喉，他将这滋味深深刻入骨髓。",
        },
        common_misuses=["用于形容短期忍耐", "忽视最终复仇成功的结局"],
        emotions=[EmotionalCategory.REVENGE, EmotionalCategory.AMBITION],
        cultural_context=CulturalContext.CHINESE_CLASSICAL
    ),
    AllusionDetail(
        title="塞翁失马",
        origin="《淮南子·人间训》",
        original_story="边塞老翁丢失马匹，后马带回胡马，儿子骑马摔断腿，却因此免于征战。",
        core_meaning="祸福相依，塞翁失马焉知非福",
        main_characters=["塞翁"],
        usage_examples={
            "direct": "正所谓塞翁失马，焉知非福。",
            "adapted": "这次失败，或许就是他的塞翁失马。",
            "inverted": "可惜世事并非都如塞翁失马，有些失去就是失去。",
            "implicit": "他望着手中的碎片，却意外地笑了。",
            "transformed": "旧门关上，新窗已然洞开。",
        },
        common_misuses=["用于安慰所有失败"],
        emotions=[EmotionalCategory.HOPE, EmotionalCategory.NOSTALGIA],
        cultural_context=CulturalContext.CHINESE_CLASSICAL
    ),
    AllusionDetail(
        title="精卫填海",
        origin="《山海经·北山经》",
        original_story="炎帝之女溺死东海，化为精卫鸟，衔石填海，誓要填平大海。",
        core_meaning="坚持不懈，意志坚定，即使面对不可能也绝不放弃",
        main_characters=["精卫", "女娃"],
        usage_examples={
            "direct": "她有精卫填海般的执着。",
            "adapted": "日复一日，他如精卫般往返于两地。",
            "inverted": "他不愿做那愚蠢的精卫，明知不可为而为之。",
            "implicit": "一块，又一块。她从未停止。",
            "transformed": "衔起命运的碎石，她要亲手铺平前路。",
        },
        common_misuses=["忽视其悲剧性和不可能性"],
        emotions=[EmotionalCategory.AMBITION, EmotionalCategory.SORROW],
        cultural_context=CulturalContext.MYTHOLOGY_CHINESE
    ),
]

PRESET_POETRY: List[PoetryQuote] = [
    PoetryQuote(
        quote="人生若只如初见，何事秋风悲画扇",
        author="纳兰性德",
        dynasty="清",
        mood=EmotionalCategory.NOSTALGIA,
        imagery=["秋风", "画扇"],
        best_for=["爱情变质", "物是人非", "往事追忆"],
        adaptation_example="若一切都能停在最初，该有多好。"
    ),
    PoetryQuote(
        quote="山重水复疑无路，柳暗花明又一村",
        author="陆游",
        dynasty="宋",
        mood=EmotionalCategory.HOPE,
        imagery=["山", "水", "柳", "花", "村"],
        best_for=["困境转机", "峰回路转", "绝处逢生"],
        adaptation_example="就在他以为走投无路时，前方竟豁然开朗。"
    ),
    PoetryQuote(
        quote="曾经沧海难为水，除却巫山不是云",
        author="元稹",
        dynasty="唐",
        mood=EmotionalCategory.LONGING,
        imagery=["沧海", "巫山", "云"],
        best_for=["深情表白", "至死不渝", "曾经拥有"],
        adaptation_example="见过她之后，世间的女子都黯然失色。"
    ),
    PoetryQuote(
        quote="大漠孤烟直，长河落日圆",
        author="王维",
        dynasty="唐",
        mood=EmotionalCategory.AMBITION,
        imagery=["大漠", "孤烟", "长河", "落日"],
        season="秋",
        best_for=["边塞场景", "壮阔景象", "孤独英雄"],
        adaptation_example="远方，一缕狼烟直冲云霄，染红了半边天际。"
    ),
]

PRESET_MOTIFS: List[NarrativeMotif] = [
    NarrativeMotif(
        name="英雄之旅",
        description="主角从平凡世界出发，经历考验，获得成长，最终归来并带来改变",
        stages=[
            "平凡世界", "冒险召唤", "拒绝召唤", "遇见导师",
            "跨越第一道门槛", "试炼、盟友、敌人", "接近深渊",
            "磨难", "报酬", "归途", "复活", "携万灵药归来"
        ],
        core_conflict="个人成长与外部挑战",
        typical_roles=["英雄", "导师", "守门人", "使者", "变形者", "阴影", "盟友"],
        classic_examples=["《西游记》", "《星球大战》", "《哈利波特》"],
        variations=["反英雄之旅", "悲剧英雄", "集体英雄"],
        suitable_genres=["玄幻", "仙侠", "科幻", "奇幻"]
    ),
    NarrativeMotif(
        name="复仇之路",
        description="主角因亲人或重要之人受害，踏上复仇之路",
        stages=[
            "平静生活", "灾难降临", "失去挚爱", "蛰伏成长",
            "追查真相", "直面仇人", "复仇抉择", "结局反思"
        ],
        core_conflict="复仇与放下、正义与私怨",
        typical_roles=["复仇者", "仇人", "导师", "同路人", "牺牲者"],
        classic_examples=["《基督山伯爵》", "《赵氏孤儿》"],
        variations=["放弃复仇", "复仇失败", "复仇后空虚"],
        suitable_genres=["武侠", "仙侠", "都市"]
    ),
    NarrativeMotif(
        name="救赎之旅",
        description="主角曾犯下过错，通过一系列经历寻求自我救赎",
        stages=[
            "罪与愧", "逃避", "契机", "面对过去",
            "赎罪行动", "危机考验", "救赎成功或失败"
        ],
        core_conflict="过去的罪与当下的善",
        typical_roles=["赎罪者", "受害者", "引导者", "见证者"],
        classic_examples=["《追风筝的人》", "《悲惨世界》"],
        variations=["无法救赎", "牺牲式救赎", "被原谅"],
        suitable_genres=["文艺", "武侠", "仙侠"]
    ),
]
