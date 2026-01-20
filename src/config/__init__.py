"""
Config Module
Unified configuration interface for NovelGen-Enterprise
"""

from .settings import AntigravityConfig, ModelConfig, DatabaseConfig, RedisConfig, WritingConfig
from .defaults import Defaults
from .prompts import PromptTemplates
from .messages import ErrorMessages, SuccessMessages

# Initialize DatabaseConfig attributes that require method calls
DatabaseConfig.POOL_SIZE = DatabaseConfig.get_pool_size()
DatabaseConfig.MAX_OVERFLOW = DatabaseConfig.get_max_overflow()

class Config:
    """主配置类"""
    
    antigravity = AntigravityConfig
    model = ModelConfig
    database = DatabaseConfig
    redis = RedisConfig
    writing = WritingConfig
    defaults = Defaults
    prompts = PromptTemplates
    messages = ErrorMessages
    
    # 项目信息
    PROJECT_NAME = "NovelGen-Enterprise"
    VERSION = "1.0.0"
    
    @classmethod
    def validate(cls) -> dict:
        """验证配置完整性"""
        issues = []
        warnings = []
        
        if not cls.model.GEMINI_API_KEY:
            issues.append("缺少 GOOGLE_API_KEY (必需)")
        
        if not cls.database.POSTGRES_URL:
            issues.append("缺少 POSTGRES_URL (必需)")
        
        if cls.antigravity.MAX_RETRY_LIMIT < 1:
            issues.append(f"MAX_RETRY_LIMIT 必须 >= 1，当前值: {cls.antigravity.MAX_RETRY_LIMIT}")
        
        if cls.antigravity.MAX_RETRY_LIMIT > 10:
            warnings.append(f"MAX_RETRY_LIMIT 过大 ({cls.antigravity.MAX_RETRY_LIMIT})，可能导致长时间等待")
        
        if cls.writing.MIN_CHAPTER_LENGTH > cls.writing.TARGET_CHAPTER_LENGTH:
            issues.append(
                f"MIN_CHAPTER_LENGTH ({cls.writing.MIN_CHAPTER_LENGTH}) "
                f"不能大于 TARGET_CHAPTER_LENGTH ({cls.writing.TARGET_CHAPTER_LENGTH})"
            )
        
        if cls.writing.MIN_LOGIC_SCORE < 0 or cls.writing.MIN_LOGIC_SCORE > 1:
            issues.append(f"MIN_LOGIC_SCORE 必须在 0-1 之间，当前值: {cls.writing.MIN_LOGIC_SCORE}")
        
        if cls.database.POOL_SIZE < 1:
            issues.append(f"DB_POOL_SIZE 必须 >= 1，当前值: {cls.database.POOL_SIZE}")
        
        if cls.database.MAX_OVERFLOW < 0:
            issues.append(f"DB_MAX_OVERFLOW 必须 >= 0，当前值: {cls.database.MAX_OVERFLOW}")
        
        if cls.model.GEMINI_TEMPERATURE < 0 or cls.model.GEMINI_TEMPERATURE > 2:
            warnings.append(f"GEMINI_TEMPERATURE 超出推荐范围 (0-2)，当前值: {cls.model.GEMINI_TEMPERATURE}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @classmethod
    def print_config(cls):
        """打印当前配置（隐藏敏感信息）"""
        print(f"🔧 {cls.PROJECT_NAME} v{cls.VERSION} 配置")
        print(f"├─ Gemini Model: {cls.model.GEMINI_MODEL}")
        print(f"├─ DeepSeek Model: {cls.model.DEEPSEEK_MODEL}")
        print(f"├─ OpenAI Model: {cls.model.OPENAI_MODEL}")
        print(f"├─ Max Retry Limit: {cls.antigravity.MAX_RETRY_LIMIT}")
        print(f"├─ Context Window: {cls.antigravity.RECENT_CHAPTERS_CONTEXT} 章")
        print(f"├─ Min Chapter Length: {cls.writing.MIN_CHAPTER_LENGTH} 字")
        print(f"└─ Logic Audit: {'启用' if cls.writing.ENABLE_LOGIC_AUDIT else '禁用'}")
