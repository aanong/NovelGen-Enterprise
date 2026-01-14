from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, Float, Boolean, Index, ARRAY
from sqlalchemy.orm import relationship
# from pgvector.sqlalchemy import Vector
from .base import Base
import datetime

class Novel(Base):
    """小说元数据管理"""
    __tablename__ = "novels"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    author = Column(String(100))
    status = Column(String(50), default="ongoing") # ongoing, completed, hiatus
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 关系
    chapters = relationship("Chapter", back_populates="novel", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="novel", cascade="all, delete-orphan")
    outlines = relationship("PlotOutline", back_populates="novel", cascade="all, delete-orphan")
    bible_entries = relationship("NovelBible", back_populates="novel", cascade="all, delete-orphan")
    world_items = relationship("WorldItem", back_populates="novel", cascade="all, delete-orphan")
    reference_materials = relationship("ReferenceMaterial", foreign_keys="ReferenceMaterial.novel_id", cascade="all, delete-orphan")
    plot_branches = relationship("PlotBranch", back_populates="novel", cascade="all, delete-orphan")

class StyleRef(Base):
    __tablename__ = "style_ref"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float)) # Fallback to ARRAY(Float) if pgvector is not available
    source_author = Column(String(255))
    style_metadata = Column(JSON) # 存储句式统计、修辞分布等特征
    
    # 可选：关联特定小说，为空则为全局通用
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=True, index=True)

class ReferenceMaterial(Base):
    """通用资料库/经典文献 (用于初始化设定参考)"""
    __tablename__ = "reference_materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True) # 标题/书名/条目名
    content = Column(Text, nullable=False)  # 内容片段
    embedding = Column(ARRAY(Float))         # 向量
    source = Column(String(255))            # 来源（作者/书名）
    category = Column(String(100), index=True) # 分类：world_setting(世界观), plot_trope(剧情), character_archetype(人物原型), style(文风)
    tags = Column(JSON)                     # 标签列表
    
    # 可选：关联特定小说，为空则为全局通用资料库
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        Index('idx_novel_category', 'novel_id', 'category'),  # 优化按小说和分类查询
    )

class NovelBible(Base):
    """世界观/设定集 (Novel Bible)"""
    __tablename__ = "novel_bible"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), index=True) 
    key = Column(String(255), index=True) # 去掉 unique=True，因为不同小说可能有相同的 key
    content = Column(Text, nullable=False)
    embedding = Column(ARRAY(Float)) # Fallback to ARRAY(Float)
    importance = Column(Integer, default=5)
    tags = Column(JSON)
    
    novel = relationship("Novel", back_populates="bible_entries")

    # 添加复合索引以优化按 category + importance 查询
    __table_args__ = (
        Index('idx_novel_category_importance', 'novel_id', 'category', 'importance'),
        Index('idx_novel_key', 'novel_id', 'key', unique=True), # 在同一本小说内 key 必须唯一
    )

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), index=True, nullable=False) # 去掉全局 unique
    role = Column(String(100)) # 主角/配角/反派
    personality_traits = Column(JSON) # MBTI, BigFive, 核心动机, 缺陷
    skills = Column(JSON)             # 功法、神技、被动技能
    assets = Column(JSON)             # 灵石、地盘、声望等非实物资产
    evolution_log = Column(JSON)      # 章节成长记录
    current_mood = Column(String(100))
    status = Column(JSON)             # 当前生理/心理状态（受伤、狂喜等）
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 新增：能力等级系统
    # 格式：{"技能名": {"level": 1-10, "proficiency": 0.0-1.0, "description": "..."}, ...}
    ability_levels = Column(JSON, default=dict)
    
    # 新增：价值观/信念系统
    # 格式：{"核心信念": 0.0-1.0, ...} 如 {"正义": 0.8, "复仇": 0.3, "家族": 0.9}
    core_values = Column(JSON, default=dict)
    
    # 新增：性格动态维度（可演化的性格特质）
    # 格式：{"勇气": 0.0-1.0, "理性": 0.0-1.0, "同理心": 0.0-1.0, ...}
    personality_dynamics = Column(JSON, default=dict)
    
    # 新增：人物内在需求与缺陷（用于弧光推进）
    core_need = Column(String(255))    # 核心需求，如"被认可"、"自我救赎"
    core_flaw = Column(String(255))    # 核心缺陷，如"傲慢"、"恐惧亲密"
    
    # ========== 人物语言风格系统 ==========
    # 说话风格（如：文雅、粗犷、阴阳怪气、冷淡、热情、学究气）
    speech_pattern = Column(String(255))
    
    # 口头禅/语言习惯（JSON 数组）
    # 格式：["有趣", "哼，愚蠢", "你觉得呢？"]
    verbal_tics = Column(JSON, default=list)
    
    # 语气修饰词偏好（JSON 对象）
    # 格式：{"常用语气词": ["嘛", "呢", "啊"], "句式特点": "喜欢用反问句", "称呼习惯": "称他人为'小友'"}
    tone_modifiers = Column(JSON, default=dict)
    
    # 对话风格详细描述（供 LLM 参考）
    dialogue_style_description = Column(Text)

    novel = relationship("Novel", back_populates="characters")

    # 添加关系
    inventory = relationship("WorldItem", back_populates="owner")
    relationships_as_a = relationship("CharacterRelationship", foreign_keys="CharacterRelationship.char_a_id", back_populates="character_a", cascade="all, delete-orphan")
    relationships_as_b = relationship("CharacterRelationship", foreign_keys="CharacterRelationship.char_b_id", back_populates="character_b", cascade="all, delete-orphan")
    branch_statuses = relationship("CharacterBranchStatus", back_populates="character", cascade="all, delete-orphan")
    character_arc = relationship("CharacterArc", back_populates="character", uselist=False, cascade="all, delete-orphan")
    key_events = relationship("CharacterKeyEvent", back_populates="character", cascade="all, delete-orphan")
    
    # 支线关联
    branch_associations = relationship("PlotBranchCharacter", back_populates="character", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_novel_char_name', 'novel_id', 'name', unique=True), # 同一本小说内名字唯一
    )

