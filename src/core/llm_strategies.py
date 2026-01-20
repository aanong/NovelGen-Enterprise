"""
LLM Strategies Module
Strategy pattern for LLM initialization
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from ..config import Config

class BaseLLMStrategy(ABC):
    """LLM Strategy Abstract Base Class"""
    
    @abstractmethod
    def create_llm(self, temperature: Optional[float] = None, **kwargs) -> Any:
        """
        Create an LLM instance
        
        Args:
            temperature: Model temperature
            **kwargs: Additional arguments
            
        Returns:
            LLM instance
        """
        pass

class GeminiStrategy(BaseLLMStrategy):
    """Strategy for Google Gemini"""
    
    def create_llm(self, temperature: Optional[float] = None, **kwargs) -> ChatGoogleGenerativeAI:
        temp = temperature or Config.model.GEMINI_TEMPERATURE
        return ChatGoogleGenerativeAI(
            model=Config.model.GEMINI_MODEL,
            google_api_key=Config.model.GEMINI_API_KEY,
            temperature=temp,
            **kwargs
        )

class DeepSeekStrategy(BaseLLMStrategy):
    """Strategy for DeepSeek (or OpenAI compatible)"""
    
    def create_llm(self, temperature: Optional[float] = None, **kwargs) -> Any:
        temp = temperature or Config.model.DEEPSEEK_ARCHITECT_TEMP
        
        # Check if using local Ollama (fallback to Gemini if localhost)
        is_local = "localhost" in Config.model.DEEPSEEK_API_BASE or Config.model.DEEPSEEK_API_KEY == "ollama"
        
        if is_local:
            # Fallback to Gemini for local execution
            return ChatGoogleGenerativeAI(
                model=Config.model.GEMINI_MODEL,
                google_api_key=Config.model.GEMINI_API_KEY,
                temperature=temp,
                **kwargs
            )
        
        return ChatOpenAI(
            model=Config.model.DEEPSEEK_MODEL,
            openai_api_key=Config.model.DEEPSEEK_API_KEY,
            openai_api_base=Config.model.DEEPSEEK_API_BASE,
            temperature=temp,
            **kwargs
        )

class OpenAIStrategy(BaseLLMStrategy):
    """Strategy for OpenAI"""
    
    def create_llm(self, temperature: Optional[float] = None, **kwargs) -> ChatOpenAI:
        temp = temperature or Config.model.OPENAI_TEMPERATURE
        return ChatOpenAI(
            model=Config.model.OPENAI_MODEL,
            openai_api_key=Config.model.OPENAI_API_KEY,
            openai_api_base=Config.model.OPENAI_API_BASE,
            temperature=temp,
            **kwargs
        )

class LLMStrategyFactory:
    """Factory to get the right strategy"""
    
    _strategies = {
        "gemini": GeminiStrategy(),
        "deepseek": DeepSeekStrategy(),
        "logic": DeepSeekStrategy(), # Logic uses DeepSeek config
        "openai": OpenAIStrategy(),
    }
    
    @classmethod
    def get_strategy(cls, name: str) -> BaseLLMStrategy:
        return cls._strategies.get(name.lower(), cls._strategies["gemini"])
