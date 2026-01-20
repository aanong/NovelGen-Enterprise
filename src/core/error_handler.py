"""
错误处理模块
提供统一的错误分类、友好的错误消息和重试策略
"""
import asyncio
import logging
from enum import Enum
from typing import Any, Dict, Optional, Type
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""
    # 临时错误（可重试）
    TEMPORARY = "temporary"
    NETWORK_ERROR = "network_error"  # 网络错误
    RATE_LIMIT = "rate_limit"  # 速率限制
    TIMEOUT = "timeout"  # 超时
    SERVICE_UNAVAILABLE = "service_unavailable"  # 服务不可用

    # 永久错误（不可重试）
    PERMANENT = "permanent"
    INVALID_INPUT = "invalid_input"  # 无效输入
    AUTHENTICATION_ERROR = "authentication_error"  # 认证错误
    PERMISSION_DENIED = "permission_denied"  # 权限不足
    RESOURCE_NOT_FOUND = "resource_not_found"  # 资源不存在
    VALIDATION_ERROR = "validation_error"  # 验证错误
    QUOTA_EXCEEDED = "quota_exceeded"  # 配额超限

    # 系统错误
    SYSTEM_ERROR = "system_error"
    DATABASE_ERROR = "database_error"  # 数据库错误
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


class NGEDomainError(Exception):
    """NGE 领域异常基类"""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        original_exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.original_exception = original_exception
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_type": self.error_type.value,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp
        }

    def __str__(self) -> str:
        return f"[{self.error_type.value}] {self.message}"


class LLMError(NGEDomainError):
    """LLM 相关错误"""

    def __init__(
        self,
        message: str,
        model_name: str = "unknown",
        **kwargs
    ):
        # 根据消息内容判断错误类型
        if "rate" in message.lower() or "quota" in message.lower():
            error_type = ErrorType.RATE_LIMIT
        elif "timeout" in message.lower() or "timed out" in message.lower():
            error_type = ErrorType.TIMEOUT
        elif "authentication" in message.lower() or "api key" in message.lower():
            error_type = ErrorType.AUTHENTICATION_ERROR
        else:
            error_type = ErrorType.TEMPORARY

        super().__init__(
            message=message,
            error_type=error_type,
            **kwargs
        )
        self.model_name = model_name


class DatabaseError(NGEDomainError):
    """数据库相关错误"""

    def __init__(
        self,
        message: str,
        operation: str = "unknown",
        table: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.DATABASE_ERROR,
            **kwargs
        )
        self.operation = operation
        self.table = table