class CharacterBranchStatus(Base):
    """人物在特定分支、特定章节的状态快照"""
    __tablename__ = "character_branch_statuses"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(100), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False, index=True)
    
    # 状态快照
    current_mood = Column(String(100))
    status = Column(JSON) # 生理/心理状态
    skills = Column(JSON) # 当时的技能列表
    assets = Column(JSON) # 当时的资产
    is_active = Column(Boolean, default=True) # 是否存活/活跃
    
    # 新增：性格和价值观快照
    personality_snapshot = Column(JSON)  # 性格特质快照（含演化后的数值）
    values_snapshot = Column(JSON)       # 价值观快照
    ability_levels_snapshot = Column(JSON)  # 能力等级快照
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    character = relationship("Character", back_populates="branch_statuses")

    __table_args__ = (
        Index('idx_char_branch_chapter', 'character_id', 'branch_id', 'chapter_number', unique=True),
    )


class CharacterArc(Base):
    """
    人物弧光（Character Arc）定义
    预设角色的成长轨迹，系统按规划推进
    """
    __tablename__ = "character_arcs"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 弧光类型：positive(正向成长), negative(堕落), flat(扁平/坚守), transformation(转变)
    arc_type = Column(String(50), nullable=False, default="positive")
    
    # 起点状态描述
    starting_state = Column(JSON, nullable=False)  # {"personality": {...}, "values": {...}, "core_flaw": "...", "core_need": "..."}
    
    # 终点状态描述（目标）
    target_state = Column(JSON, nullable=False)    # {"personality": {...}, "values": {...}, "resolved_flaw": "...", "fulfilled_need": "..."}
    
    # 关键里程碑（按章节规划）
    milestones = Column(JSON)  # [{"chapter_range": [1, 10], "description": "...", "trigger_event": "...", "expected_change": {...}}]
    
    # 当前进度（0.0 - 1.0）
    progress = Column(Float, default=0.0)
    
    # 当前阶段索引
    current_milestone_index = Column(Integer, default=0)
    
    # 弧光状态：active, completed, abandoned
    status = Column(String(50), default="active")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    character = relationship("Character", back_populates="character_arc")

    __table_args__ = (
        Index('idx_char_arc_status', 'character_id', 'status'),
    )


class CharacterKeyEvent(Base):
    """
    人物关键事件记录
    记录创伤、顿悟、重大决定等影响人物性格/价值观的事件
    """
    __tablename__ = "character_key_events"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number = Column(Integer, nullable=False, index=True)
    branch_id = Column(String(100), default="main", index=True)
    
    # 事件类型：trauma(创伤), epiphany(顿悟), decision(重大决定), loss(失去), gain(获得), betrayal(背叛), sacrifice(牺牲)
    event_type = Column(String(50), nullable=False)
    
    # 事件描述
    description = Column(Text, nullable=False)
    
    # 事件影响
    impact = Column(JSON)  # {"personality_changes": {...}, "value_changes": {...}, "ability_changes": {...}, "relationship_changes": {...}}
    
    # 影响强度（0.0 - 1.0）
    intensity = Column(Float, default=0.5)
    
    # 是否已处理/应用
    is_processed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    character = relationship("Character", back_populates="key_events")

    __table_args__ = (
        Index('idx_key_event_chapter', 'character_id', 'branch_id', 'chapter_number'),
    )

