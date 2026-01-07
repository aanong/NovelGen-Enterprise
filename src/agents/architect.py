import os
import re
import json
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from ..schemas.state import PlotPoint, NGEState
from dotenv import load_dotenv

load_dotenv()

class OutlineExpansion(BaseModel):
    expanded_points: List[PlotPoint] = Field(description="详细的大纲列表，精确到场面调度")

class ChapterPlan(BaseModel):
    thinking: str = Field(description="思考过程：本章如何服务主线？如何承接上文？")
    scene_description: str = Field(description="核心场面调度描述")
    key_conflict: str = Field(description="核心冲突点与高潮")
    instruction: str = Field(description="给 Writer Agent 的具体写作指令，包含语气、视角要求")

class ArchitectAgent:
    """
    Architect Agent (Deepseek): 负责剧情逻辑、大纲构建与拆解。
    利用 Deepseek 的推理能力防止剧情崩坏。
    """
    def __init__(self):
        # 使用 Deepseek 模型 (通过 OpenAI 兼容接口)
        self.llm = ChatOpenAI(
            model="deepseek-chat", # 或者 deepseek-reasoner (R1)
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com/v1",
            temperature=0.3
        )
        self.outline_parser = PydanticOutputParser(pydantic_object=OutlineExpansion)
        self.plan_parser = PydanticOutputParser(pydantic_object=ChapterPlan)

    async def expand_outline(self, user_prompt: str, world_view: str) -> List[PlotPoint]:
        """
        根据用户输入的简单大纲，扩充为精细化的大纲。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个严谨的网文主编和架构师。擅长构建逻辑严密、节奏感强的小说大纲。\n"
                "必须遵循以下规则：\n"
                "1. 严禁逻辑漏洞。\n"
                "2. 每个剧情点必须包含明确的冲突和推进作用。\n"
                "3. 世界观限制：{world_view}\n"
                "输出格式必须为 JSON。\n"
                "{format_instructions}"
            )),
            ("human", "请根据以下简述扩充大纲：\n{user_prompt}")
        ])

        chain = prompt | self.llm | self.outline_parser
        result = await chain.ainvoke({
            "world_view": world_view,
            "user_prompt": user_prompt,
            "format_instructions": self.outline_parser.get_format_instructions()
        })
        return result.expanded_points

    async def plan_next_chapter(self, state: NGEState) -> Dict[str, Any]:
        """
        写每一章前，Agent 必须回答：“这一章如何服务于主线？上一章的结尾是什么？”
        """
        if not state.plot_progress or state.current_plot_index >= len(state.plot_progress):
            current_point_info = "剧情自由发展阶段"
        else:
            current_point = state.plot_progress[state.current_plot_index]
            current_point_info = f"标题：{current_point.title}\n描述：{current_point.description}\n关键事件：{', '.join(current_point.key_events)}"

        last_summary = state.memory_context.recent_summaries[-1] if state.memory_context.recent_summaries else "开篇第一章"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个剧情规划专家。任务是为即将撰写的章节制定详细的微型提纲。\n"
                "必须输出 JSON 格式，包含 thinking, scene_description, key_conflict, instruction。\n"
                "{format_instructions}"
            )),
            ("human", (
                f"当前剧情点：\n{current_point_info}\n\n"
                f"上一章总结：{last_summary}\n\n"
                "请规划下一章详情。"
            ))
        ])
        
        input_data = {
            "format_instructions": self.plan_parser.get_format_instructions()
        }
        
        prompt_value = prompt.format_prompt(**input_data)
        try:
            response = await self.llm.ainvoke(prompt_value.to_messages())
            content_str = response.content
            
            # Filter <think> tags (Rule 4.1)
            content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()
            
            # Robust JSON extraction
            json_match = re.search(r'(\{.*\})', content_str, re.DOTALL)
            if json_match:
                plan_json = json.loads(json_match.group(1))
                return {
                    "scene": plan_json.get("scene_description") or plan_json.get("scene", "未知场景"),
                    "conflict": plan_json.get("key_conflict") or plan_json.get("conflict", "未知冲突"),
                    "instruction": plan_json.get("instruction", f"请继续写下一章。基于剧情点：{current_point_info}")
                }
            
            raise ValueError(f"Could not find JSON in response: {content_str}")

        except Exception as e:
            print(f"Plan Error: {e}")
            # Fallback
            return {
                "scene": "未知场景",
                "conflict": "未知冲突",
                "instruction": f"请继续写下一章。基于剧情点：{current_point_info}"
            }
