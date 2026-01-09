from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from .config import Config

def get_llm(model_name: str = "gemini"):
    """
    获去统一配置的 LLM 实例。
    遵循 Rule 2.1 (双模型协作策略)。
    """
    if model_name == "gemini":
        return ChatGoogleGenerativeAI(
            model=Config.model.GEMINI_MODEL,
            google_api_key=Config.model.GEMINI_API_KEY,
            temperature=Config.model.GEMINI_TEMPERATURE
        )
    elif model_name == "deepseek" or model_name == "logic":
        # 如果提供了 DEEPSEEK_API_BASE 且包含 localhost/ollama，则可能是 Ollama
        return ChatOpenAI(
            model=Config.model.DEEPSEEK_MODEL,
            openai_api_key=Config.model.DEEPSEEK_API_KEY,
            base_url=Config.model.DEEPSEEK_API_BASE,
            temperature=Config.model.DEEPSEEK_ARCHITECT_TEMP
        )
    else:
        # 默认回退到 Gemini
        return ChatGoogleGenerativeAI(
            model=Config.model.GEMINI_MODEL,
            google_api_key=Config.model.GEMINI_API_KEY,
            temperature=0.7
        )