class CharacterRelationship(Base):
    """人物关系矩阵"""
    __tablename__ = "character_relationships"

    id = Column(Integer, primary_key=True, index=True)
    char_a_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"))
    char_b_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"))
    relation_type = Column(String(100)) # 敌对, 盟友, 暧昧, 师徒等
    intimacy = Column(Float, default=0.0) # 亲密度等级 -1.0 到 1.0
    history = Column(JSON) # 记录影响关系的重大事件
    
    # 添加关系
    character_a = relationship("Character", foreign_keys=[char_a_id], back_populates="relationships_as_a")
    character_b = relationship("Character", foreign_keys=[char_b_id], back_populates="relationships_as_b")
    
    # 添加复合索引和唯一约束
    __table_args__ = (
        Index('idx_char_pair', 'char_a_id', 'char_b_id'),
    )

class PlotOutline(Base):
    """细化剧情大纲"""
    __tablename__ = "plot_outlines"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(100), default="main", index=True) # 分支 ID
    chapter_number = Column(Integer, index=True)
    title = Column(String(255))      # 章节标题
    scene_description = Column(Text) # 核心场面描写
    key_conflict = Column(Text)      # 核心冲突点
    foreshadowing = Column(JSON)      # 本章埋下的伏笔
    recalls = Column(JSON)           # 需要回收的伏笔
    status = Column(String(50), default="pending") # pending, completed, skipped
    
    novel = relationship("Novel", back_populates="outlines")

    # 修改复合唯一索引，包含 branch_id
    __table_args__ = (
        Index('idx_novel_branch_chapter', 'novel_id', 'branch_id', 'chapter_number', unique=True),
    )

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(100), default="main", index=True) # 分支 ID
    chapter_number = Column(Integer, nullable=False, index=True)
    previous_chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True) # 链表结构
    title = Column(String(512))
    content = Column(Text)
    scene_tags = Column(JSON)        # 场景标签：战斗/对话/环境描写
    summary = Column(Text)           # 章节摘要
    logic_checked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    novel = relationship("Novel", back_populates="chapters")

    # 添加关系
    audits = relationship("LogicAudit", back_populates="chapter", cascade="all, delete-orphan")
    # 自引用关系，用于章节链表
    parent = relationship("Chapter", remote_side=[id], backref="children")
    
    # 修改复合唯一索引，包含 branch_id
    __table_args__ = (
        Index('idx_novel_branch_chapter_num', 'novel_id', 'branch_id', 'chapter_number', unique=True),
    )

class LogicAudit(Base):
    """剧情逻辑审核记录"""
    __tablename__ = "logic_audits"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    reviewer_role = Column(String(100)) # Deepseek-Critic, Editor等
    is_passed = Column(Boolean)
    feedback = Column(Text) # 具体的逻辑漏洞或改进建议
    logic_score = Column(Float) # 0.0 - 1.0
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 添加关系
    chapter = relationship("Chapter", back_populates="audits")

class WorldItem(Base):
    """关键物品/法宝管理"""
    __tablename__ = "world_items"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), index=True, nullable=False) # 去掉全局 unique
    description = Column(Text)
    rarity = Column(String(100)) # 凡、灵、宝、仙、神
    powers = Column(JSON)       # 物品的具体数值或特殊词条
    owner_id = Column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)
    location = Column(String(255)) # 如果不在人身上，所在位置
    is_unique = Column(Boolean, default=True)

    novel = relationship("Novel", back_populates="world_items")
    owner = relationship("Character", back_populates="inventory")
    
    # 支线关联
    branch_associations = relationship("PlotBranchItem", back_populates="item", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_novel_item_name', 'novel_id', 'name', unique=True), # 同一本小说内物品名唯一
    )


# ============ 剧情支线管理系统 ============

