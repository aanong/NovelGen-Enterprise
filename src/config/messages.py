"""
Messages Module
Error and Success messages
"""

class ErrorMessages:
    """错误消息常量"""
    PARSE_ERROR = "解析失败，请检查模型输出格式"
    LLM_ERROR = "LLM 调用失败"
    DATABASE_ERROR = "数据库操作失败"
    VALIDATION_ERROR = "输入验证失败"
    CONFIG_ERROR = "配置错误"
    WORKFLOW_ERROR = "工作流执行失败"
    ANTIGRAVITY_VIOLATION = "违反反重力规则"

class SuccessMessages:
    """成功消息常量"""
    CHAPTER_GENERATED = "章节生成成功"
    REVIEW_PASSED = "审核通过"
    EVOLUTION_COMPLETE = "人物演化完成"
    CONTEXT_LOADED = "上下文加载完成"
    RHYTHM_ANALYZED = "节奏分析完成"
    ALLUSION_RECOMMENDED = "典故推荐完成"
    FORESHADOWING_PROCESSED = "伏笔处理完成"
