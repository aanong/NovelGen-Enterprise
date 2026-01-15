"""
Agent 常量定义
集中管理所有魔法字符串和数字

注意：部分类型定义已迁移到 src/core/types.py
此文件保留向后兼容的导入和额外的常量定义
"""
from typing import Dict, Any

# 从核心模块导入类型定义（向后兼容）
from ..core.types import (
    SceneType,
    NodeAction,
    ReviewDecision,
    OutlineStatus,
    ForeshadowingStatus,
    ArcStatus,
)

# 重新导出以保持向后兼容
__all__ = [
    "SceneType",
    "NodeAction", 
    "ReviewDecision",
    "OutlineStatus",
    "ForeshadowingStatus",
    "ArcStatus",
    "Defaults",
    "PromptTemplates",
    "ErrorMessages",
    "SuccessMessages",
]


# 默认配置值
class Defaults:
    """
    默认配置值
    集中管理系统级别的默认参数
    """
    
    # ========== 章节相关 ==========
    MIN_CHAPTER_LENGTH = 2000       # 最小章节长度
    TARGET_CHAPTER_LENGTH = 3000    # 目标章节长度
    MAX_CHAPTER_LENGTH = 5000       # 最大章节长度
    
    # ========== 重试相关 ==========
    MAX_RETRY_LIMIT = 3             # 最大重试次数
    RETRY_DELAY_SECONDS = 1         # 重试延迟秒数
    
    # ========== 上下文相关 ==========
    RECENT_CHAPTERS_CONTEXT = 3     # 近期章节上下文数量
    MAX_CONTEXT_CHAPTERS = 10       # 最大上下文章节数
    MAX_CONTEXT_SUMMARIES = 3       # 提示词中使用的最大摘要数量（优化 token 使用）
    MAX_CHARACTERS_IN_PROMPT = 5   # 提示词中包含的最大角色数量（优化 token 使用）
    
    # ========== RAG 相关 ==========
    BIBLE_SEARCH_TOP_K = 3          # 世界观检索数量
    STYLE_SEARCH_TOP_K = 1          # 文风检索数量
    REFERENCE_SEARCH_TOP_K = 2      # 参考资料检索数量
    
    # ========== 逻辑审查 ==========
    MIN_LOGIC_SCORE = 0.7           # 最低逻辑评分
    MAX_LOGIC_SCORE = 1.0           # 最高逻辑评分
    
    # ========== 节奏控制 ==========
    RHYTHM_LOOKBACK_CHAPTERS = 5    # 节奏分析回看章节数
    HIGH_INTENSITY_THRESHOLD = 7    # 高强度阈值
    LOW_INTENSITY_THRESHOLD = 3     # 低强度阈值
    CONSECUTIVE_HIGH_LIMIT = 3      # 连续高强度章节限制
    CONSECUTIVE_LOW_LIMIT = 4       # 连续低强度章节限制
    
    # ========== 伏笔管理 ==========
    FORESHADOWING_LOOKAHEAD = 3     # 伏笔到期提前提醒章节数
    FORESHADOWING_OVERDUE_WARNING = True  # 是否开启过期警告
    
    # ========== 缓存相关 ==========
    CACHE_TTL_LLM_RESPONSE = 3600      # LLM 响应缓存 TTL（秒），默认 1 小时
    CACHE_TTL_EMBEDDING = 86400        # Embedding 缓存 TTL（秒），默认 24 小时
    CACHE_TTL_VECTOR_SEARCH = 300      # 向量检索缓存 TTL（秒），默认 5 分钟
    CACHE_TTL_PLAN_RESULT = 86400      # 规划结果缓存 TTL（秒），默认 24 小时
    
    # ========== 向量检索 ==========
    MAX_FALLBACK_ITEMS = 100           # Fallback 模式最大查询数量
    NOVEL_SPECIFIC_PRIORITY_BOOST = 1.2  # 小说特定项目的优先级提升倍数
    
    # ========== 重试相关 ==========
    MAX_STYLE_RETRIES = 2              # 风格问题最大重试次数


# 提示词模板片段
class PromptTemplates:
    """
    提示词模板片段
    用于构建 LLM 提示词的可复用组件
    """
    
    # 反重力规则警告
    ANTIGRAVITY_WARNING = """
【反重力规则警告】
- Rule 1.1: 严禁修改世界观设定，只能根据设定进行演绎
- Rule 2.1: 严禁人物性格突变或降智
- Rule 2.2: 严禁自发导致人物性格突变或降智
- Rule 3.3: 严禁逻辑硬伤
- Rule 4.1: 清除 AI 思考痕迹
- Rule 5.1: 循环熔断保护
- Rule 6.1: 场景化强制约束
"""
    
    # 人物锚定提示
    CHARACTER_ANCHOR_TEMPLATE = """
【人物灵魂锚定 - {character_name}】
- 禁止行为：{forbidden_actions}
- 当前状态：{current_mood}
- 技能：{skills}
- 资产：{assets}
"""
    
    # 场景约束提示
    SCENE_CONSTRAINT_TEMPLATE = """
【场景强制约束 - {scene_type}】
- 风格要求：{preferred_style}
- 禁忌模式：{forbidden_patterns}
"""
    
    # 伏笔管理提示
    FORESHADOWING_TEMPLATE = """
【伏笔管理要求】
1. 推进策略：明确指出本章应推进哪些已有的存量伏笔
2. 回收策略：如果剧情时机成熟，明确指出应在本章回收/揭晓的伏笔
3. 埋线策略：根据主线需要，本章是否需要埋下新的伏笔或悬念
"""
    
    # 节奏控制提示
    RHYTHM_TEMPLATE = """
【节奏控制要求】
- 节奏强度：{intensity}/10 ({intensity_desc})
- 节奏类型：{rhythm_type}
- 情绪基调：{emotional_tone}
- 避免模式：{avoid_patterns}
"""
    
    # 语言风格提示
    SPEECH_STYLE_TEMPLATE = """
【{character_name}的语言风格】
- 说话风格：{speech_pattern}
- 口头禅：{verbal_tics}
- 语气特点：{tone_modifiers}
"""


# 错误消息
class ErrorMessages:
    """错误消息常量"""
    PARSE_ERROR = "解析失败，请检查模型输出格式"
    LLM_ERROR = "LLM 调用失败"
    DATABASE_ERROR = "数据库操作失败"
    VALIDATION_ERROR = "输入验证失败"
    CONFIG_ERROR = "配置错误"
    WORKFLOW_ERROR = "工作流执行失败"
    ANTIGRAVITY_VIOLATION = "违反反重力规则"


# 成功消息
class SuccessMessages:
    """成功消息常量"""
    CHAPTER_GENERATED = "章节生成成功"
    REVIEW_PASSED = "审核通过"
    EVOLUTION_COMPLETE = "人物演化完成"
    CONTEXT_LOADED = "上下文加载完成"
    RHYTHM_ANALYZED = "节奏分析完成"
    ALLUSION_RECOMMENDED = "典故推荐完成"
    FORESHADOWING_PROCESSED = "伏笔处理完成"