class PlotBranch(Base):
    """
    剧情支线定义
    支持为小说创建多条剧情支线，每条支线可关联专属人物和道具
    """
    __tablename__ = "plot_branches"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 支线基本信息
    branch_key = Column(String(100), nullable=False, index=True)  # 支线唯一标识，如 "side_quest_1"
    name = Column(String(255), nullable=False)                     # 支线名称，如 "复仇者的道路"
    description = Column(Text)                                     # 支线描述
    
    # 支线类型：main(主线), side(支线), hidden(隐藏线), parallel(平行线)
    branch_type = Column(String(50), default="side")
    
    # 引入时机
    introduce_at_chapter = Column(Integer, nullable=True)          # 在第几章引入（null表示从头开始）
    introduce_condition = Column(Text)                             # 引入条件描述（如"当主角到达某地时"）
    
    # 支线状态：planned(已规划), active(进行中), completed(已完成), abandoned(已放弃)
    status = Column(String(50), default="planned")
    
    # 支线优先级（影响生成时的考虑权重）
    priority = Column(Integer, default=5)  # 1-10，10最高
    
    # 支线目标和结局
    objectives = Column(JSON)              # 支线目标列表
    possible_endings = Column(JSON)        # 可能的结局列表
    current_ending = Column(String(100))   # 当前走向的结局
    
    # 进度追踪
    progress = Column(Float, default=0.0)  # 0.0-1.0
    current_stage = Column(Integer, default=0)  # 当前阶段索引
    stages = Column(JSON)                  # 支线阶段定义 [{"name": "", "description": "", "chapter_range": []}]
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    activated_at = Column(DateTime, nullable=True)  # 实际激活时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间

    # 关系
    novel = relationship("Novel", back_populates="plot_branches")
    character_associations = relationship("PlotBranchCharacter", back_populates="branch", cascade="all, delete-orphan")
    item_associations = relationship("PlotBranchItem", back_populates="branch", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_novel_branch_key', 'novel_id', 'branch_key', unique=True),
        Index('idx_novel_branch_status', 'novel_id', 'status'),
        Index('idx_novel_introduce_chapter', 'novel_id', 'introduce_at_chapter'),
    )


