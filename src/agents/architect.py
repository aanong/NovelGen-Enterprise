import os
import re
import json
from typing import List, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from ..schemas.state import PlotPoint, NGEState, ForeshadowingSchema, ForeshadowingStatus
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, normalize_llm_content
from ..db.vector_store import VectorStore
from .base import BaseAgent
from dotenv import load_dotenv

load_dotenv()


class ForeshadowingStrategy(BaseModel):
    """伏笔处理策略"""
    advance: List[str] = Field(default_factory=list, description="本章应推进的伏笔")
    resolve: List[str] = Field(default_factory=list, description="本章应回收的伏笔")
    plant: List[str] = Field(default_factory=list, description="本章应埋设的新伏笔")
    reasoning: str = Field(default="", description="策略理由")

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

class ArchitectAgent(BaseAgent):
    """
    Architect Agent (Gemini): 负责剧情逻辑、大纲构建与拆解。
    利用 Gemini 的逻辑推演能力，确保世界观一致性。
    遵循 Rule 1.1: Gemini 为王（底层逻辑最终解释权）
    """
    def __init__(self, temperature: Optional[float] = None):
        super().__init__(
            model_name="gemini",
            temperature=temperature or Config.model.GEMINI_TEMPERATURE,
            mock_responses=[
                # Response for generate_chapter_outlines
                json.dumps({"chapters": [
                    {"chapter_number": 1, "title": "Ch1", "scene_description": "Scene 1", "key_conflict": "Conflict 1", "foreshadowing": []},
                    {"chapter_number": 2, "title": "Ch2", "scene_description": "Scene 2", "key_conflict": "Conflict 2", "foreshadowing": []},
                    {"chapter_number": 3, "title": "Ch3", "scene_description": "Scene 3", "key_conflict": "Conflict 3", "foreshadowing": []}
                ]}),
                # Response for plan_next_chapter (called by Writer/Graph)
                json.dumps({"thinking": "Think", "scene_description": "Scene", "key_conflict": "Conflict", "instruction": "Write"}),
                # More responses if needed
                json.dumps({"thinking": "Think", "scene_description": "Scene", "key_conflict": "Conflict", "instruction": "Write"}),
            ]
        )
        self.outline_parser = PydanticOutputParser(pydantic_object=OutlineExpansion)
        self.plan_parser = PydanticOutputParser(pydantic_object=ChapterPlan)
        self.full_outline_parser = PydanticOutputParser(pydantic_object=FullNovelOutline)
        self.vector_store = VectorStore()

    async def process(self, state: NGEState, **kwargs) -> Dict[str, Any]:
        """
        BaseAgent required method.
        Delegates to plan_next_chapter for the main workflow.
        """
        return await self.plan_next_chapter(state)

    async def generate_chapter_outlines(self, synopsis: str, world_view: str, total_chapters: int = 10) -> List[ChapterOutline]:
        """
        Rule 3.4: 全书大纲预生成
        将核心梗概拆解为具体的分章大纲。
        """
        # 检索参考资料
        references = await self.vector_store.search_references(synopsis, top_k=2)
        ref_context = ""
        if references:
            ref_context = "\n【参考资料】\n"
            for ref in references:
                ref_context += f"- {ref['title']}: {ref['content'][:100]}...\n"

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个网文总策划。任务是将一个简短的故事梗概拆解为详细的分章大纲。\n"
                "【要求】\n"
                "1. 总共生成约 {total_chapters} 章。\n"
                "2. 每一章都要有明确的冲突和推进。\n"
                "3. 严格遵守世界观设定：{world_view}\n"
                "4. 确保剧情节奏张弛有度（起承转合）。\n"
                "{ref_context}\n"
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
                "ref_context": ref_context,
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
        # 检索参考资料
        references = await self.vector_store.search_references(user_prompt, top_k=2)
        ref_context = ""
        if references:
            ref_context = "\n【参考资料】\n"
            for ref in references:
                ref_context += f"- {ref['title']}: {ref['content'][:100]}...\n"

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个严谨的网文主编和架构师。擅长构建逻辑严密、节奏感强的小说大纲。\n"
                "必须遵循以下规则：\n"
                "1. 严禁逻辑漏洞。\n"
                "2. 每个剧情点必须包含明确的冲突和推进作用。\n"
                "3. 世界观限制：{world_view}\n"
                "{ref_context}\n"
                "输出格式必须为 JSON。\n"
                "{format_instructions}"
            )),
            ("human", "请根据以下简述扩充大纲：\n{user_prompt}")
        ])

        chain = prompt | self.llm | self.outline_parser
        result = await chain.ainvoke({
            "world_view": world_view,
            "user_prompt": user_prompt,
            "ref_context": ref_context,
            "format_instructions": self.outline_parser.get_format_instructions()
        })
        return result.expanded_points

    async def check_coherence(self, state: NGEState, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查规划与前文的连贯性。
        """
        recent_summaries = getattr(getattr(state, "memory_context", None), "recent_summaries", [])
        last_summary = "\n".join([f"- {s}" for s in recent_summaries[-3:]]) if recent_summaries else "无前文"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个极其严谨的小说逻辑审查员。你的任务是检查【拟定的下一章规划】与【前文内容】是否存在逻辑矛盾。\n"
                "重点检查：\n"
                "1. 时间线是否冲突？\n"
                "2. 角色位置、状态是否连续？\n"
                "3. 核心设定是否被违反？\n"
                "输出格式：JSON，包含 coherent (bool) 和 issues (list of str)。"
            )),
            ("human", (
                "【前文摘要回顾】\n{last_summary}\n\n"
                "【拟定的规划】\n"
                "场景：{scene}\n"
                "冲突：{conflict}\n"
                "指令：{instruction}\n\n"
                "请评估其连贯性。"
            ))
        ])
        
        try:
            messages = prompt.format_messages(
                last_summary=last_summary,
                scene=plan_data.get("scene", ""),
                conflict=plan_data.get("conflict", ""),
                instruction=plan_data.get("instruction", "")
            )
            response = await self.llm.ainvoke(messages)
            content = strip_think_tags(normalize_llm_content(response.content))
            return extract_json_from_text(content)
        except Exception as e:
            print(f"Coherence Check Error: {e}")
            return {"coherent": True, "issues": []}

    async def plan_next_chapter(self, state: NGEState) -> Dict[str, Any]:
        """
        写每一章前，Agent 必须回答："这一章如何服务于主线？上一章的结尾是什么？"
        遵循 Rule 1.1: Gemini 为王，不得自行修改设定
        
        增强功能：
        1. 检查即将到期的伏笔
        2. 强制在规划中包含过期伏笔的处理指令
        3. 生成伏笔推进策略
        """
        current_chapter = state.current_plot_index + 1
        
        if not state.plot_progress or state.current_plot_index >= len(state.plot_progress):
            current_point_info = "剧情自由发展阶段"
        else:
            current_point = state.plot_progress[state.current_plot_index]
            key_events = getattr(current_point, "key_events", []) or []
            current_point_info = (
                f"标题：{getattr(current_point, 'title', '')}\n"
                f"描述：{getattr(current_point, 'description', '')}\n"
                f"关键事件：{', '.join(key_events)}"
            )

        recent_summaries = getattr(getattr(state, "memory_context", None), "recent_summaries", None) or []
        if recent_summaries:
            last_summary = "\n".join([f"- {s}" for s in recent_summaries])
        else:
            last_summary = "开篇第一章"

        characters = getattr(state, "characters", None) or {}
        if characters:
            char_info = "\n".join([
                (
                    f"- {name}: "
                    f"技能={', '.join(getattr(char, 'skills', []) or [])}, "
                    f"资产={json.dumps(getattr(char, 'assets', {}) or {}, ensure_ascii=False)}, "
                    f"物品={', '.join([getattr(i, 'name', str(i)) for i in (getattr(char, 'inventory', []) or [])])}"
                )
                for name, char in characters.items()
            ])
        else:
            char_info = "无"

        # ========== 增强：伏笔回收时机规划 ==========
        # 获取结构化伏笔（优先）和传统伏笔列表
        foreshadowing_analysis = self._analyze_foreshadowing_timing(state, current_chapter)
        threads_str = foreshadowing_analysis["threads_str"]
        foreshadowing_urgency = foreshadowing_analysis["urgency_prompt"]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个剧情规划专家。任务是为即将撰写的章节制定详细的微型提纲。\n"
                "必须输出 JSON 格式，包含 thinking, scene_description, key_conflict, instruction, foreshadowing_strategy。\n\n"
                "【伏笔管理要求】：\n"
                "1. 推进策略：明确指出本章应推进哪些已有的存量伏笔。\n"
                "2. 回收策略：如果剧情时机成熟，明确指出应在本章回收/揭晓的伏笔。\n"
                "3. 埋线策略：根据主线需要，本章是否需要埋下新的伏笔或悬念。\n\n"
                "【伏笔紧急性说明】：\n"
                "{foreshadowing_urgency}\n\n"
                "【foreshadowing_strategy 格式】：\n"
                "{{\n"
                '  "advance": ["伏笔A的推进方式", "伏笔B的推进方式"],\n'
                '  "resolve": ["应回收的伏笔及回收方式"],\n'
                '  "plant": ["新埋设的伏笔描述"],\n'
                '  "reasoning": "策略理由"\n'
                "}}\n\n"
                "{format_instructions}"
            )),
            ("human", (
                "【前文摘要】\n{last_summary}\n\n"
                "【人物信息】\n{char_info}\n\n"
                "【未回收伏笔/悬念】\n{threads_str}\n\n"
                "【当前剧情点】\n{current_point_info}\n\n"
                "请规划下一章详情。在 instruction 中显式包含对伏笔处理的具体写作指令。"
            ))
        ])

        messages = prompt.format_messages(
            last_summary=last_summary,
            char_info=char_info,
            threads_str=threads_str,
            current_point_info=current_point_info,
            foreshadowing_urgency=foreshadowing_urgency,
            format_instructions=self.plan_parser.get_format_instructions()
        )

        try:
            response = await self.llm.ainvoke(messages)
            content_str = strip_think_tags(normalize_llm_content(response.content))
            plan_json = extract_json_from_text(content_str)

            if isinstance(plan_json, dict) and plan_json:
                # 提取伏笔策略
                foreshadowing_strategy = plan_json.get("foreshadowing_strategy", {})
                
                # 构建增强的指令，包含伏笔处理要求
                instruction = plan_json.get("instruction") or f"请继续写下一章。基于剧情点：{current_point_info}"
                
                # 如果有过期伏笔，强制添加回收指令
                if foreshadowing_analysis["overdue"]:
                    overdue_instruction = self._build_overdue_instruction(foreshadowing_analysis["overdue"])
                    instruction = f"{instruction}\n\n{overdue_instruction}"
                
                return {
                    "scene": plan_json.get("scene_description") or plan_json.get("scene") or "未知场景",
                    "conflict": plan_json.get("key_conflict") or plan_json.get("conflict") or "未知冲突",
                    "instruction": instruction,
                    "foreshadowing_strategy": foreshadowing_strategy,
                }

            raise ValueError(f"Could not find JSON in response: {content_str}")

        except Exception as e:
            print(f"Plan Error: {e}")
            return {
                "scene": "未知场景",
                "conflict": "未知冲突",
                "instruction": f"请继续写下一章。基于剧情点：{current_point_info}",
                "foreshadowing_strategy": {},
            }
    
    def _analyze_foreshadowing_timing(
        self, 
        state: NGEState, 
        current_chapter: int
    ) -> Dict[str, Any]:
        """
        分析伏笔回收时机
        
        Args:
            state: 当前状态
            current_chapter: 当前章节号
            
        Returns:
            包含伏笔分析信息的字典
        """
        overdue = []  # 过期伏笔
        due_soon = []  # 即将到期的伏笔
        active = []  # 所有活跃伏笔
        
        # 优先使用结构化伏笔
        if hasattr(state.memory_context, 'structured_foreshadowing') and state.memory_context.structured_foreshadowing:
            for f in state.memory_context.structured_foreshadowing:
                if f.status in [ForeshadowingStatus.PLANTED, ForeshadowingStatus.ADVANCED]:
                    active.append(f)
                    
                    if f.expected_resolve_chapter:
                        if f.expected_resolve_chapter < current_chapter:
                            overdue.append(f)
                        elif f.expected_resolve_chapter <= current_chapter + 3:
                            due_soon.append(f)
            
            # 构建伏笔字符串
            threads_parts = []
            for f in active:
                urgency = ""
                if f in overdue:
                    urgency = "【过期！】"
                elif f in due_soon:
                    urgency = f"【第{f.expected_resolve_chapter}章到期】"
                
                importance_star = "★" * min(f.importance, 5)
                threads_parts.append(
                    f"- {urgency}{f.content}（重要性:{importance_star}，埋于第{f.created_at_chapter}章）"
                )
            
            threads_str = "\n".join(threads_parts) if threads_parts else "无"
        else:
            # 回退到传统伏笔列表
            traditional = getattr(state.memory_context, "global_foreshadowing", []) or []
            threads_str = "\n".join([f"- {t}" for t in traditional]) if traditional else "无"
        
        # 构建紧急性提示
        urgency_parts = []
        if overdue:
            urgency_parts.append(
                f"⚠️ 严重警告：有 {len(overdue)} 个伏笔已超过预期回收时间，必须尽快处理！"
            )
            for f in overdue[:3]:
                delay = current_chapter - f.expected_resolve_chapter
                urgency_parts.append(
                    f"  - \"{f.content[:30]}...\"（已延迟 {delay} 章，原定第{f.expected_resolve_chapter}章回收）"
                )
        
        if due_soon and not overdue:
            urgency_parts.append(
                f"📌 提醒：有 {len(due_soon)} 个伏笔即将到期，请考虑推进或回收。"
            )
            for f in due_soon[:2]:
                chapters_left = f.expected_resolve_chapter - current_chapter
                urgency_parts.append(
                    f"  - \"{f.content[:30]}...\"（还剩 {chapters_left} 章）"
                )
        
        if not urgency_parts:
            urgency_parts.append("当前无紧急需要处理的伏笔。可根据剧情需要自由推进或埋设新伏笔。")
        
        return {
            "threads_str": threads_str,
            "urgency_prompt": "\n".join(urgency_parts),
            "overdue": overdue,
            "due_soon": due_soon,
            "active": active
        }
    
    def _build_overdue_instruction(self, overdue_foreshadowings: List[ForeshadowingSchema]) -> str:
        """
        构建过期伏笔的强制回收指令
        
        Args:
            overdue_foreshadowings: 过期伏笔列表
            
        Returns:
            强制回收指令文本
        """
        lines = ["【过期伏笔强制处理指令】"]
        lines.append("以下伏笔已超过预期回收时间，本章必须进行处理（推进或回收）：")
        
        for i, f in enumerate(overdue_foreshadowings[:3], 1):
            lines.append(f"{i}. {f.content}")
            if f.resolve_condition:
                lines.append(f"   回收条件：{f.resolve_condition}")
            if f.resolve_strategy:
                lines.append(f"   建议策略：{f.resolve_strategy}")
        
        lines.append("\n请在写作时确保对上述伏笔有明确的推进或回收。")
        
        return "\n".join(lines)
