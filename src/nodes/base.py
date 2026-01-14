"""
Node 基类模块
提供统一的工作流节点接口和通用功能
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, Callable
from contextlib import contextmanager
from sqlalchemy.orm import Session
import logging

from ..schemas.state import NGEState
from ..db.base import SessionLocal
from ..core.types import NodeAction

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseNode(ABC):
    """
    工作流节点基类
    提供统一的接口和通用功能
    
    功能：
    1. 统一的节点执行接口
    2. 数据库会话管理
    3. 日志和错误处理
    4. 状态更新辅助方法
    """
    
    # 节点名称（子类可覆盖）
    node_name: str = "BaseNode"
    
    def __init__(self):
        """初始化节点"""
        self._execution_count = 0
    
    @abstractmethod
    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        """
        执行节点处理
        
        Args:
            state: 当前全局状态
            
        Returns:
            状态更新字典
        """
        pass
    
    @contextmanager
    def db_session(self):
        """
        数据库会话上下文管理器
        自动处理提交和回滚
        
        Yields:
            Session: 数据库会话
            
        Example:
            with self.db_session() as db:
                db.query(Model).filter(...).first()
        """
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"{self.node_name} 数据库操作失败: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    def create_result(
        self,
        next_action: str,
        **updates
    ) -> Dict[str, Any]:
        """
        创建统一的节点返回结果
        
        Args:
            next_action: 下一个动作
            **updates: 其他状态更新
            
        Returns:
            状态更新字典
        """
        result = {"next_action": next_action}
        result.update(updates)
        return result
    
    def log_start(self, state: NGEState, extra_info: str = ""):
        """
        记录节点开始执行
        
        Args:
            state: 当前状态
            extra_info: 额外信息
        """
        chapter = state.current_plot_index + 1
        branch = state.current_branch
        info = f" - {extra_info}" if extra_info else ""
        print(f"--- {self.node_name.upper()} (Ch.{chapter}, Branch: {branch}){info} ---")
        logger.info(f"{self.node_name} 开始执行: Chapter {chapter}, Branch {branch}")
    
    def log_success(self, message: str = "完成"):
        """记录成功"""
        print(f"✅ {self.node_name}: {message}")
        logger.info(f"{self.node_name}: {message}")
    
    def log_warning(self, message: str):
        """记录警告"""
        print(f"⚠️ {self.node_name}: {message}")
        logger.warning(f"{self.node_name}: {message}")
    
    def log_error(self, message: str, exc: Optional[Exception] = None):
        """记录错误"""
        print(f"❌ {self.node_name}: {message}")
        if exc:
            logger.error(f"{self.node_name}: {message}", exc_info=True)
        else:
            logger.error(f"{self.node_name}: {message}")
    
    def get_current_chapter(self, state: NGEState) -> int:
        """获取当前章节号（从1开始）"""
        return state.current_plot_index + 1
    
    def get_node_info(self) -> Dict[str, Any]:
        """
        获取节点信息
        
        Returns:
            节点信息字典
        """
        return {
            "name": self.node_name,
            "class": self.__class__.__name__,
            "execution_count": self._execution_count
        }
    
    async def safe_execute(
        self,
        func: Callable[..., T],
        *args,
        default: T = None,
        error_message: str = "执行失败",
        **kwargs
    ) -> T:
        """
        安全执行函数，捕获异常并返回默认值
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            default: 默认返回值
            error_message: 错误消息
            **kwargs: 关键字参数
            
        Returns:
            函数返回值或默认值
        """
        try:
            if callable(func):
                result = func(*args, **kwargs)
                # 处理协程
                if hasattr(result, '__await__'):
                    return await result
                return result
        except Exception as e:
            self.log_warning(f"{error_message}: {e}")
        return default


class AgentNode(BaseNode):
    """
    带 Agent 的节点基类
    为需要调用 Agent 的节点提供额外功能
    """
    
    def __init__(self, agent=None):
        """
        初始化 Agent 节点
        
        Args:
            agent: 关联的 Agent 实例
        """
        super().__init__()
        self.agent = agent
    
    async def invoke_agent(self, state: NGEState, **kwargs) -> Any:
        """
        调用关联的 Agent
        
        Args:
            state: 当前状态
            **kwargs: 额外参数
            
        Returns:
            Agent 处理结果
        """
        if self.agent is None:
            raise ValueError(f"{self.node_name} 没有关联的 Agent")
        
        return await self.agent.process(state, **kwargs)