class PlotBranchCharacter(Base):
    """
    剧情支线与人物的关联表（多对多）
    记录哪些人物参与了哪条支线，以及他们在支线中的角色
    """
    __tablename__ = "plot_branch_characters"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("plot_branches.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = Column(Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 角色在支线中的定位
    role_in_branch = Column(String(100))  # 如 "主导者", "对手", "协助者", "受益者", "牺牲者"
    
    # 参与程度：core(核心), major(主要), minor(次要), cameo(客串)
    involvement_level = Column(String(50), default="major")
    
    # 加入支线的章节
    join_at_chapter = Column(Integer, nullable=True)
    
    # 离开支线的章节（如果已离开）
    leave_at_chapter = Column(Integer, nullable=True)
    
    # 该人物在此支线的特殊设定（覆盖或补充主设定）
    branch_specific_traits = Column(JSON)  # 如 {"hidden_motivation": "...", "secret": "..."}
    
    # 该人物在此支线的弧光变化预期
    expected_arc_changes = Column(JSON)  # 如 {"personality": {...}, "values": {...}}
    
    # 备注
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 关系
    branch = relationship("PlotBranch", back_populates="character_associations")
    character = relationship("Character", back_populates="branch_associations")

    __table_args__ = (
        Index('idx_branch_character', 'branch_id', 'character_id', unique=True),
    )


class PlotBranchItem(Base):
    """
    剧情支线与道具的关联表（多对多）
    记录哪些道具与哪条支线相关
    """
    __tablename__ = "plot_branch_items"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("plot_branches.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("world_items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 道具在支线中的角色
    role_in_branch = Column(String(100))  # 如 "麦高芬", "关键钥匙", "奖励", "诅咒之物"
    
    # 重要程度：critical(关键), important(重要), optional(可选)
    importance = Column(String(50), default="important")
    
    # 出现章节
    appear_at_chapter = Column(Integer, nullable=True)
    
    # 道具在此支线中的特殊设定
    branch_specific_powers = Column(JSON)  # 支线专属能力或属性
    
    # 获取条件
    acquisition_condition = Column(Text)  # 如何获得此道具
    
    # 备注
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 关系
    branch = relationship("PlotBranch", back_populates="item_associations")
    item = relationship("WorldItem", back_populates="branch_associations")

    __table_args__ = (
        Index('idx_branch_item', 'branch_id', 'item_id', unique=True),
    )


# ============ 伏笔生命周期管理系统 ============

class Foreshadowing(Base):
    """
    伏笔生命周期管理表
    替代简单的字符串列表，提供完整的伏笔元数据管理
    """
    __tablename__ = "foreshadowings"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id = Column(String(100), default="main", index=True)  # 所属分支
    
    # 伏笔内容
    content = Column(Text, nullable=False)  # 伏笔描述
    hint_text = Column(Text)  # 埋设时的暗示文本（用于回收时呼应）
    
    # 时间线管理
    created_at_chapter = Column(Integer, nullable=False)  # 埋下章节
    expected_resolve_chapter = Column(Integer)  # 预期回收章节
    actual_resolve_chapter = Column(Integer)  # 实际回收章节
    
    # 状态管理：planted(已埋设), advanced(已推进), resolved(已回收), abandoned(已放弃)
    status = Column(String(50), default="planted", index=True)
    
    # 重要性等级 1-10（影响回收优先级）
    importance = Column(Integer, default=5)
    
    # 关联数据（JSON 格式）
    related_characters = Column(JSON)  # 相关角色 ID 或名称列表
    related_items = Column(JSON)  # 相关道具 ID 或名称列表
    related_plot_points = Column(JSON)  # 相关剧情点
    
    # 回收条件与策略
    resolve_condition = Column(Text)  # 回收条件描述
    resolve_strategy = Column(Text)  # 回收策略建议（如：反转、呼应、升华）
    
    # 伏笔类型：character(人物), plot(剧情), item(道具), mystery(谜团), prophecy(预言)
    foreshadowing_type = Column(String(50), default="plot")
    
    # 推进记录（JSON 数组）
    # 格式：[{"chapter": 5, "description": "暗示加强", "timestamp": "..."}]
    advancement_log = Column(JSON, default=list)
    
    # 回收质量评分（回收后由 Reviewer 评分，0.0-1.0）
    resolve_quality_score = Column(Float)
    resolve_feedback = Column(Text)  # 回收质量反馈
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    resolved_at = Column(DateTime)

    __table_args__ = (
        Index('idx_novel_foreshadowing_status', 'novel_id', 'branch_id', 'status'),
        Index('idx_novel_foreshadowing_chapter', 'novel_id', 'created_at_chapter'),
        Index('idx_novel_foreshadowing_expected', 'novel_id', 'expected_resolve_chapter'),
    )


class ForeshadowingLink(Base):
    """
    伏笔链条追踪表
    记录伏笔之间的关联关系（父子、依赖、互斥等）
    """
    __tablename__ = "foreshadowing_links"

    id = Column(Integer, primary_key=True, index=True)
    
    # 父伏笔（被依赖的）
    parent_id = Column(Integer, ForeignKey("foreshadowings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 子伏笔（依赖父伏笔的）
    child_id = Column(Integer, ForeignKey("foreshadowings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 关联类型
    # derives_from: 子伏笔由父伏笔衍生
    # requires: 回收子伏笔需要先回收父伏笔
    # blocks: 回收父伏笔会阻止子伏笔
    # parallel: 平行伏笔，需同时推进
    # contradicts: 矛盾伏笔，只能回收其一
    link_type = Column(String(50), nullable=False)
    
    # 备注
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index('idx_foreshadowing_link', 'parent_id', 'child_id', unique=True),
    )


# ============ 主支线交织管理系统 ============

class PlotInterweaving(Base):
    """
    主线与支线的交织点管理表
    记录主线和支线在何处如何交织
    """
    __tablename__ = "plot_interweavings"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, ForeignKey("novels.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 交织的主线剧情点（对应 PlotOutline 的章节）
    main_plot_chapter = Column(Integer, nullable=False)
    main_plot_description = Column(Text)  # 主线剧情点描述
    
    # 交织的支线
    branch_id = Column(Integer, ForeignKey("plot_branches.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 交织类型
    # converge: 汇合（支线合入主线）
    # diverge: 分离（从主线分出支线）
    # parallel: 平行（同时推进但相互影响）
    # cross: 交叉（短暂交集后分开）
    # merge: 融合（支线彻底融入主线）
    interweave_type = Column(String(50), nullable=False)
    
    # 交织发生的章节
    chapter_number = Column(Integer, nullable=False, index=True)
    
    # 交织影响描述
    impact_description = Column(Text)
    
    # 对主线的影响程度（0.0-1.0）
    main_plot_impact = Column(Float, default=0.5)
    
    # 对支线的影响程度（0.0-1.0）
    branch_impact = Column(Float, default=0.5)
    
    # 涉及的角色变化
    character_changes = Column(JSON)  # {"角色名": "变化描述"}
    
    # 交织状态：planned(已规划), active(进行中), completed(已完成)
    status = Column(String(50), default="planned")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # 关系
    branch = relationship("PlotBranch")

    __table_args__ = (
        Index('idx_novel_interweave_chapter', 'novel_id', 'chapter_number'),
        Index('idx_novel_interweave_branch', 'novel_id', 'branch_id'),
    )