class ValidationError(NGEDomainError):
    """验证错误"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.VALIDATION_ERROR,
            **kwargs
        )
        self.field = field
        self.value = value


class ErrorHandler:
    """
    错误处理器
    提供错误分类、友好消息生成和重试决策
    """

    # 错误类型到重试策略的映射
    RETRYABLE_ERRORS = {
        ErrorType.NETWORK_ERROR,
        ErrorType.RATE_LIMIT,
        ErrorType.TIMEOUT,
        ErrorType.SERVICE_UNAVAILABLE,
        ErrorType.DATABASE_ERROR,
    }

    # 临时错误的重试延迟（秒）
    RETRY_DELAYS = {
        ErrorType.RATE_LIMIT: 30,  # 速率限制需要更长的等待
        ErrorType.TIMEOUT: 10,
        ErrorType.NETWORK_ERROR: 5,
        ErrorType.SERVICE_UNAVAILABLE: 15,
        ErrorType.DATABASE_ERROR: 5,
    }

    @classmethod
    def classify_error(cls, error: Exception) -> tuple[ErrorType, str]:
        """
        分类错误并返回错误类型和原始消息

        Args:
            error: 异常对象

        Returns:
            (错误类型, 原始错误消息)
        """
        error_msg = str(error).lower()
        original_msg = str(error)

        # LLM 相关错误
        if "gemini" in error_msg or "google" in error_msg:
            if "rate" in error_msg or "quota" in error_msg:
                return ErrorType.RATE_LIMIT, original_msg
            elif "authentication" in error_msg or "api key" in error_msg:
                return ErrorType.AUTHENTICATION_ERROR, original_msg
            elif "timeout" in error_msg:
                return ErrorType.TIMEOUT, original_msg
            else:
                return ErrorType.TEMPORARY, original_msg

        # DeepSeek 相关错误
        if "deepseek" in error_msg or "ollama" in error_msg:
            if "rate" in error_msg or "quota" in error_msg:
                return ErrorType.RATE_LIMIT, original_msg
            elif "connection" in error_msg or "network" in error_msg:
                return ErrorType.NETWORK_ERROR, original_msg
            elif "timeout" in error_msg:
                return ErrorType.TIMEOUT, original_msg
            else:
                return ErrorType.TEMPORARY, original_msg

        # 数据库错误
        if "sql" in error_msg or "database" in error_msg or "connection" in error_msg:
            if "duplicate" in error_msg:
                return ErrorType.VALIDATION_ERROR, original_msg
            else:
                return ErrorType.DATABASE_ERROR, original_msg

        # 认证错误
        if "auth" in error_msg or "unauthorized" in error_msg or "forbidden" in error_msg:
            return ErrorType.AUTHENTICATION_ERROR, original_msg

        # 超时错误
        if "timeout" in error_msg or "timed out" in error_msg:
            return ErrorType.TIMEOUT, original_msg

        # 速率限制
        if "rate limit" in error_msg or "too many requests" in error_msg:
            return ErrorType.RATE_LIMIT, original_msg

        # 默认分类
        return ErrorType.UNKNOWN_ERROR, original_msg

    @classmethod
    def get_friendly_error_message(cls, error: Exception) -> str:
        """
        获取友好的错误消息

        Args:
            error: 异常对象

        Returns:
            用户友好的错误消息
        """
        error_type, _ = cls.classify_error(error)

        friendly_messages = {
            ErrorType.RATE_LIMIT: "API 调用频率超限，请稍后重试",
            ErrorType.TIMEOUT: "请求超时，请检查网络连接后重试",
            ErrorType.NETWORK_ERROR: "网络连接失败，请检查网络后重试",
            ErrorType.AUTHENTICATION_ERROR: "认证失败，请检查 API 密钥配置",
            ErrorType.QUOTA_EXCEEDED: "API 配额已用完，请升级或等待配额重置",
            ErrorType.DATABASE_ERROR: "数据库操作失败，请稍后重试",
            ErrorType.INVALID_INPUT: "输入数据无效，请检查后重新提交",
            ErrorType.RESOURCE_NOT_FOUND: "请求的资源不存在",
            ErrorType.VALIDATION_ERROR: "数据验证失败，请检查输入内容",
            ErrorType.PERMISSION_DENIED: "权限不足，无法执行此操作",
            ErrorType.SERVICE_UNAVAILABLE: "服务暂时不可用，请稍后重试",
            ErrorType.UNKNOWN_ERROR: "发生未知错误，请稍后重试",
        }

        return friendly_messages.get(error_type, "发生错误，请稍后重试")

    @classmethod
    def should_retry(cls, error: Exception, retry_count: int = 0) -> tuple[bool, Optional[int]]:
        """
        判断是否应该重试

        Args:
            error: 异常对象
            retry_count: 当前重试次数

        Returns:
            (是否重试, 重试延迟秒数)
        """
        error_type, _ = cls.classify_error(error)

        # 检查是否是可重试的错误类型
        if error_type not in cls.RETRYABLE_ERRORS:
            return False, None

        # 检查重试次数是否超限
        max_retries = 3
        if retry_count >= max_retries:
            logger.warning(f"重试次数已达上限 ({max_retries})，放弃重试")
            return False, None

        # 计算重试延迟（使用指数退避）
        base_delay = cls.RETRY_DELAYS.get(error_type, 5)
        delay = min(base_delay * (2 ** retry_count), 60)  # 最大延迟 60 秒

        return True, delay

    @classmethod
    async def execute_with_retry(
        cls,
        func,
        *args,
        max_retries: int = 3,
        **kwargs
    ) -> Any:
        """
        带重试的异步执行

        Args:
            func: 异步函数
            *args: 函数参数
            max_retries: 最大重试次数
            **kwargs: 函数关键字参数

        Returns:
            函数返回值

        Raises:
            最终的异常（如果重试耗尽）
        """
        last_error = None

        for retry_count in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                should_retry, delay = cls.should_retry(e, retry_count)

                if not should_retry:
                    logger.warning(f"错误不可重试: {e}")
                    raise

                logger.warning(
                    f"第 {retry_count + 1} 次尝试失败: {e}，"
                    f"{delay} 秒后重试"
                )

                await asyncio.sleep(delay)

        raise last_error

    @classmethod
    def log_error(
        cls,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error"
    ) -> None:
        """
        记录错误日志

        Args:
            error: 异常对象
            context: 错误上下文
            level: 日志级别
        """
        error_type, error_msg = cls.classify_error(error)
        log_data = {
            "error_type": error_type.value,
            "error_message": error_msg,
            "context": context or {}
        }

        log_func = getattr(logger, level, logger.error)
        log_func(f"错误发生: {json.dumps(log_data, ensure_ascii=False)}")

        # 如果是严重错误，同时打印到控制台
        if level == "error":
            print(f"❌ [{error_type.value}] {error_msg}")


class CircuitBreaker:
    """
    熔断器
    防止持续调用失败的服务，保护系统稳定性
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_time: int = 60,
        half_open_requests: int = 3
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 失败阈值（连续失败次数）
            recovery_time: 恢复时间（秒）
            half_open_requests: 半开状态允许的请求数
        """
        self._failure_count = 0
        self._success_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_time = recovery_time
        self._half_open_requests = half_open_requests
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half_open

    @property
    def state(self) -> str:
        """获取当前状态"""
        if self._state == "open":
            # 检查是否应该进入半开状态
            if self._last_failure_time:
                elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
                if elapsed >= self._recovery_time:
                    self._state = "half_open"
                    self._success_count = 0
        return self._state

    def record_success(self) -> None:
        """记录成功"""
        if self._state == "half_open":
            self._success_count += 1
            if self._success_count >= self._half_open_requests:
                self._state = "closed"
                self._failure_count = 0
                logger.info("熔断器已关闭，服务恢复正常")

    def record_failure(self) -> None:
        """记录失败"""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()

        if self._state == "half_open":
            self._state = "open"
            logger.warning("熔断器打开，服务不可用")

        elif self._failure_count >= self._failure_threshold:
            self._state = "open"
            logger.warning(f"熔断器打开，连续失败 {self._failure_threshold} 次")

    def allow_request(self) -> bool:
        """是否允许请求"""
        return self.state != "open"

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self._failure_threshold,
            "recovery_time": self._recovery_time
        }


# 全局熔断器实例
_llm_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_time=60,
    half_open_requests=3
)


def get_llm_circuit_breaker() -> CircuitBreaker:
    """获取 LLM 熔断器"""
    return _llm_circuit_breaker


if __name__ == "__main__":
    # 测试错误分类
    test_errors = [
        Exception("Rate limit exceeded for Gemini API"),
        Exception("Connection timeout"),
        Exception("Database connection failed"),
        Exception("Authentication failed for API key"),
        Exception("Unknown error occurred"),
    ]

    print("错误分类测试:")
    for error in test_errors:
        error_type, original_msg = ErrorHandler.classify_error(error)
        friendly_msg = ErrorHandler.get_friendly_error_message(error)
        should_retry, delay = ErrorHandler.should_retry(error)
        print(f"  - {original_msg}")
        print(f"    类型: {error_type.value}, 友好消息: {friendly_msg}")
        print(f"    可重试: {should_retry}, 延迟: {delay}s")
        print()
