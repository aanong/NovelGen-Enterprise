"""
Agent 常量定义
集中管理所有魔法字符串和数字
"""
from typing import Dict, Any

# 场景类型
class SceneType:
    """场景类型常量"""
    ACTION = "Action"
    EMOTIONAL = "Emotional"
    DIALOGUE = "Dialogue"
    NORMAL = "Normal"


# 节点动作
class NodeAction:
    """工作流节点动作常量"""
    INIT = "init"
    PLAN = "plan"
    REFINE_CONTEXT = "refine_context"
    WRITE = "write"
    REVIEW = "review"
    REVISE = "revise"
    EVOLVE = "evolve"
    REPAIR = "repair"
    FINALIZE = "finalize"


# 审核结果
class ReviewDecision:
    """审核决策常量"""
    CONTINUE = "continue"
    REVISE = "revise"
    REPAIR = "repair"


# 大纲状态
class OutlineStatus:
    """大纲状态常量"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# 默认配置值
class Defaults:
    """默认配置值"""
    # 章节相关
    MIN_CHAPTER_LENGTH = 2000
    TARGET_CHAPTER_LENGTH = 3000
    MAX_CHAPTER_LENGTH = 5000
    
    # 重试相关
    MAX_RETRY_LIMIT = 3
    RETRY_DELAY_SECONDS = 1
    
    # 上下文相关
    RECENT_CHAPTERS_CONTEXT = 3
    MAX_CONTEXT_CHAPTERS = 10
    
    # RAG 相关
    BIBLE_SEARCH_TOP_K = 3
    STYLE_SEARCH_TOP_K = 1
    REFERENCE_SEARCH_TOP_K = 2
    
    # 逻辑审查
    MIN_LOGIC_SCORE = 0.7
    MAX_LOGIC_SCORE = 1.0


# 提示词模板片段
class PromptTemplates:
    """提示词模板片段"""
    
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


# 错误消息
class ErrorMessages:
    """错误消息常量"""
    PARSE_ERROR = "解析失败，请检查模型输出格式"
    LLM_ERROR = "LLM 调用失败"
    DATABASE_ERROR = "数据库操作失败"
    VALIDATION_ERROR = "输入验证失败"
    CONFIG_ERROR = "配置错误"


# 成功消息
class SuccessMessages:
    """成功消息常量"""
    CHAPTER_GENERATED = "章节生成成功"
    REVIEW_PASSED = "审核通过"
    EVOLUTION_COMPLETE = "人物演化完成"
    CONTEXT_LOADED = "上下文加载完成"
