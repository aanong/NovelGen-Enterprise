"""
NovelGen-Enterprise 配置管理
集中管理所有配置项，包括 Antigravity Rules 参数
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
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
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


class DatabaseConfig:
    """数据库配置"""
    
    POSTGRES_URL = os.getenv("POSTGRES_URL")
    POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))


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


class Config:
    """主配置类"""
    
    antigravity = AntigravityConfig
    model = ModelConfig
    database = DatabaseConfig
    writing = WritingConfig
    
    # 项目信息
    PROJECT_NAME = "NovelGen-Enterprise"
    VERSION = "1.0.0"
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """验证配置完整性"""
        issues = []
        
        if not cls.model.GEMINI_API_KEY:
            issues.append("缺少 GOOGLE_API_KEY")
        
        if not cls.database.POSTGRES_URL:
            issues.append("缺少 POSTGRES_URL")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    @classmethod
    def print_config(cls):
        """打印当前配置（隐藏敏感信息）"""
        print(f"🔧 {cls.PROJECT_NAME} v{cls.VERSION} 配置")
        print(f"├─ Gemini Model: {cls.model.GEMINI_MODEL}")
        print(f"├─ DeepSeek Model: {cls.model.DEEPSEEK_MODEL}")
        print(f"├─ Max Retry Limit: {cls.antigravity.MAX_RETRY_LIMIT}")
        print(f"├─ Context Window: {cls.antigravity.RECENT_CHAPTERS_CONTEXT} 章")
        print(f"├─ Min Chapter Length: {cls.writing.MIN_CHAPTER_LENGTH} 字")
        print(f"└─ Logic Audit: {'启用' if cls.writing.ENABLE_LOGIC_AUDIT else '禁用'}")


if __name__ == "__main__":
    Config.print_config()
    validation = Config.validate()
    if not validation["valid"]:
        print("\n⚠️ 配置问题:")
        for issue in validation["issues"]:
            print(f"  - {issue}")
