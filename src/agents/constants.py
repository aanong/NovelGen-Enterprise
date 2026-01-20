"""
Agent 常量定义
集中管理所有魔法字符串和数字

注意：类型定义已迁移到 src/core/types.py，配置已迁移到 src/config/
此文件保留向后兼容的导入和类型定义
"""
from typing import Dict, Any

# 从核心模块导入类型定义
from ..core.types import (
    SceneType,
    NodeAction,
    ReviewDecision,
    OutlineStatus,
    ForeshadowingStatus,
    ArcStatus,
)

# 从配置模块导入常量（为了向后兼容）
from ..config.defaults import Defaults
from ..config.prompts import PromptTemplates
from ..config.messages import ErrorMessages, SuccessMessages

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
