"""
NovelGen-Enterprise 异常定义
统一的异常类层次结构
"""
from typing import Optional, List, Dict, Any


class NGEException(Exception):
    """
    NovelGen-Enterprise 基础异常类
    所有自定义异常的基类
    """
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化异常
        
        Args:
            message: 错误消息
            code: 错误代码
            details: 额外的错误详情
        """
        super().__init__(message)
        self.message = message
        self.code = code or "NGE_ERROR"
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


class LLMParseError(NGEException):
    """
    LLM 响应解析错误
    当无法解析 LLM 输出时抛出
    """
    
    def __init__(
        self, 
        message: str = "无法解析 LLM 响应",
        raw_content: Optional[str] = None
    ):
        super().__init__(
            message=message,
            code="LLM_PARSE_ERROR",
            details={"raw_content": raw_content[:500] if raw_content else None}
        )
        self.raw_content = raw_content


class ValidationError(NGEException):
    """
    输入验证错误
    当输入数据不符合要求时抛出
    """
    
    def __init__(
        self, 
        message: str = "输入验证失败",
        field: Optional[str] = None,
        violations: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={
                "field": field,
                "violations": violations or []
            }
        )
        self.field = field
        self.violations = violations or []


class DatabaseError(NGEException):
    """
    数据库操作错误
    当数据库操作失败时抛出
    """
    
    def __init__(
        self, 
        message: str = "数据库操作失败",
        operation: Optional[str] = None,
        table: Optional[str] = None
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details={
                "operation": operation,
                "table": table
            }
        )


class ConfigurationError(NGEException):
    """
    配置错误
    当配置缺失或无效时抛出
    """
    
    def __init__(
        self, 
        message: str = "配置错误",
        config_key: Optional[str] = None
    ):
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            details={"config_key": config_key}
        )


class WorkflowError(NGEException):
    """
    工作流执行错误
    当工作流节点执行失败时抛出
    """
    
    def __init__(
        self, 
        message: str = "工作流执行错误",
        node_name: Optional[str] = None,
        state_info: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            code="WORKFLOW_ERROR",
            details={
                "node_name": node_name,
                "state_info": state_info
            }
        )


class AntigravityViolation(NGEException):
    """
    反重力规则违反
    当生成的内容违反 Antigravity Rules 时抛出
    """
    
    def __init__(
        self, 
        message: str = "违反反重力规则",
        rule_id: Optional[str] = None,
        violations: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            code="ANTIGRAVITY_VIOLATION",
            details={
                "rule_id": rule_id,
                "violations": violations or []
            }
        )
        self.rule_id = rule_id
        self.violations = violations or []
