"""
章节摘要生成器
使用 LLM 生成高质量的结构化摘要
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from ..schemas.state import NGEState
from ..config import Config
from ..utils import normalize_llm_content, extract_json_from_text, strip_think_tags
from .base import BaseAgent
import json
import logging

logger = logging.getLogger(__name__)


class ChapterSummary(BaseModel):
    """结构化章节摘要"""
    core_events: str = Field(description="核心事件（1-2句话）")
    character_changes: str = Field(description="关键人物状态变化")
    new_foreshadowing: list = Field(default_factory=list, description="新出现的伏笔或线索")
    plot_advancement: str = Field(description="与主线的关联和推进")
    key_dialogue: Optional[str] = Field(None, description="重要对话或行动（可选）")


class ChapterSummarizer(BaseAgent):
    """
    章节摘要生成器
    使用 LLM 生成高质量的结构化摘要，替代简单的文本截取
    """
    
    def __init__(self, temperature: Optional[float] = None):
        """
        初始化摘要生成器
        
        Args:
            temperature: 温度参数，默认使用配置值
        """
        super().__init__(
            model_name="gemini",
            temperature=temperature or Config.model.GEMINI_TEMPERATURE
        )
    
    async def generate_summary(
        self, 
        content: str, 
        state: Optional[NGEState] = None,
        max_content_length: int = 3000
    ) -> Dict[str, Any]:
        """
        生成结构化摘要
        
        Args:
            content: 章节内容
            state: 当前状态（可选，用于提供上下文）
            max_content_length: 用于摘要的内容最大长度
            
        Returns:
            包含摘要信息的字典
        """
        # 限制内容长度以避免 token 浪费
        content_for_summary = content[:max_content_length]
        if len(content) > max_content_length:
            content_for_summary += "\n[内容已截断...]"
        
        # 构建上下文信息
        context_info = ""
        if state:
            # 添加当前章节信息
            if state.current_plot_index < len(state.plot_progress):
                plot_point = state.plot_progress[state.current_plot_index]
                context_info = f"当前剧情点：{plot_point.title}\n描述：{plot_point.description}\n"
            
            # 添加涉及的主要人物
            if state.characters:
                main_chars = list(state.characters.keys())[:5]  # 限制数量
                context_info += f"主要人物：{', '.join(main_chars)}\n"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个专业的小说编辑，擅长提炼章节核心内容。\n"
                "请为以下章节生成结构化摘要，必须包含：\n"
                "1. 核心事件（1-2句话概括本章最重要的情节）\n"
                "2. 关键人物状态变化（谁的状态、心情、能力发生了变化）\n"
                "3. 新出现的伏笔或线索（本章埋下的新悬念）\n"
                "4. 与主线的关联（本章如何推进主线剧情）\n"
                "5. 重要对话或行动（可选，如果有特别重要的）\n\n"
                "输出格式必须为 JSON。\n"
                "{format_instructions}"
            )),
            ("human", (
                "{context_info}"
                "章节内容：\n"
                "{content}\n\n"
                "请生成结构化摘要。"
            ))
        ])
        
        try:
            from langchain_core.output_parsers import PydanticOutputParser
            parser = PydanticOutputParser(pydantic_object=ChapterSummary)
            
            messages = prompt.format_messages(
                context_info=context_info,
                content=content_for_summary,
                format_instructions=parser.get_format_instructions()
            )
            
            response = await self.llm.ainvoke(messages)
            content_str = normalize_llm_content(response.content)
            content_str = strip_think_tags(content_str)
            
            # 尝试解析 JSON
            summary_json = extract_json_from_text(content_str)
            if summary_json:
                return {
                    "summary": self._format_summary(summary_json),
                    "structured": summary_json,
                    "core_events": summary_json.get("core_events", ""),
                    "character_changes": summary_json.get("character_changes", ""),
                    "new_foreshadowing": summary_json.get("new_foreshadowing", []),
                    "plot_advancement": summary_json.get("plot_advancement", "")
                }
            
            # Fallback: 如果解析失败，使用 LLM 直接生成文本摘要
            logger.warning("JSON 解析失败，使用文本摘要模式")
            return await self._generate_text_summary(content_for_summary, context_info)
            
        except Exception as e:
            logger.error(f"摘要生成失败: {e}", exc_info=True)
            # 最终回退：简单截取
            return {
                "summary": content[:200] + "...",
                "structured": None,
                "core_events": "",
                "character_changes": "",
                "new_foreshadowing": [],
                "plot_advancement": ""
            }
    
    async def _generate_text_summary(self, content: str, context_info: str) -> Dict[str, Any]:
        """生成文本格式摘要（回退方案）"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个专业的小说编辑，请为章节生成简洁的摘要（100-200字）。"),
            ("human", f"{context_info}\n章节内容：\n{content[:2000]}\n\n请生成摘要。")
        ])
        
        response = await self.llm.ainvoke(prompt.format_messages(
            context_info=context_info,
            content=content[:2000]
        ))
        summary_text = normalize_llm_content(response.content)
        summary_text = strip_think_tags(summary_text)
        
        return {
            "summary": summary_text[:200],
            "structured": None,
            "core_events": summary_text,
            "character_changes": "",
            "new_foreshadowing": [],
            "plot_advancement": ""
        }
    
    def _format_summary(self, summary_json: Dict[str, Any]) -> str:
        """格式化摘要为文本"""
        parts = []
        
        if summary_json.get("core_events"):
            parts.append(f"核心事件：{summary_json['core_events']}")
        
        if summary_json.get("character_changes"):
            parts.append(f"人物变化：{summary_json['character_changes']}")
        
        if summary_json.get("plot_advancement"):
            parts.append(f"剧情推进：{summary_json['plot_advancement']}")
        
        if summary_json.get("new_foreshadowing"):
            foreshadowing = ", ".join(summary_json['new_foreshadowing'])
            parts.append(f"新伏笔：{foreshadowing}")
        
        return "\n".join(parts) if parts else "无摘要"
