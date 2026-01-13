"""
Agent 基类模块
提供统一的 Agent 接口和通用功能
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from ..config import Config
from ..utils import MockChatModel
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Agent 基类
    提供统一的接口和 LLM 初始化逻辑
    """
    
    def __init__(
        self,
        model_name: str = "gemini",
        temperature: Optional[float] = None,
        use_mock: bool = False,
        mock_responses: Optional[list] = None
    ):
        """
        初始化 Agent
        
        Args:
            model_name: 模型名称 ("gemini", "deepseek", "logic")
            temperature: 温度参数，如果为 None 则使用配置默认值
            use_mock: 是否使用 Mock 模型（用于测试）
            mock_responses: Mock 模型的响应列表
        """
        self.model_name = model_name
        self.temperature = temperature
        self.llm = self._init_llm(use_mock, mock_responses)
    
    def _init_llm(self, use_mock: bool, mock_responses: Optional[list]) -> Any:
        """
        初始化 LLM 实例
        
        Args:
            use_mock: 是否使用 Mock 模型
            mock_responses: Mock 响应列表
            
        Returns:
            LLM 实例
        """
        # 优先使用 Mock（用于测试）
        if use_mock or Config.model.GEMINI_MODEL == "mock":
            logger.info(f"{self.__class__.__name__} using MockChatModel")
            return MockChatModel(responses=mock_responses or [])
        
        # 根据模型名称选择对应的 LLM
        if self.model_name == "gemini":
            temp = self.temperature or Config.model.GEMINI_TEMPERATURE
            return ChatGoogleGenerativeAI(
                model=Config.model.GEMINI_MODEL,
                google_api_key=Config.model.GEMINI_API_KEY,
                temperature=temp
            )
        elif self.model_name in ("deepseek", "logic"):
            # 检查是否是本地 Ollama
            if "localhost" in Config.model.DEEPSEEK_API_BASE or Config.model.DEEPSEEK_API_KEY == "ollama":
                logger.info(f"{self.__class__.__name__} falling back to Gemini (Ollama not available)")
                temp = self.temperature or Config.model.DEEPSEEK_ARCHITECT_TEMP
                return ChatGoogleGenerativeAI(
                    model=Config.model.GEMINI_MODEL,
                    google_api_key=Config.model.GEMINI_API_KEY,
                    temperature=temp
                )
            else:
                temp = self.temperature or Config.model.DEEPSEEK_ARCHITECT_TEMP
                return ChatOpenAI(
                    model=Config.model.DEEPSEEK_MODEL,
                    openai_api_key=Config.model.DEEPSEEK_API_KEY,
                    openai_api_base=Config.model.DEEPSEEK_API_BASE,
                    temperature=temp
                )
        else:
            # 默认回退到 Gemini
            logger.warning(f"Unknown model_name '{self.model_name}', falling back to Gemini")
            temp = self.temperature or Config.model.GEMINI_TEMPERATURE
            return ChatGoogleGenerativeAI(
                model=Config.model.GEMINI_MODEL,
                google_api_key=Config.model.GEMINI_API_KEY,
                temperature=temp
            )
    
    @abstractmethod
    async def process(self, *args, **kwargs) -> Any:
        """
        处理任务的主方法（子类必须实现）
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            处理结果
        """
        pass
    
    def validate_input(self, *args, **kwargs) -> bool:
        """
        验证输入参数（子类可重写）
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            是否有效
        """
        return True
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取 Agent 信息
        
        Returns:
            Agent 信息字典
        """
        return {
            "name": self.__class__.__name__,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "llm_type": type(self.llm).__name__
        }
