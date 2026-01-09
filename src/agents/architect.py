import os
import re
import json
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from ..schemas.state import PlotPoint, NGEState
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text
from dotenv import load_dotenv

load_dotenv()

class OutlineExpansion(BaseModel):
    expanded_points: List[PlotPoint] = Field(description="详细的大纲列表，精确到场面调度")

class ChapterPlan(BaseModel):
    thinking: str = Field(description="思考过程：本章如何服务主线？如何承接上文？")
    scene_description: str = Field(description="核心场面调度描述")
    key_conflict: str = Field(description="核心冲突点与高潮")
    instruction: str = Field(description="给 Writer Agent 的具体写作指令，包含语气、视角要求")

class ChapterOutline(BaseModel):
    chapter_number: int = Field(description="章节序号")
    title: str = Field(description="章节标题")
    scene_description: str = Field(description="核心场面调度描述")
    key_conflict: str = Field(description="核心冲突点与高潮")
    foreshadowing: List[str] = Field(default_factory=list, description="本章埋下的伏笔")

class FullNovelOutline(BaseModel):
    chapters: List[ChapterOutline] = Field(description="全书分章大纲列表")

class ArchitectAgent:
    """
    Architect Agent (Gemini): 负责剧情逻辑、大纲构建与拆解。
    利用 Gemini 的逻辑推演能力，确保世界观一致性。
    遵循 Rule 1.1: Gemini 为王（底层逻辑最终解释权）
    """
    def __init__(self):
        # 使用配置文件中的设置
        self.llm = ChatGoogleGenerativeAI(
            model=Config.model.GEMINI_MODEL,
            google_api_key=Config.model.GEMINI_API_KEY,
            temperature=Config.model.DEEPSEEK_ARCHITECT_TEMP
        )
        self.outline_parser = PydanticOutputParser(pydantic_object=OutlineExpansion)
        self.plan_parser = PydanticOutputParser(pydantic_object=ChapterPlan)
        self.full_outline_parser = PydanticOutputParser(pydantic_object=FullNovelOutline)

    async def generate_chapter_outlines(self, synopsis: str, world_view: str, total_chapters: int = 10) -> List[ChapterOutline]:
        """
        Rule 3.4: 全书大纲预生成
        将核心梗概拆解为具体的分章大纲。
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个网文总策划。任务是将一个简短的故事梗概拆解为详细的分章大纲。\n"
                "【要求】\n"
                "1. 总共生成约 {total_chapters} 章。\n"
                "2. 每一章都要有明确的冲突和推进。\n"
                "3. 严格遵守世界观设定：{world_view}\n"
                "4. 确保剧情节奏张弛有度（起承转合）。\n"
                "输出格式必须为 JSON。\n"
                "{format_instructions}"
            )),
            ("human", "故事梗概：\n{synopsis}")
        ])

        chain = prompt | self.llm | self.full_outline_parser
        try:
            result = await chain.ainvoke({
                "world_view": world_view,
                "synopsis": synopsis,
                "total_chapters": total_chapters,
                "format_instructions": self.full_outline_parser.get_format_instructions()
            })
            return result.chapters
        except Exception as e:
            print(f"Outline Generation Error: {e}")
            return []

    async def refine_outline(self, current_outlines: List[Dict[str, Any]], instruction: str, start_chapter: int, world_view: str) -> List[ChapterOutline]:
        """
        调整现有大纲：从 start_chapter 开始，根据 instruction 重新规划后续章节。
        """
        # 提取前文摘要（start_chapter 之前的内容）
        context_summary = "\n".join([
            f"第 {o['chapter_number']} 章: {o['scene_description']}" 
            for o in current_outlines if o['chapter_number'] < start_chapter
        ])
        
        remaining_chapters = len(current_outlines) - (start_chapter - 1)
        if remaining_chapters < 1:
            remaining_chapters = 5 # 默认续写 5 章
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个网文主编。任务是根据修改意见，重新规划小说后续的大纲。\n"
                "【前情提要】\n{context_summary}\n\n"
                "【修改要求】\n{instruction}\n\n"
                "【世界观】\n{world_view}\n\n"
                "请从第 {start_chapter} 章开始，重新生成约 {remaining_chapters} 章的大纲。\n"
                "输出格式必须为 JSON。\n"
                "{format_instructions}"
            )),
            ("human", "请开始重新规划。")
        ])
        
        chain = prompt | self.llm | self.full_outline_parser
        try:
            result = await chain.ainvoke({
                "context_summary": context_summary,
                "instruction": instruction,
                "world_view": world_view,
                "start_chapter": start_chapter,
                "remaining_chapters": remaining_chapters,
                "format_instructions": self.full_outline_parser.get_format_instructions()
            })
            # 修正章节号，确保连续
            for i, ch in enumerate(result.chapters):
                ch.chapter_number = start_chapter + i
            return result.chapters
        except Exception as e:
            print(f"Outline Refinement Error: {e}")
            return []

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
        写每一章前，Agent 必须回答："这一章如何服务于主线？上一章的结尾是什么？"
        遵循 Rule 1.1: Gemini 为王，不得自行修改设定
        """
        if not state.plot_progress or state.current_plot_index >= len(state.plot_progress):
            current_point_info = "剧情自由发展阶段"
        else:
            current_point = state.plot_progress[state.current_plot_index]
            current_point_info = f"标题：{current_point.title}\n描述：{current_point.description}\n关键事件：{', '.join(current_point.key_events)}"

        last_summary = state.memory_context.recent_summaries[-1] if state.memory_context.recent_summaries else "开篇第一章"
        
        char_info = "\n".join([
            f"- {n}: 技能={', '.join(c.skills)}, 资产={json.dumps(c.assets, ensure_ascii=False)}, 物品={', '.join([i.name for i in c.inventory])}"
            for n, c in state.characters.items()
        ])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个剧情规划专家。任务是为即将撰写的章节制定详细的微型提纲。\n"
                "【反重力规则警告】\n"
                "- Rule 1.1: 严禁修改世界观设定，只能根据设定进行演绎\n"
                "- Rule 2.2: 严禁自发导致人物性格突变或降智\n"
                "必须输出 JSON 格式，包含 thinking, scene_description, key_conflict, instruction。\n"
                "{format_instructions}"
            )),
            ("human", (
                "当前活跃角色状态：\n{char_info}\n\n"
                "当前剧情点：\n{current_point_info}\n\n"
                "上一章总结：{last_summary}\n\n"
                "请规划下一章详情。"
            ))
        ])
        
        input_data = {
            "char_info": char_info,
            "current_point_info": current_point_info,
            "last_summary": last_summary,
            "format_instructions": self.plan_parser.get_format_instructions()
        }
        
        prompt_value = prompt.format_prompt(**input_data)
        try:
            response = await self.llm.ainvoke(prompt_value.to_messages())
            content_str = response.content
            
            # Rule 4.1: 使用工具函数过滤 <think> 标签
            content_str = strip_think_tags(content_str)
            
            # 使用工具函数提取 JSON
            plan_json = extract_json_from_text(content_str)
            
            if plan_json:
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
