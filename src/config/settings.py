"""
Settings Module
Core configuration classes for NovelGen-Enterprise
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AntigravityConfig:
    """反重力规则配置"""
    
    # Rule 5.1 & 5.2: 循环熔断机制
    MAX_RETRY_LIMIT = int(os.getenv("MAX_RETRY_LIMIT", "3"))
    
    # Rule 3.1 & 3.2: 上下文滑窗准则
    RECENT_CHAPTERS_CONTEXT = int(os.getenv("RECENT_CHAPTERS_CONTEXT", "3"))
    MAX_CONTEXT_CHAPTERS = int(os.getenv("MAX_CONTEXT_CHAPTERS", "10"))
    
    # Rule 6: 场景化强制约束
    SCENE_CONSTRAINTS = {
        "Action": {
            "max_sentence_length": 20,
            "preferred_style": "短促动词为主",
            "forbidden_patterns": ["超过20字的长句"]
        },
        "Emotional": {
            "forbidden_patterns": ["连续动词堆叠"],
            "preferred_style": "心理描写为主"
        },
        "Dialogue": {
            "min_dialogue_ratio": 0.6,
            "preferred_style": "符合人物语气"
        }
    }
    
    # Rule 2.1: 人物灵魂锚定 - 默认禁忌行为模板
    DEFAULT_CHARACTER_FORBIDDEN = [
        "突然性格大变",
        "违背核心动机",
        "降智行为"
    ]


class ModelConfig:
    """模型配置"""
    
    # Gemini 配置 (Writer Agent)
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-3-pro-preview")
    GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.8"))
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # DeepSeek 配置 (Architect & Reviewer)
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-r1:7b")
    DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "http://localhost:11434/v1")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "ollama")
    DEEPSEEK_ARCHITECT_TEMP = float(os.getenv("DEEPSEEK_ARCHITECT_TEMP", "0.3"))
    DEEPSEEK_REVIEWER_TEMP = float(os.getenv("DEEPSEEK_REVIEWER_TEMP", "0.1"))
    
    # Setup Reviewer 配置
    SETUP_REVIEWER_MODEL = os.getenv("SETUP_REVIEWER_MODEL", "models/gemini-3-pro-preview")
    SETUP_REVIEWER_TEMP = float(os.getenv("SETUP_REVIEWER_TEMP", "0.3"))
    
    # Embedding 模型配置
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    
    # OpenAI 配置
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))


class DatabaseConfig:
    """数据库配置"""
    
    POSTGRES_URL = os.getenv("POSTGRES_URL")
    
    @classmethod
    def get_pool_size(cls) -> int:
        """Get connection pool size"""
        concurrent_tasks = int(os.getenv("CONCURRENT_TASKS", "5"))
        calculated_size = max(10, concurrent_tasks * 2)
        return int(os.getenv("DB_POOL_SIZE", str(calculated_size)))
    
    @classmethod
    def get_max_overflow(cls) -> int:
        """Get max overflow connection number"""
        pool_size = cls.get_pool_size()
        return int(os.getenv("DB_MAX_OVERFLOW", str(pool_size * 2)))
    
    POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    
    # Note: POOL_SIZE and MAX_OVERFLOW are initialized in src/config/__init__.py

class RedisConfig:
    """Redis 配置"""
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class WritingConfig:
    """写作配置"""
    
    # 章节字数要求
    MIN_CHAPTER_LENGTH = int(os.getenv("MIN_CHAPTER_LENGTH", "2000"))
    TARGET_CHAPTER_LENGTH = int(os.getenv("TARGET_CHAPTER_LENGTH", "3000"))
    
    # 文风分析
    ENABLE_STYLE_ANALYSIS = os.getenv("ENABLE_STYLE_ANALYSIS", "true").lower() == "true"
    
    # 逻辑审查
    ENABLE_LOGIC_AUDIT = os.getenv("ENABLE_LOGIC_AUDIT", "true").lower() == "true"
    MIN_LOGIC_SCORE = float(os.getenv("MIN_LOGIC_SCORE", "0.7"))
