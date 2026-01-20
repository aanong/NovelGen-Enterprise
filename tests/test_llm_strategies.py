"""
Unit tests for LLM Strategies Module
Tests the Strategy pattern for LLM provider selection
"""
import pytest
from unittest.mock import patch, MagicMock
from src.core.llm_strategies import (
    BaseLLMStrategy,
    GeminiStrategy,
    DeepSeekStrategy,
    OpenAIStrategy,
    LLMStrategyFactory
)


class TestBaseLLMStrategy:
    """Tests for BaseLLMStrategy abstract class"""

    def test_cannot_instantiate_directly(self):
        """Test that BaseLLMStrategy cannot be instantiated directly"""
        with pytest.raises(TypeError):
            BaseLLMStrategy()

    def test_has_abstract_create_llm(self):
        """Test that BaseLLMStrategy has abstract create_llm method"""
        assert hasattr(BaseLLMStrategy, 'create_llm')
        assert getattr(BaseLLMStrategy.create_llm, '__isabstractmethod__', False)


class TestGeminiStrategy:
    """Tests for GeminiStrategy"""

    def _create_mock_config(self):
        """Create a mock config for testing"""
        mock_config = MagicMock()
        mock_config.model.GEMINI_TEMPERATURE = 0.7
        mock_config.model.GEMINI_MODEL = "gemini-pro"
        mock_config.model.GEMINI_API_KEY = "test_api_key"
        return mock_config

    def test_create_llm_returns_google_genai(self):
        """Test that GeminiStrategy creates ChatGoogleGenerativeAI"""
        from langchain_google_genai import ChatGoogleGenerativeAI

        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = GeminiStrategy()
            llm = strategy.create_llm()
            assert isinstance(llm, ChatGoogleGenerativeAI)

    def test_create_llm_with_custom_temperature(self):
        """Test that GeminiStrategy respects custom temperature"""
        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = GeminiStrategy()
            llm = strategy.create_llm(temperature=0.5)
            assert llm.temperature == 0.5

    def test_create_llm_uses_default_temperature(self):
        """Test that GeminiStrategy uses default temperature from config"""
        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = GeminiStrategy()
            llm = strategy.create_llm()
            assert llm.temperature == 0.7


class TestDeepSeekStrategy:
    """Tests for DeepSeekStrategy"""

    def _create_mock_config(self):
        """Create a mock config for testing"""
        mock_config = MagicMock()
        mock_config.model.DEEPSEEK_ARCHITECT_TEMP = 0.3
        mock_config.model.DEEPSEEK_MODEL = "deepseek-chat"
        mock_config.model.DEEPSEEK_API_KEY = "test_deepseek_key"
        mock_config.model.DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
        mock_config.model.GEMINI_MODEL = "gemini-pro"
        mock_config.model.GEMINI_API_KEY = "test_gemini_key"
        return mock_config

    def test_create_llm_returns_openai_compatible(self):
        """Test that DeepSeekStrategy creates ChatOpenAI for remote API"""
        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = DeepSeekStrategy()
            llm = strategy.create_llm()

            from langchain_openai import ChatOpenAI
            assert isinstance(llm, ChatOpenAI)

    def test_create_llm_with_custom_temperature(self):
        """Test that DeepSeekStrategy respects custom temperature"""
        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = DeepSeekStrategy()
            llm = strategy.create_llm(temperature=0.9)
            assert llm.temperature == 0.9

    def test_fallback_to_gemini_for_localhost(self):
        """Test that DeepSeekStrategy falls back to Gemini for localhost"""
        mock_config = MagicMock()
        mock_config.model.DEEPSEEK_ARCHITECT_TEMP = 0.3
        mock_config.model.DEEPSEEK_API_BASE = "http://localhost:11434/v1"
        mock_config.model.DEEPSEEK_API_KEY = "ollama"
        mock_config.model.GEMINI_MODEL = "gemini-pro"
        mock_config.model.GEMINI_API_KEY = "test_gemini_key"

        with patch('src.core.llm_strategies.Config', mock_config):
            from langchain_google_genai import ChatGoogleGenerativeAI

            strategy = DeepSeekStrategy()
            llm = strategy.create_llm()

            assert isinstance(llm, ChatGoogleGenerativeAI)


class TestLLMStrategyFactory:
    """Tests for LLMStrategyFactory"""

    def test_get_gemini_strategy(self):
        """Test getting Gemini strategy"""
        strategy = LLMStrategyFactory.get_strategy("gemini")
        assert isinstance(strategy, GeminiStrategy)

    def test_get_deepseek_strategy(self):
        """Test getting DeepSeek strategy"""
        strategy = LLMStrategyFactory.get_strategy("deepseek")
        assert isinstance(strategy, DeepSeekStrategy)

    def test_get_logic_strategy(self):
        """Test getting logic strategy (uses DeepSeek)"""
        strategy = LLMStrategyFactory.get_strategy("logic")
        assert isinstance(strategy, DeepSeekStrategy)

    def test_get_openai_strategy(self):
        """Test getting OpenAI strategy"""
        strategy = LLMStrategyFactory.get_strategy("openai")
        assert isinstance(strategy, OpenAIStrategy)

    def test_get_unknown_strategy_defaults_to_gemini(self):
        """Test that unknown strategy defaults to Gemini"""
        strategy = LLMStrategyFactory.get_strategy("unknown")
        assert isinstance(strategy, GeminiStrategy)

    def test_get_strategy_case_insensitive(self):
        """Test that strategy name is case insensitive"""
        strategy1 = LLMStrategyFactory.get_strategy("GEMINI")
        strategy2 = LLMStrategyFactory.get_strategy("Gemini")
        strategy3 = LLMStrategyFactory.get_strategy("gemini")

        assert isinstance(strategy1, GeminiStrategy)
        assert isinstance(strategy2, GeminiStrategy)
        assert isinstance(strategy3, GeminiStrategy)

    def test_factory_has_required_strategies(self):
        """Test that factory has all expected strategies"""
        expected = ["gemini", "deepseek", "logic", "openai"]
        for name in expected:
            strategy = LLMStrategyFactory.get_strategy(name)
            assert strategy is not None
            assert isinstance(strategy, BaseLLMStrategy)


class TestOpenAIStrategy:
    """Tests for OpenAIStrategy"""

    def _create_mock_config(self):
        """Create a mock config for testing"""
        mock_config = MagicMock()
        mock_config.model.OPENAI_TEMPERATURE = 0.7
        mock_config.model.OPENAI_MODEL = "gpt-4o"
        mock_config.model.OPENAI_API_KEY = "test_openai_key"
        mock_config.model.OPENAI_API_BASE = "https://api.openai.com/v1"
        return mock_config

    def test_create_llm_returns_openai(self):
        """Test that OpenAIStrategy creates ChatOpenAI"""
        from langchain_openai import ChatOpenAI

        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = OpenAIStrategy()
            llm = strategy.create_llm()
            assert isinstance(llm, ChatOpenAI)

    def test_create_llm_with_custom_temperature(self):
        """Test that OpenAIStrategy respects custom temperature"""
        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = OpenAIStrategy()
            llm = strategy.create_llm(temperature=0.5)
            assert llm.temperature == 0.5

    def test_create_llm_uses_default_temperature(self):
        """Test that OpenAIStrategy uses default temperature from config"""
        mock_config = self._create_mock_config()
        with patch('src.core.llm_strategies.Config', mock_config):
            strategy = OpenAIStrategy()
            llm = strategy.create_llm()
            assert llm.temperature == 0.7
