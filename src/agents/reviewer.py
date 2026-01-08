import os
import re
import json
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState, character_state
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, validate_character_consistency
from dotenv import load_dotenv

load_dotenv()

class ReviewerAgent:
    """
    Reviewer Agent (Deepseek): 负责逻辑审查、人物OOC检查及状态演化。
    遵循 Rule 2.2: 逻辑与一致性守门人
    """
    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.model.DEEPSEEK_MODEL,
            openai_api_key=Config.model.DEEPSEEK_API_KEY,
            openai_api_base=Config.model.DEEPSEEK_API_BASE,
            temperature=Config.model.DEEPSEEK_REVIEWER_TEMP
        )

    async def review_draft(self, state: NGEState, draft: str) -> Dict[str, Any]:
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

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极其敏锐的小说评论家和逻辑学家。你的任务是发现草稿中的任何微小漏洞。\n"
                "【反重力规则警告】\n"
                "- 严禁人物性格突变 (OOC)\n"
                "- 严禁逻辑硬伤\n"
                "- 严禁修改已确定的世界观\n"
                f"当前人物灵魂锚定：\n{character_rules}\n"
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
        
        response = await self.llm.ainvoke(prompt.format(
            draft=draft, 
            summary=last_summary
        ))
        
        content_str = strip_think_tags(response.content)
        result = extract_json_from_text(content_str)
        
        if not result:
            return {
                "passed": False, 
                "score": 0.0, 
                "feedback": "审核系统解析失败，请检查模型输出格式", 
                "logical_errors": ["Parse Error"]
            }
            
        return result

    async def evolve_characters(self, state: NGEState, draft: str) -> Dict[str, Any]:
        """
        CharacterEvolver: 分析该章节发生的事件是否改变了人物的心境或关系。
        遵循 Rule 3.2: 人物立体与成长
        """
        char_list = ", ".join(state.characters.keys())
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个心理分析专家和人物塑造师。\n"
                f"当前活跃角色：{char_list}\n"
                "请分析本章事件对这些角色的心境、性格、关系的影响。\n"
                "输出格式必须为 JSON。"
            )),
            ("human", (
                "角色初始状态：{char_states}\n"
                "本章内容：\n{draft}\n\n"
                "请生成每个角色的更新状态，必须包含字段：new_mood, evolution_summary, relationship_changes"
            ))
        ])
        
        char_states = json.dumps({n: {"mood": c.current_mood, "personality": c.personality_traits} for n, c in state.characters.items()})
        
        response = await self.llm.ainvoke(prompt.format(
            draft=draft,
            char_states=char_states
        ))
        
        content_str = strip_think_tags(response.content)
        return extract_json_from_text(content_str) or {}
