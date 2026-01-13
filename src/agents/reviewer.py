import os
import re
import json
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState, CharacterState
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, validate_character_consistency, normalize_llm_content
from .base import BaseAgent
from dotenv import load_dotenv

load_dotenv()

from .constants import SceneType, Defaults, PromptTemplates, ErrorMessages

class ReviewerAgent(BaseAgent):
    """
    Reviewer Agent (Gemini): 负责逻辑审查、人物OOC检查及状态演化。
    作为【王】进行最后的裁决。
    遵循 Rule 1.1 / 2.2: 逻辑与一致性守门人
    """
    def __init__(self, temperature: float = None):
        super().__init__(
            model_name="gemini",
            temperature=temperature or Config.model.DEEPSEEK_REVIEWER_TEMP,
            mock_responses=[
                # Response for review_draft
                json.dumps({"passed": True, "score": 0.9, "feedback": "Good job", "logical_errors": []}),
            ]
        )

    async def process(self, state: NGEState, draft: str) -> Dict[str, Any]:
        """
        BaseAgent required method.
        Delegates to review_draft.
        """
        return await self.review_draft(state, draft)

    async def review_draft(self, state: NGEState, draft: str, outline_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        检查生成的正文是否有逻辑漏洞或人物 OOC。
        遵循 Rule 3.3: 剧情防崩与连贯
        """
        # 提取当前所有角色禁忌
        character_rules = ""
        for name, char in state.characters.items():
            anchors = state.antigravity_context.character_anchors.get(name, [])
            if anchors:
                character_rules += f"- {name}: 禁止 {', '.join(anchors)}\n"

        # 提取全局伏笔
        active_threads = state.memory_context.global_foreshadowing
        threads_str = "\n".join([f"- {t}" for t in active_threads]) if active_threads else "无"

        # 大纲遵循度参考
        outline_context = ""
        if outline_info:
            outline_context = (
                f"\n【本章规划要求】\n"
                f"场景设定：{outline_info.get('scene', '无')}\n"
                f"核心冲突：{outline_info.get('conflict', '无')}\n"
            )

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极其敏锐的小说评论家和逻辑学家。你的任务是发现草稿中的任何微小漏洞。\n"
                f"{PromptTemplates.ANTIGRAVITY_WARNING}\n"
                "当前人物灵魂锚定：\n{character_rules}\n"
                "【需关注的未回收伏笔】：\n{threads_str}\n"
                "{outline_context}\n"
                "【审核重点】：\n"
                "1. 逻辑自洽性：是否存在前后矛盾或时空错误？\n"
                "2. 人物一致性：角色行为是否符合性格锚定？是否 OOC？\n"
                "3. 大纲遵循度：是否完成了规划要求的场景和核心冲突？\n"
                "4. 伏笔处理：是否按计划推进或回收了指定的伏笔？\n"
                "输出格式必须为 JSON。"
            )),
            ("human", (
                "请审查以下小说章节草稿，并给出详细反馈。\n"
                "剧情背景：{summary}\n"
                "草稿内容：\n{draft}\n\n"
                "必须包含以下字段：passed (bool), score (0.0-1.0), feedback (str), logical_errors (list)"
            ))
        ])

        last_summary = state.memory_context.recent_summaries[-1] if state.memory_context.recent_summaries else "开篇"
        
        # Use format_messages instead of format
        messages = prompt.format_messages(
            draft=draft, 
            summary=last_summary,
            character_rules=character_rules,
            threads_str=threads_str,
            outline_context=outline_context
        )
        response = await self.llm.ainvoke(messages)
        
        content_str = normalize_llm_content(response.content)
        content_str = strip_think_tags(content_str)
        result = extract_json_from_text(content_str)
        
        if not result:
            return {
                "passed": False, 
                "score": 0.0, 
                "feedback": "审核系统解析失败，请检查模型输出格式", 
                "logical_errors": ["Parse Error"]
            }
            
        return result
