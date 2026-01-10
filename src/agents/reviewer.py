import os
import re
import json
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState, CharacterState
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, validate_character_consistency, normalize_llm_content
from dotenv import load_dotenv

load_dotenv()

class ReviewerAgent:
    """
    Reviewer Agent (Gemini): 负责逻辑审查、人物OOC检查及状态演化。
    作为【王】进行最后的裁决。
    遵循 Rule 1.1 / 2.2: 逻辑与一致性守门人
    """
    def __init__(self):
        if Config.model.GEMINI_MODEL == "mock":
            from ..utils import MockChatModel
            self.llm = MockChatModel(responses=[
                # Response for review_draft
                json.dumps({"passed": True, "score": 0.9, "feedback": "Good job", "logical_errors": []}),
                # Response for evolve_characters (if called, but EvolverAgent seems to be used instead in graph)
                json.dumps({"new_mood": "Happy", "evolution_summary": "Evolved", "new_skills": [], "asset_changes": {}, "acquired_items": [], "lost_items": [], "relationship_changes": [], "summary": "Ch summary"})
            ])
        else:
            self.llm = ChatGoogleGenerativeAI(
                model=Config.model.GEMINI_MODEL,
                google_api_key=Config.model.GEMINI_API_KEY,
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
                "当前人物灵魂锚定：\n{character_rules}\n"
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
            character_rules=character_rules
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
                "请分析并返回 JSON，包含每个角色的更新状态。字段要求：\n"
                "- new_mood: 变化后的心情描述\n"
                "- evolution_summary: 本章成长/变化摘要\n"
                "- new_skills: 本章习得的新技能列表 (若无则为空列表)\n"
                "- asset_changes: 资产变动 (如 {'灵石': -10}) (若无则为空字典)\n"
                "- acquired_items: 本章获得的关键物品名称列表 (若无则为空列表)\n"
                "- lost_items: 本章失去/消耗的关键物品名称列表 (若无则为空列表)\n"
                "- relationship_changes: 关系变动列表，每项需包含 {'target': '对方名', 'change_type': '类型', 'value': 0.1} (若无则为空列表)\n"
                "- summary: 整个章节的文字总结 (String)"
            ))
        ])
        
        char_states = json.dumps({
            n: {
                "mood": c.current_mood, 
                "personality": c.personality_traits,
                "skills": c.skills,
                "assets": c.assets,
                "inventory": [i.name for i in c.inventory]
            } for n, c in state.characters.items()
        }, ensure_ascii=False)
        
        messages = prompt.format_messages(
            draft=draft,
            char_states=char_states
        )
        response = await self.llm.ainvoke(messages)
        
        content_str = normalize_llm_content(response.content)
        content_str = strip_think_tags(content_str)
        return extract_json_from_text(content_str) or {}
