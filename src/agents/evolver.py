from ..schemas.state import NGEState, CharacterState
from ..llms import get_llm
from ..utils import normalize_llm_content, extract_json_from_text, strip_think_tags
from ..config import Config
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

class CharacterEvolution(BaseModel):
    """定义了单个人物在一个章节内的状态演化"""
    character_name: str = Field(description="发生变化的角色姓名")
    mood_change: str = Field(description="角色的心情变化，如'从平静变为愤怒'")
    skill_update: List[str] = Field(default_factory=list, description="角色获得或失去的技能")
    relationship_change: Dict[str, str] = Field(default_factory=dict, description="与其他角色关系的变化，格式：{'角色名': '关系描述'}")
    status_change: Optional[Dict[str, Any]] = Field(None, description="角色状态变更，如死亡、受伤等")
    evolution_summary: str = Field(description="描述角色为何以及如何发生这些变化的简短摘要")

class PlotUpdate(BaseModel):
    new_foreshadowing: List[str] = Field(default_factory=list, description="本章埋下的新伏笔")
    resolved_threads: List[str] = Field(default_factory=list, description="本章解决或回收的旧伏笔")

class EvolutionResult(BaseModel):
    """定义了整个章节所有人物的演化结果及剧情推进"""
    evolutions: List[CharacterEvolution]
    story_updates: Optional[PlotUpdate] = None

from .base import BaseAgent
from .constants import PromptTemplates
from langchain_core.prompts import ChatPromptTemplate

class CharacterEvolver(BaseAgent):
    """
    负责在章节结束后，根据内容分析人物状态的演化及剧情推进。
    遵循 Antigravity Rule 3.2 (人物立体与成长) 及 Rule 3.4 (伏笔回收).
    """
    def __init__(self, temperature: Optional[float] = None):
        super().__init__(
            model_name="deepseek", # 使用逻辑模型进行分析
            temperature=temperature,
            mock_responses=[
                json.dumps({
                    "evolutions": [],
                    "story_updates": {"new_foreshadowing": [], "resolved_threads": []}
                })
            ]
        )

    async def process(self, state: NGEState) -> Any:
        """
        BaseAgent required method.
        Delegates to evolve.
        """
        return await self.evolve(state)

    async def evolve(self, state: NGEState) -> EvolutionResult:
        """
        分析章节内容，并返回结构化的人物演化数据及剧情更新。
        """
        chapter_content = state.current_draft
        characters_involved = list(state.characters.keys())
        # 获取当前未解决的伏笔列表，供模型参考
        active_threads = state.memory_context.global_foreshadowing 
        active_threads_str = "\n".join([f"- {t}" for t in active_threads]) if active_threads else "无"

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个专业的小说编辑，擅长分析人物弧光和成长，以及剧情线的收束。\n"
                f"{PromptTemplates.ANTIGRAVITY_WARNING}\n"
                "请仔细阅读以下章节内容，并分析其中主要人物的状态变化以及剧情伏笔的变动。\n"
                "请严格按照 JSON 格式输出。"
            )),
            ("human", (
                "**章节内容:**\n"
                "---\n"
                "{chapter_content}\n"
                "---\n"
                "**涉及人物:** {characters_involved}\n"
                "**当前未解决伏笔:**\n{active_threads_str}\n\n"
                "请根据章节内容：\n"
                "1. 为每一个发生了显著变化的人物（心情、技能、人际关系、状态等）生成演化报告。\n"
                "2. 分析本章是否埋下了新的伏笔？\n"
                "3. 分析本章是否回收/解决了上述'当前未解决伏笔'中的任何一项？\n\n"
                "请严格按照以下 JSON 格式输出：\n"
                "{{\n"
                "    \"evolutions\": [\n"
                "        {{\n"
                "            \"character_name\": \"角色A\",\n"
                "            \"mood_change\": \"...\",\n"
                "            \"skill_update\": [\"...\"],\n"
                "            \"relationship_change\": {{ \"角色B\": \"...\" }},\n"
                "            \"status_change\": {{ \"is_active\": false, \"reason\": \"死亡\" }},\n"
                "            \"evolution_summary\": \"...\"\n"
                "        }}\n"
                "    ],\n"
                "    \"story_updates\": {{\n"
                "        \"new_foreshadowing\": [\"...\"],\n"
                "        \"resolved_threads\": [\"...\"]\n"
                "    }}\n"
                "}}"
            ))
        ])

        messages = prompt.format_messages(
            chapter_content=chapter_content,
            characters_involved=", ".join(characters_involved),
            active_threads_str=active_threads_str
        )
        
        response = await self.llm.ainvoke(messages)
        content = normalize_llm_content(response.content)
        content = strip_think_tags(content)
        data = extract_json_from_text(content)
        
        if not data:
             # Fallback empty result
             return EvolutionResult(evolutions=[], story_updates=PlotUpdate())
             
        return EvolutionResult.model_validate(data)

        
        try:
            response = await self.llm.ainvoke(prompt)
            content = normalize_llm_content(response.content)
            json_data = extract_json_from_text(content)
            if not json_data:
                logger.warning(f"无法从 LLM 响应中提取 JSON，返回空演化结果。响应内容: {content[:200]}...")
                return EvolutionResult(evolutions=[])
            
            return EvolutionResult.model_validate(json_data)
        except Exception as e:
            logger.error(f"人物演化分析失败: {e}", exc_info=True)
            # 返回空结果，避免阻塞流程
            return EvolutionResult(evolutions=[])
