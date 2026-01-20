"""
RhythmAnalyzer Agent 模块
负责剧情节奏分析与控制
防止连续多章高潮或低谷，保持张弛有度
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..schemas.state import NGEState
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, normalize_llm_content
from .base import BaseAgent
from ..core.registry import register_agent

@register_agent("rhythm_analyzer")
class RhythmAnalyzer(BaseAgent):
    """
    RhythmAnalyzer Agent: 负责剧情节奏分析与控制
    
    职责：
    1. 分析近 N 章的节奏曲线（紧张/舒缓）
    2. 建议下一章的节奏走向
    3. 防止连续多章高潮或低谷
    4. 生成节奏控制指令供 Writer 使用
    """
    
    # 节奏类型常量
    RHYTHM_TYPES = {
        "climax": "高潮",
        "rising": "上升",
        "falling": "下降",
        "calm": "平静",
        "transition": "过渡"
    }
    
    # 节奏模式警告阈值
    CONSECUTIVE_HIGH_THRESHOLD = 3  # 连续高强度章节阈值
    CONSECUTIVE_LOW_THRESHOLD = 4   # 连续低强度章节阈值
    HIGH_INTENSITY_THRESHOLD = 7    # 高强度阈值
    LOW_INTENSITY_THRESHOLD = 3     # 低强度阈值
    
    def __init__(self, temperature: Optional[float] = None):
        """
        初始化 RhythmAnalyzer Agent
        
        Args:
            temperature: 温度参数，默认使用配置值
        """
        super().__init__(
            model_name="deepseek",  # 使用 DeepSeek 进行逻辑分析
            temperature=temperature or 0.3,  # 较低温度保证分析稳定性
            mock_responses=[
                json.dumps({
                    "curve_analysis": {
                        "recent_chapters": [
                            {"chapter_number": 1, "rhythm_level": {"intensity": 5, "rhythm_type": "rising", "emotional_tone": "期待"}, "key_events": ["出场"], "pacing_notes": "开篇"}
                        ],
                        "overall_trend": "ascending",
                        "pattern_warning": None,
                        "average_intensity": 5.0
                    },
                    "next_chapter_suggestion": {
                        "suggested_intensity": 6,
                        "suggested_type": "rising",
                        "suggested_tone": "紧张",
                        "reasoning": "承接上章节奏，逐步推进",
                        "pacing_instructions": ["增加冲突元素", "保持适度紧张"],
                        "avoid_patterns": ["过度描写"]
                    }
                })
            ]
        )
        self.result_parser = PydanticOutputParser(pydantic_object=RhythmAnalysisResult)
    
    async def process(self, state: NGEState, **kwargs) -> Dict[str, Any]:
        """
        处理节奏分析任务
        
        Args:
            state: 当前状态
            
        Returns:
            节奏分析结果和建议
        """
        return await self.analyze_and_suggest(state)
    
    async def analyze_and_suggest(
        self,
        state: NGEState,
        lookback_chapters: int = 5
    ) -> Dict[str, Any]:
        """
        分析近期章节节奏并给出下一章建议
        
        Args:
            state: 当前状态
            lookback_chapters: 回顾的章节数
            
        Returns:
            包含节奏分析和建议的字典
        """
        # 获取最近章节的摘要
        recent_summaries = state.memory_context.recent_summaries[-lookback_chapters:]
        
        if not recent_summaries:
            # 如果没有历史章节，返回默认建议
            return self._get_opening_suggestion()
        
        # 构建分析提示词
        prompt = self._create_analysis_prompt()
        
        # 准备章节信息
        chapters_info = self._format_chapters_info(recent_summaries, state)
        
        messages = prompt.format_messages(
            chapters_info=chapters_info,
            current_plot_info=self._get_current_plot_info(state),
            format_instructions=self.result_parser.get_format_instructions()
        )
        
        try:
            response = await self.llm.ainvoke(messages)
            content = strip_think_tags(normalize_llm_content(response.content))
            
            # 解析结果
            result_json = extract_json_from_text(content)
            if isinstance(result_json, dict):
                # 进行规则校验和调整
                result = self._validate_and_adjust(result_json, recent_summaries)
                return result
            
            raise ValueError("无法解析节奏分析结果")
            
        except Exception as e:
            print(f"RhythmAnalyzer Error: {e}")
            return self._get_default_suggestion(len(recent_summaries))
    
    def _create_analysis_prompt(self) -> ChatPromptTemplate:
        """创建节奏分析提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个专业的小说节奏分析师。任务是分析近期章节的节奏曲线，并为下一章提供节奏建议。\n\n"
                "【节奏分析原则】\n"
                "1. 节奏强度 1-10：1=极度舒缓（日常/休息），10=极度紧张（生死大战/重大转折）\n"
                "2. 节奏类型：climax(高潮)、rising(上升)、falling(下降)、calm(平静)、transition(过渡)\n"
                "3. 情绪基调：紧张、悲伤、喜悦、愤怒、恐惧、平静、期待、压抑等\n\n"
                "【节奏控制黄金法则】\n"
                "- 避免连续 3 章以上保持高强度（>7），读者会疲劳\n"
                "- 避免连续 4 章以上保持低强度（<3），节奏会拖沓\n"
                "- 高潮之后需要有下降和缓冲\n"
                "- 平静期要为下一个高潮埋伏笔\n"
                "- 大起大落之间要有过渡\n\n"
                "输出必须是严格的 JSON 格式。\n"
                "{format_instructions}"
            )),
            ("human", (
                "【近期章节摘要】\n{chapters_info}\n\n"
                "【当前剧情点】\n{current_plot_info}\n\n"
                "请分析节奏曲线并给出下一章的节奏建议。"
            ))
        ])
    
    def _format_chapters_info(
        self,
        summaries: List[str],
        state: NGEState
    ) -> str:
        """格式化章节信息"""
        current_chapter = state.current_plot_index + 1
        start_chapter = current_chapter - len(summaries)
        
        lines = []
        for i, summary in enumerate(summaries):
            chapter_num = start_chapter + i
            lines.append(f"第 {chapter_num} 章：{summary[:200]}...")
        
        return "\n".join(lines)
    
    def _get_current_plot_info(self, state: NGEState) -> str:
        """获取当前剧情点信息"""
        if state.current_plot_index >= len(state.plot_progress):
            return "剧情自由发展阶段"
        
        current_point = state.plot_progress[state.current_plot_index]
        return f"标题：{current_point.title}\n描述：{current_point.description}"
    
    def _validate_and_adjust(
        self,
        result: Dict[str, Any],
        summaries: List[str]
    ) -> Dict[str, Any]:
        """
        验证并调整分析结果
        应用节奏控制规则
        
        Args:
            result: 原始分析结果
            summaries: 章节摘要
            
        Returns:
            调整后的结果
        """
        curve = result.get("curve_analysis", {})
        suggestion = result.get("next_chapter_suggestion", {})
        
        # 提取近期章节的强度
        recent_chapters = curve.get("recent_chapters", [])
        intensities = [ch.get("rhythm_level", {}).get("intensity", 5) for ch in recent_chapters]
        
        # 检查连续高强度
        if self._check_consecutive_pattern(intensities, self.HIGH_INTENSITY_THRESHOLD, ">="):
            consecutive_high = self._count_consecutive(intensities, self.HIGH_INTENSITY_THRESHOLD, ">=")
            if consecutive_high >= self.CONSECUTIVE_HIGH_THRESHOLD:
                # 强制建议降低强度
                curve["pattern_warning"] = f"警告：已连续 {consecutive_high} 章高强度，读者可能疲劳"
                suggestion["suggested_intensity"] = min(suggestion.get("suggested_intensity", 5), 5)
                suggestion["suggested_type"] = "falling"
                suggestion["avoid_patterns"] = suggestion.get("avoid_patterns", []) + ["继续高强度冲突"]
                suggestion["pacing_instructions"] = ["安排舒缓场景", "角色休整或反思", "为下一个高潮蓄力"]
        
        # 检查连续低强度
        if self._check_consecutive_pattern(intensities, self.LOW_INTENSITY_THRESHOLD, "<="):
            consecutive_low = self._count_consecutive(intensities, self.LOW_INTENSITY_THRESHOLD, "<=")
            if consecutive_low >= self.CONSECUTIVE_LOW_THRESHOLD:
                # 强制建议提高强度
                curve["pattern_warning"] = f"警告：已连续 {consecutive_low} 章低强度，节奏拖沓"
                suggestion["suggested_intensity"] = max(suggestion.get("suggested_intensity", 5), 6)
                suggestion["suggested_type"] = "rising"
                suggestion["avoid_patterns"] = suggestion.get("avoid_patterns", []) + ["继续平淡叙事"]
                suggestion["pacing_instructions"] = ["引入冲突或转折", "推进关键剧情", "制造悬念"]
        
        return {
            "curve_analysis": curve,
            "next_chapter_suggestion": suggestion
        }
    
    def _check_consecutive_pattern(
        self,
        intensities: List[int],
        threshold: int,
        operator: str
    ) -> bool:
        """检查是否存在连续模式"""
        if not intensities:
            return False
        
        # 从末尾开始检查
        for intensity in reversed(intensities):
            if operator == ">=" and intensity < threshold:
                return False
            if operator == "<=" and intensity > threshold:
                return False
        return True
    
    def _count_consecutive(
        self,
        intensities: List[int],
        threshold: int,
        operator: str
    ) -> int:
        """计算连续满足条件的章节数"""
        count = 0
        for intensity in reversed(intensities):
            if operator == ">=" and intensity >= threshold:
                count += 1
            elif operator == "<=" and intensity <= threshold:
                count += 1
            else:
                break
        return count
    
    def _get_opening_suggestion(self) -> Dict[str, Any]:
        """获取开篇建议"""
        return {
            "curve_analysis": {
                "recent_chapters": [],
                "overall_trend": "ascending",
                "pattern_warning": None,
                "average_intensity": 0
            },
            "next_chapter_suggestion": {
                "suggested_intensity": 5,
                "suggested_type": "rising",
                "suggested_tone": "期待",
                "reasoning": "开篇第一章，建议中等强度，建立世界观和人物，同时制造悬念吸引读者",
                "pacing_instructions": [
                    "快速建立主角形象",
                    "展示世界观核心设定",
                    "埋下第一个悬念或冲突",
                    "结尾留下钩子"
                ],
                "avoid_patterns": [
                    "过长的背景介绍",
                    "信息量过载",
                    "无冲突的平淡开场"
                ]
            }
        }
    
    def _get_default_suggestion(self, chapter_count: int) -> Dict[str, Any]:
        """获取默认建议"""
        base_intensity = 5 + (chapter_count % 3)  # 5-7 之间波动
        return {
            "curve_analysis": {
                "recent_chapters": [],
                "overall_trend": "fluctuating",
                "pattern_warning": None,
                "average_intensity": 5.0
            },
            "next_chapter_suggestion": {
                "suggested_intensity": base_intensity,
                "suggested_type": "rising" if base_intensity > 5 else "transition",
                "suggested_tone": "期待",
                "reasoning": "根据章节数自动生成的默认建议",
                "pacing_instructions": [
                    "保持适度的冲突推进",
                    "角色发展与剧情平衡"
                ],
                "avoid_patterns": []
            }
        }
    
    def generate_pacing_prompt(self, suggestion: Dict[str, Any]) -> str:
        """
        根据节奏建议生成供 Writer 使用的节奏控制提示词
        
        Args:
            suggestion: 节奏建议
            
        Returns:
            格式化的节奏控制提示词
        """
        s = suggestion.get("next_chapter_suggestion", suggestion)
        
        intensity = s.get("suggested_intensity", 5)
        rhythm_type = s.get("suggested_type", "transition")
        tone = s.get("suggested_tone", "平静")
        instructions = s.get("pacing_instructions", [])
        avoid = s.get("avoid_patterns", [])
        
        prompt_parts = [
            f"\n【本章节奏控制】",
            f"- 节奏强度：{intensity}/10（{self._intensity_description(intensity)}）",
            f"- 节奏类型：{self.RHYTHM_TYPES.get(rhythm_type, rhythm_type)}",
            f"- 情绪基调：{tone}"
        ]
        
        if instructions:
            prompt_parts.append("- 节奏要求：" + "；".join(instructions))
        
        if avoid:
            prompt_parts.append("- 避免：" + "；".join(avoid))
        
        return "\n".join(prompt_parts)
    
    def _intensity_description(self, intensity: int) -> str:
        """获取强度描述"""
        if intensity <= 2:
            return "极度舒缓，日常/休息"
        elif intensity <= 4:
            return "平静舒缓，适合铺垫"
        elif intensity <= 6:
            return "中等强度，稳步推进"
        elif intensity <= 8:
            return "较高强度，冲突加剧"
        else:
            return "极高强度，高潮/转折"
