import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from ..schemas.style import StyleFeatures
from ..config import Config
from .base import BaseAgent
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

class StyleAnalyzer(BaseAgent):
    """
    文风分析 Agent，负责从参考文本中提取句式、修辞、节奏等特征。
    使用 Gemini 模型进行深度语义与风格分析。
    """
    def __init__(self, temperature: Optional[float] = None):
        super().__init__(
            model_name="gemini",
            temperature=temperature or 0.2,
            mock_responses=[
                '{"tone": "Dark", "rhetoric": ["Metaphor"], "keywords": ["Shadow"], "example_sentence": "Darkness fell."}'
            ]
        )
        self.parser = PydanticOutputParser(pydantic_object=StyleFeatures)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个专业且严谨的文学评论家和文风分析专家。\n"
                "你的任务是深度分析输入文本的文风特征，并以结构化的格式输出结果。\n"
                "必须关注以下维度：\n"
                "1. 句式长度分布 (短句/中长句比例)\n"
                "2. 常用修辞手法\n"
                "3. 对话与旁白的比例\n"
                "4. 整体情绪色调 (Tone)\n"
                "5. 核心词汇偏好\n"
                "6. 文字的节奏感 (Rhythm)\n\n"
                "{format_instructions}\n"
                "请在分析时保持客观，并提供深刻的洞察。"
            )),
            ("human", "请分析以下文本的文风特征：\n\n{text}")
        ])

    async def process(self, text: str) -> StyleFeatures:
        """
        BaseAgent required method.
        Delegates to analyze.
        """
        return await self.analyze(text)

    async def analyze(self, text: str) -> StyleFeatures:
        """
        异步分析给定文本的风格。
        """
        chain = self.prompt | self.llm | self.parser
        
        # 遵循 CoT 策略，LLM 内部推理后产出结构化结果
        result = await chain.ainvoke({
            "text": text,
            "format_instructions": self.parser.get_format_instructions()
        })
        return result

# 模块测试入口
if __name__ == "__main__":
    import asyncio
    
    async def test():
        analyzer = StyleAnalyzer()
        test_text = "屋外的雪下得紧，天地间只剩下一片惨白。他推开门，冷气灌了满怀。这种冷，不是皮肤上的，是骨子里的。"
        try:
            features = await analyzer.analyze(test_text)
            print(features.json(indent=4, ensure_ascii=False))
        except Exception as e:
            print(f"分析出错: {e}")

    # asyncio.run(test())
