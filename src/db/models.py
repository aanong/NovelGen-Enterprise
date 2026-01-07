from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from .base import Base
import datetime

class StyleRef(Base):
    __tablename__ = "style_ref"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON)  # Fallback: 使用 JSON 存储向量 (如果缺少 pgvector 扩展)
    source_author = Column(String(255))
    style_metadata = Column(JSON) # 存储句式统计、修辞分布等特征 (避免使用 python 内置关键字 metadata)

class NovelBible(Base):
    """世界观/设定集 (Novel Bible)"""
    __tablename__ = "novel_bible"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(100), index=True) # 如：地理, 战力体系, 关键道具, 历史背景
    key = Column(String(255), unique=True, index=True)
    content = Column(Text, nullable=False)
    importance = Column(Integer, default=5) # 1-10, 决定 RAG 检索时的权重
    tags = Column(JSON) # 用于联想检索

class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(100)) # 主角/配角/反派
    personality_traits = Column(JSON) # MBTI, BigFive, 核心动机, 缺陷
    evolution_log = Column(JSON)      # 章节成长记录
    current_mood = Column(String(100))
    status = Column(JSON)             # 当前生理/心理状态（受伤、狂喜等）
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class CharacterRelationship(Base):
    """人物关系矩阵"""
    __tablename__ = "character_relationships"

    id = Column(Integer, primary_key=True, index=True)
    char_a_id = Column(Integer, ForeignKey("characters.id"))
    char_b_id = Column(Integer, ForeignKey("characters.id"))
    relation_type = Column(String(100)) # 敌对, 盟友, 暧昧, 师徒等
    intimacy = Column(Float, default=0.0) # 亲密度等级 -1.0 到 1.0
    history = Column(JSON) # 记录影响关系的重大事件

class PlotOutline(Base):
    """细化剧情大纲"""
    __tablename__ = "plot_outlines"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, index=True)
    chapter_number = Column(Integer)
    scene_description = Column(Text) # 核心场面描写
    key_conflict = Column(Text)      # 核心冲突点
    foreshadowing = Column(JSON)      # 本章埋下的伏笔
    recalls = Column(JSON)           # 需要回收的伏笔
    status = Column(String(50), default="pending") # pending, completed, skipped

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    novel_id = Column(Integer, index=True)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(512))
    content = Column(Text)
    scene_tags = Column(JSON)        # 场景标签：战斗/对话/环境描写
    summary = Column(Text)           # 章节摘要
    logic_checked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LogicAudit(Base):
    """剧情逻辑审核记录"""
    __tablename__ = "logic_audits"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    reviewer_role = Column(String(100)) # Deepseek-Critic, Editor等
    is_passed = Column(Boolean)
    feedback = Column(Text) # 具体的逻辑漏洞或改进建议
    logic_score = Column(Float) # 0.0 - 1.0
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
