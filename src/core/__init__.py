"""
NovelGen-Enterprise 核心模块
提供基础组件、工具类和通用接口
"""
from .llm_handler import (
    LLMResponseHandler,
    normalize_llm_content,
    strip_think_tags,
    extract_json_from_text,
)
from .types import (
    AgentResult,
    NodeResult,
    ResultStatus,
    SceneType,
    NodeAction,
    ReviewDecision,
    OutlineStatus,
    ForeshadowingStatus,
    ArcStatus,
)
from .exceptions import (
    NGEException,
    LLMParseError,
    ValidationError,
    DatabaseError,
    ConfigurationError,
    WorkflowError,
    AntigravityViolation,
)
from .factories import (
    AgentFactory,
    NodeFactory,
    DependencyContainer,
    get_container,
    get_agent_factory,
    get_node_factory,
)

__all__ = [
    # LLM 处理
    "LLMResponseHandler",
    "normalize_llm_content",
    "strip_think_tags",
    "extract_json_from_text",
    # 类型定义
    "AgentResult",
    "NodeResult",
    "ResultStatus",
    "SceneType",
    "NodeAction",
    "ReviewDecision",
    "OutlineStatus",
    "ForeshadowingStatus",
    "ArcStatus",
    # 异常
    "NGEException",
    "LLMParseError",
    "ValidationError",
    "DatabaseError",
    "ConfigurationError",
    "WorkflowError",
    "AntigravityViolation",
    # 工厂
    "AgentFactory",
    "NodeFactory",
    "DependencyContainer",
    "get_container",
    "get_agent_factory",
    "get_node_factory",
]
