"""
Agent 基类模块
提供统一的 Agent 接口和通用功能
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Type
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from ..config import Config
from ..utils import MockChatModel
from ..core.llm_handler import LLMResponseHandler
from ..core.exceptions import LLMParseError
from ..core.cache import get_cache_manager
from ..core.llm_strategies import LLMStrategyFactory
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class BaseAgent(ABC):
    """
    Agent 基类
    提供统一的接口和 LLM 初始化逻辑
    
    功能：
    1. 自动初始化 LLM 实例（支持 Gemini、DeepSeek、Mock）
    2. 提供统一的响应处理方法
    3. 提供日志和错误处理
    4. 支持链式调用和模板化提示词
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
        self._use_mock = use_mock
        self._mock_responses = mock_responses
        self.llm = self._init_llm(use_mock, mock_responses)
        self._call_count = 0
    
    def _init_llm(self, use_mock: bool, mock_responses: Optional[list]) -> Any:
        """
        Initialize LLM instance
        
        Args:
            use_mock: Whether to use Mock model
            mock_responses: Mock response list
            
        Returns:
            LLM instance
        """
        # Priority 1: Use Mock (for testing)
        if use_mock or Config.model.GEMINI_MODEL == "mock":
            logger.info(f"{self.__class__.__name__} using MockChatModel")
            return MockChatModel(responses=mock_responses or [])
        
        # Priority 2: Use Strategy Pattern
        strategy = LLMStrategyFactory.get_strategy(self.model_name)
        logger.info(f"{self.__class__.__name__} using {strategy.__class__.__name__}")
        return strategy.create_llm(temperature=self.temperature)
    
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
    
    async def invoke_llm(
        self,
        prompt: ChatPromptTemplate,
        variables: Dict[str, Any],
        parse_json: bool = True,
        use_cache: bool = True,
        cache_ttl: int = 3600
    ) -> Dict[str, Any]:
        """
        调用 LLM 并处理响应（支持缓存）
        
        Args:
            prompt: 提示词模板
            variables: 模板变量
            parse_json: 是否解析 JSON
            use_cache: 是否使用缓存，默认 True
            cache_ttl: 缓存过期时间（秒），默认 1 小时
            
        Returns:
            处理后的响应字典
        """
        self._call_count += 1
        messages = prompt.format_messages(**variables)
        
        # 构建缓存键（使用完整的 prompt 和 variables）
        prompt_str = str(messages)
        cache_manager = get_cache_manager()
        
        # 尝试从缓存获取
        if use_cache and not self._use_mock:
            try:
                cached_response = await cache_manager.get_llm_response(
                    model_name=self.model_name,
                    prompt=prompt_str,
                    temperature=self.temperature
                )
                if cached_response:
                    logger.info(f"{self.__class__.__name__} 使用缓存响应")
                    result = LLMResponseHandler.process_response(
                        type('obj', (object,), {'content': cached_response})(),
                        extract_json=parse_json
                    )
                    return result
            except Exception as e:
                logger.debug(f"缓存查询失败: {e}，继续调用 LLM")
        
        # 调用 LLM
        try:
            response = await self.llm.ainvoke(messages)
            result = LLMResponseHandler.process_response(response, extract_json=parse_json)
            
            # 保存到缓存
            if use_cache and not self._use_mock and result.get("success"):
                try:
                    await cache_manager.set_llm_response(
                        model_name=self.model_name,
                        prompt=prompt_str,
                        response=result.get("cleaned", result.get("raw", "")),
                        ttl=cache_ttl,
                        temperature=self.temperature
                    )
                except Exception as e:
                    logger.debug(f"保存缓存失败: {e}")
            
            if not result["success"] and parse_json:
                logger.warning(f"{self.__class__.__name__} 无法解析 JSON 响应")
            
            return result
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__} LLM 调用失败: {e}", exc_info=True)
            return {
                "raw": "",
                "cleaned": "",
                "json": None,
                "success": False,
                "error": str(e)
            }
    
    async def invoke_and_parse(
        self,
        prompt: ChatPromptTemplate,
        variables: Dict[str, Any],
        model_class: Type[T],
        default: Optional[T] = None
    ) -> Optional[T]:
        """
        调用 LLM 并解析为 Pydantic 模型
        
        Args:
            prompt: 提示词模板
            variables: 模板变量
            model_class: 目标 Pydantic 模型类
            default: 解析失败时的默认值
            
        Returns:
            解析后的模型实例，或默认值
        """
        result = await self.invoke_llm(prompt, variables, parse_json=True)
        
        if result.get("json"):
            try:
                return model_class.model_validate(result["json"])
            except Exception as e:
                logger.warning(f"模型验证失败: {e}")
        
        return default
    
    def clean_response(self, content: Any) -> str:
        """
        清洗 LLM 响应
        
        Args:
            content: 原始响应内容
            
        Returns:
            清洗后的内容
        """
        return LLMResponseHandler.clean(content)
    
    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从文本中提取 JSON
        
        Args:
            text: 包含 JSON 的文本
            
        Returns:
            解析后的 JSON 对象
        """
        return LLMResponseHandler.extract_json(text)
    
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
            "llm_type": type(self.llm).__name__,
            "call_count": self._call_count
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self._call_count = 0
