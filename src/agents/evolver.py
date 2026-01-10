from ..schemas.state import NGEState, CharacterState
from ..llms import get_llm
from ..utils import normalize_llm_content, extract_json_from_text
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class CharacterEvolution(BaseModel):
    """定义了单个人物在一个章节内的状态演化"""
    character_name: str = Field(description="发生变化的角色姓名")
    mood_change: str = Field(description="角色的心情变化，如'从平静变为愤怒'")
    skill_update: List[str] = Field(default_factory=list, description="角色获得或失去的技能")
    relationship_change: Dict[str, str] = Field(default_factory=dict, description="与其他角色关系的变化，格式：{'角色名': '关系描述'}")
    evolution_summary: str = Field(description="描述角色为何以及如何发生这些变化的简短摘要")

class EvolutionResult(BaseModel):
    """定义了整个章节所有人物的演化结果"""
    evolutions: List[CharacterEvolution]

class CharacterEvolver:
    """
    负责在章节结束后，根据内容分析人物状态的演化。
    遵循 Antigravity Rule 3.2 (人物立体与成长)。
    """
    def __init__(self):
        self.llm = get_llm(model_name="deepseek") # 使用逻辑模型进行分析

    async def evolve(self, state: NGEState) -> EvolutionResult:
        """
        分析章节内容，并返回结构化的人物演化数据。
        """
        chapter_content = state.current_draft
        characters_involved = list(state.characters.keys())

        prompt = f"""
        你是一个专业的小说编辑，擅长分析人物弧光和成长。
        请仔细阅读以下章节内容，并分析其中主要人物的状态变化。

        **章节内容:**
        ---
        {chapter_content}
        ---

        **涉及人物:** {', '.join(characters_involved)}

        请根据章节内容，为每一个发生了显著变化的人物（心情、技能、人际关系等）生成一份演化报告。
        请严格按照以下 JSON 格式输出，如果某个角色没有变化，则不要在输出中包含该角色：
        
        {{
            "evolutions": [
                {{
                    "character_name": "角色A",
                    "mood_change": "因目睹挚友牺牲，心情从'坚定'变为'悲痛欲绝'",
                    "skill_update": ["领悟'血之哀伤'剑技"],
                    "relationship_change": {{
                        "角色B": "因共同的敌人，关系从'中立'变为'盟友'"
                    }},
                    "evolution_summary": "角色A在本章经历了重大情感创伤，激发了潜力，并与角色B建立了新的联盟。"
                }}
            ]
        }}
        """
        
        response = await self.llm.ainvoke(prompt)
        content = normalize_llm_content(response.content)
        json_data = extract_json_from_text(content)
        if not json_data:
            # Return empty result if parsing fails
            return EvolutionResult(evolutions=[])
            
        return EvolutionResult.model_validate(json_data)
