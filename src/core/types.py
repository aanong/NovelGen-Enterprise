"""
NovelGen-Enterprise 类型定义
统一的类型和数据类定义
"""
from typing import Dict, Any, Optional, List, TypeVar, Generic
from pydantic import BaseModel, Field
from enum import Enum


# ============ 通用类型 ============

T = TypeVar('T')


class ResultStatus(str, Enum):
    """结果状态枚举"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class BaseResult(BaseModel, Generic[T]):
    """
    通用结果包装类
    用于统一封装 Agent 和 Node 的返回值
    """
    status: ResultStatus = Field(default=ResultStatus.SUCCESS)
    data: Optional[T] = Field(default=None, description="结果数据")
    message: str = Field(default="", description="结果消息")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    
    def is_success(self) -> bool:
        """检查是否成功"""
        return self.status == ResultStatus.SUCCESS
    
    def is_failure(self) -> bool:
        """检查是否失败"""
        return self.status == ResultStatus.FAILURE


class AgentResult(BaseModel):
    """
    Agent 处理结果
    统一的 Agent 返回格式
    """
    success: bool = Field(default=True, description="是否成功")
    data: Dict[str, Any] = Field(default_factory=dict, description="结果数据")
    raw_response: Optional[str] = Field(default=None, description="原始 LLM 响应")
    tokens_used: int = Field(default=0, description="消耗的 token 数")
    model_name: Optional[str] = Field(default=None, description="使用的模型名称")
    error_message: Optional[str] = Field(default=None, description="错误消息")
    
    @classmethod
    def from_error(cls, error: str, raw_response: Optional[str] = None) -> "AgentResult":
        """从错误创建结果"""
        return cls(
            success=False,
            error_message=error,
            raw_response=raw_response
        )
    
    @classmethod
    def from_data(cls, data: Dict[str, Any], **kwargs) -> "AgentResult":
        """从数据创建结果"""
        return cls(success=True, data=data, **kwargs)


class NodeResult(BaseModel):
    """
    Node 处理结果
    统一的 Node 返回格式
    """
    next_action: str = Field(description="下一个动作")
    state_updates: Dict[str, Any] = Field(
        default_factory=dict, 
        description="状态更新"
    )
    success: bool = Field(default=True)
    message: Optional[str] = Field(default=None)
    
    def to_state_dict(self) -> Dict[str, Any]:
        """转换为状态更新字典"""
        result = {"next_action": self.next_action}
        result.update(self.state_updates)
        return result


# ============ 场景类型 ============

class SceneType(str, Enum):
    """场景类型枚举"""
    ACTION = "Action"
    EMOTIONAL = "Emotional"
    DIALOGUE = "Dialogue"
    NORMAL = "Normal"
    TRANSITION = "Transition"


# ============ 节点动作 ============

class NodeAction(str, Enum):
    """工作流节点动作枚举"""
    INIT = "init"
    PLAN = "plan"
    REFINE_CONTEXT = "refine_context"
    WRITE = "write"
    REVIEW = "review"
    REVISE = "revise"
    EVOLVE = "evolve"
    REPAIR = "repair"
    FINALIZE = "finalize"


class ReviewDecision(str, Enum):
    """审核决策枚举"""
    CONTINUE = "continue"
    REVISE = "revise"
    REPAIR = "repair"


# ============ 状态类型 ============

class OutlineStatus(str, Enum):
    """大纲状态枚举"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ForeshadowingStatus(str, Enum):
    """伏笔状态枚举"""
    PLANTED = "planted"
    ADVANCED = "advanced"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


class ArcStatus(str, Enum):
    """人物弧光状态枚举"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
