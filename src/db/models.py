from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, Float, Boolean, Index
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import Base
import datetime

class StyleRef(Base):
    __tablename__ = "style_ref"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768)) # 使用 pgvector 存储 768 维向量
    source_author = Column(String(255))
    style_metadata = Column(JSON) # 存储句式统计、修辞分布等特征

class NovelBible(Base):
    """世界观/设定集 (Novel Bible)"""
    __tablename__ = "novel_bible"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), index=True) 
    key = Column(String(255), unique=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768)) # 使用 pgvector 存储 768 维向量
    importance = Column(Integer, default=5)
    tags = Column(JSON)
    
    # 添加复合索引以优化按 category + importance 查询
    __table_args__ = (
        Index('idx_category_importance', 'category', 'importance'),
    )

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(100)) # 主角/配角/反派
    personality_traits = Column(JSON) # MBTI, BigFive, 核心动机, 缺陷
    skills = Column(JSON)             # 功法、神技、被动技能
    assets = Column(JSON)             # 灵石、地盘、声望等非实物资产
    evolution_log = Column(JSON)      # 章节成长记录
    current_mood = Column(String(100))
    status = Column(JSON)             # 当前生理/心理状态（受伤、狂喜等）
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 添加关系
    inventory = relationship("WorldItem", back_populates="owner")
    relationships_as_a = relationship("CharacterRelationship", foreign_keys="CharacterRelationship.char_a_id", back_populates="character_a", cascade="all, delete-orphan")
    relationships_as_b = relationship("CharacterRelationship", foreign_keys="CharacterRelationship.char_b_id", back_populates="character_b", cascade="all, delete-orphan")

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
    novel_id = Column(Integer, index=True)
    branch_id = Column(String(100), default="main", index=True) # 分支 ID
    chapter_number = Column(Integer, index=True)
    scene_description = Column(Text) # 核心场面描写
    key_conflict = Column(Text)      # 核心冲突点
    foreshadowing = Column(JSON)      # 本章埋下的伏笔
    recalls = Column(JSON)           # 需要回收的伏笔
    status = Column(String(50), default="pending") # pending, completed, skipped
    
    # 修改复合唯一索引，包含 branch_id
    __table_args__ = (
        Index('idx_novel_branch_chapter', 'novel_id', 'branch_id', 'chapter_number', unique=True),
    )

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, index=True)
    branch_id = Column(String(100), default="main", index=True) # 分支 ID
    chapter_number = Column(Integer, nullable=False, index=True)
    previous_chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True) # 链表结构，用于回溯上下文
    title = Column(String(512))
    content = Column(Text)
    scene_tags = Column(JSON)        # 场景标签：战斗/对话/环境描写
    summary = Column(Text)           # 章节摘要
    logic_checked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 添加关系
    audits = relationship("LogicAudit", back_populates="chapter", cascade="all, delete-orphan")
    parent = relationship("Chapter", remote_side=[id], backref="children") # 自引用关系
    
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
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text)
    rarity = Column(String(100)) # 凡、灵、宝、仙、神
    powers = Column(JSON)       # 物品的具体数值或特殊词条
    owner_id = Column(Integer, ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)
    location = Column(String(255)) # 如果不在人身上，所在位置
    is_unique = Column(Boolean, default=True)

    owner = relationship("Character", back_populates="inventory")
