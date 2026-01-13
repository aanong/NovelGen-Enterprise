from typing import Optional, Dict, Any
import json
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState
from ..config import Config
from ..utils import strip_think_tags, normalize_llm_content, extract_json_from_text
from .base import BaseAgent
from .constants import PromptTemplates

class SummarizerAgent(BaseAgent):
    """
    Summarizer Agent: 负责生成章节摘要和更新故事上下文
    """
    def __init__(self, temperature: Optional[float] = None):
        super().__init__(
            model_name="gemini",
            temperature=temperature or 0.3, # Summary requires lower temperature for accuracy
            mock_responses=[
                json.dumps({
                    "summary": "This is a summary of the chapter.",
                    "key_events": ["Event 1", "Event 2"],
                    "character_status_updates": {}
                })
            ]
        )

    async def process(self, state: NGEState, chapter_content: str) -> Dict[str, Any]:
        return await self.summarize_chapter(state, chapter_content)

    async def summarize_chapter(self, state: NGEState, chapter_content: str) -> Dict[str, Any]:
        """
        生成章节摘要
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个专业的小说编辑，负责为每一章撰写精炼的摘要。\n"
                f"{PromptTemplates.ANTIGRAVITY_WARNING}\n"
                "你的目标是生成简洁明了的剧情概要，用于后续章节的上下文回顾。\n"
                "输出必须是 JSON 格式。"
            )),
            ("human", (
                "请为以下章节生成摘要：\n"
                "---\n"
                "{chapter_content}\n"
                "---\n"
                "请提取以下信息：\n"
                "1. summary: 200字以内的剧情梗概\n"
                "2. key_events: 关键事件列表\n"
                "3. character_status_updates: 角色状态的显著变化（如有）\n"
                "4. new_foreshadowing: 本章新埋下的伏笔或悬念列表（如有）\n"
                "5. resolved_threads: 本章已解决或推进的旧伏笔列表（如有）\n"
            ))
        ])

        messages = prompt.format_messages(chapter_content=chapter_content)
        response = await self.llm.ainvoke(messages)
        
        content = normalize_llm_content(response.content)
        content = strip_think_tags(content)
        return extract_json_from_text(content)
