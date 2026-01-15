"""
AllusionAdvisor Agent 模块
负责典故主动注入与追踪
支持典故推荐、变体应用建议、使用追踪、使用验证
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from ..schemas.state import NGEState
from ..schemas.literary import (
    LiteraryElement, LiteraryElementType, AllusionDetail,
    PoetryQuote, NarrativeMotif, AllusionUsageValidation,
    PRESET_ALLUSIONS, PRESET_POETRY, PRESET_MOTIFS,
    EmotionalCategory, CulturalContext
)
from ..config import Config
from ..utils import strip_think_tags, extract_json_from_text, normalize_llm_content
from ..db.vector_store import VectorStore
from ..db.models import ReferenceMaterial
from .base import BaseAgent


class AllusionUsageType(BaseModel):
    """典故使用方式"""
    usage_type: str = Field(description="使用方式：direct(直接引用)/adapted(改编)/inverted(反用)/implicit(暗用)/transformed(化用)")
    description: str = Field(description="使用方式说明")


class AllusionRecommendation(BaseModel):
    """典故推荐"""
    title: str = Field(description="典故标题/名称")
    source: str = Field(description="典故来源（书名/作者）")
    original_context: str = Field(description="原典故的简要内容")
    relevance_reason: str = Field(description="与当前场景的关联原因")
    suggested_usage: AllusionUsageType = Field(description="建议的使用方式")
    application_example: str = Field(description="应用示例（如何在当前场景中使用）")
    fit_score: float = Field(ge=0.0, le=1.0, description="契合度评分 0.0-1.0")


class AllusionAdvice(BaseModel):
    """典故建议结果"""
    scene_analysis: str = Field(description="当前场景分析")
    recommendations: List[AllusionRecommendation] = Field(description="推荐的典故列表")
    usage_cautions: List[str] = Field(default_factory=list, description="使用注意事项")
    already_used_warnings: List[str] = Field(default_factory=list, description="已使用典故警告")


class AllusionUsageRecord(BaseModel):
    """典故使用记录"""
    allusion_title: str = Field(description="典故标题")
    chapter_number: int = Field(description="使用章节")
    usage_type: str = Field(description="使用方式")
    context: str = Field(description="使用场景描述")
    reference_id: Optional[int] = Field(None, description="关联的 ReferenceMaterial ID")


class AllusionAdvisor(BaseAgent):
    """
    AllusionAdvisor Agent: 负责典故主动注入与追踪
    
    职责：
    1. 根据当前场景主动推荐可用典故
    2. 建议典故的变体应用（直接引用、改编、反用、暗用、化用）
    3. 追踪已使用的典故，避免重复
    4. 生成典故注入提示词供 Writer/Refiner 使用
    """
    
    # 典故使用方式说明
    USAGE_TYPES = {
        "direct": "直接引用：明确引用典故原文或直接提及典故名称",
        "adapted": "改编：保留典故核心，但改变具体情节或人物",
        "inverted": "反用：与典故原意相反，形成反讽或对比效果",
        "implicit": "暗用：不直接提及典故，但情节或意象暗合典故",
        "transformed": "化用：提取典故精神或意象，完全融入新的叙事中"
    }
    
    def __init__(self, temperature: Optional[float] = None):
        """
        初始化 AllusionAdvisor Agent
        
        Args:
            temperature: 温度参数，默认使用配置值
        """
        super().__init__(
            model_name="gemini",  # 使用 Gemini 进行文学创意分析
            temperature=temperature or 0.7,  # 较高温度增加创意性
            mock_responses=[
                json.dumps({
                    "scene_analysis": "当前场景涉及主角面临重大抉择",
                    "recommendations": [
                        {
                            "title": "卧薪尝胆",
                            "source": "《史记·越王勾践世家》",
                            "original_context": "越王勾践忍辱负重，最终复仇成功",
                            "relevance_reason": "与主角当前处境相似",
                            "suggested_usage": {"usage_type": "implicit", "description": "暗示主角的隐忍"},
                            "application_example": "可描写主角默默承受，暗示日后必有报复",
                            "fit_score": 0.8
                        }
                    ],
                    "usage_cautions": ["注意不要过于直白"],
                    "already_used_warnings": []
                })
            ]
        )
        self.advice_parser = PydanticOutputParser(pydantic_object=AllusionAdvice)
        self.vector_store = VectorStore()
        
        # 使用记录缓存（实际应用中应持久化到数据库）
        self._usage_history: Dict[int, List[AllusionUsageRecord]] = {}  # novel_id -> records
    
    async def process(self, state: NGEState, **kwargs) -> Dict[str, Any]:
        """
        处理典故推荐任务
        
        Args:
            state: 当前状态
            
        Returns:
            典故推荐结果
        """
        return await self.recommend_allusions(state)
    
    async def recommend_allusions(
        self,
        state: NGEState,
        max_recommendations: int = 3
    ) -> Dict[str, Any]:
        """
        根据当前场景推荐典故
        
        Args:
            state: 当前状态
            max_recommendations: 最大推荐数量
            
        Returns:
            典故推荐结果
        """
        # 1. 构建场景描述
        scene_description = self._build_scene_description(state)
        
        # 2. 从资料库检索相关典故
        retrieved_allusions = await self._retrieve_allusions(scene_description, state)
        
        # 3. 获取已使用的典故
        used_allusions = self._get_used_allusions(state.current_novel_id)
        
        # 4. 调用 LLM 生成推荐
        prompt = self._create_recommendation_prompt()
        
        messages = prompt.format_messages(
            scene_description=scene_description,
            retrieved_allusions=self._format_allusions(retrieved_allusions),
            used_allusions=self._format_used_allusions(used_allusions),
            usage_types=self._format_usage_types(),
            max_recommendations=max_recommendations,
            format_instructions=self.advice_parser.get_format_instructions()
        )
        
        try:
            response = await self.llm.ainvoke(messages)
            content = strip_think_tags(normalize_llm_content(response.content))
            
            result_json = extract_json_from_text(content)
            if isinstance(result_json, dict):
                return result_json
            
            raise ValueError("无法解析典故推荐结果")
            
        except Exception as e:
            print(f"AllusionAdvisor Error: {e}")
            return self._get_default_result(scene_description)
    
    def _build_scene_description(self, state: NGEState) -> str:
        """构建当前场景描述"""
        parts = []
        
        # 当前剧情点
        if state.current_plot_index < len(state.plot_progress):
            plot_point = state.plot_progress[state.current_plot_index]
            parts.append(f"剧情点：{plot_point.title}")
            parts.append(f"描述：{plot_point.description}")
        
        # 涉及的主要人物
        if state.characters:
            char_info = []
            for name, char in list(state.characters.items())[:3]:
                mood = char.current_mood
                traits = char.personality_traits.get('personality', '')
                char_info.append(f"{name}（{traits}，当前{mood}）")
            if char_info:
                parts.append(f"涉及人物：{', '.join(char_info)}")
        
        # 最近的章节摘要
        if state.memory_context.recent_summaries:
            last_summary = state.memory_context.recent_summaries[-1]
            parts.append(f"前情：{last_summary[:150]}...")
        
        # 规划指令
        if state.review_feedback:
            parts.append(f"规划：{state.review_feedback[:200]}...")
        
        return "\n".join(parts)
    
    async def _retrieve_allusions(
        self,
        query: str,
        state: NGEState,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """从资料库检索相关典故"""
        try:
            # 检索剧情套路
            plot_tropes = await self.vector_store.search(
                query,
                model_class=ReferenceMaterial,
                top_k=top_k,
                filters={"category": "plot_trope"},
                novel_id=state.current_novel_id
            )
            
            # 检索人物原型
            char_archetypes = await self.vector_store.search(
                query,
                model_class=ReferenceMaterial,
                top_k=top_k // 2,
                filters={"category": "character_archetype"},
                novel_id=state.current_novel_id
            )
            
            # 检索世界观设定中的典故
            world_refs = await self.vector_store.search(
                query,
                model_class=ReferenceMaterial,
                top_k=top_k // 2,
                filters={"category": "world_setting"},
                novel_id=state.current_novel_id
            )
            
            all_refs = []
            for ref_list in [plot_tropes, char_archetypes, world_refs]:
                if isinstance(ref_list, list):
                    all_refs.extend(ref_list)
            
            return all_refs
            
        except Exception as e:
            print(f"典故检索失败: {e}")
            return []
    
    def _create_recommendation_prompt(self) -> ChatPromptTemplate:
        """创建典故推荐提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个博学的文学顾问，精通中外经典文学、历史典故、神话传说。\n"
                "任务是根据当前场景推荐可用的典故，并建议最佳的使用方式。\n\n"
                "【典故使用方式】\n"
                "{usage_types}\n\n"
                "【推荐原则】\n"
                "1. 典故必须与场景有明确的关联性\n"
                "2. 优先推荐可以巧妙融入叙事的典故\n"
                "3. 避免推荐过于常见或陈腐的典故\n"
                "4. 考虑典故的文化背景与小说世界观的匹配度\n"
                "5. 已使用过的典故不要重复推荐，除非是有意呼应\n\n"
                "输出必须是严格的 JSON 格式。\n"
                "{format_instructions}"
            )),
            ("human", (
                "【当前场景】\n{scene_description}\n\n"
                "【资料库中的相关典故】\n{retrieved_allusions}\n\n"
                "【已使用的典故】\n{used_allusions}\n\n"
                "请推荐最多 {max_recommendations} 个适合当前场景的典故，并给出具体的使用建议。"
            ))
        ])
    
    def _format_allusions(self, allusions: List[Dict[str, Any]]) -> str:
        """格式化检索到的典故"""
        if not allusions:
            return "（资料库暂无相关典故，请根据通用文学知识推荐）"
        
        lines = []
        for i, ref in enumerate(allusions, 1):
            title = ref.get('title', '未知')
            source = ref.get('source', '未知来源')
            content = ref.get('content', '')[:200]
            lines.append(f"{i}. {title}（{source}）：{content}...")
        
        return "\n".join(lines)
    
    def _format_used_allusions(self, used: List[AllusionUsageRecord]) -> str:
        """格式化已使用的典故"""
        if not used:
            return "（暂无已使用的典故）"
        
        lines = []
        for record in used[-10:]:  # 只显示最近 10 个
            lines.append(
                f"- {record.allusion_title}（第{record.chapter_number}章，{record.usage_type}）"
            )
        
        return "\n".join(lines)
    
    def _format_usage_types(self) -> str:
        """格式化使用方式说明"""
        return "\n".join([f"- {k}: {v}" for k, v in self.USAGE_TYPES.items()])
    
    def _get_used_allusions(self, novel_id: int) -> List[AllusionUsageRecord]:
        """获取已使用的典故记录"""
        return self._usage_history.get(novel_id, [])
    
    def record_usage(
        self,
        novel_id: int,
        allusion_title: str,
        chapter_number: int,
        usage_type: str,
        context: str,
        reference_id: Optional[int] = None
    ):
        """
        记录典故使用
        
        Args:
            novel_id: 小说 ID
            allusion_title: 典故标题
            chapter_number: 使用章节
            usage_type: 使用方式
            context: 使用场景描述
            reference_id: 关联的资料 ID
        """
        if novel_id not in self._usage_history:
            self._usage_history[novel_id] = []
        
        record = AllusionUsageRecord(
            allusion_title=allusion_title,
            chapter_number=chapter_number,
            usage_type=usage_type,
            context=context,
            reference_id=reference_id
        )
        self._usage_history[novel_id].append(record)
    
    def _get_default_result(self, scene_description: str) -> Dict[str, Any]:
        """获取默认结果"""
        return {
            "scene_analysis": scene_description[:100],
            "recommendations": [],
            "usage_cautions": ["无法生成推荐，请手动选择典故"],
            "already_used_warnings": []
        }
    
    def generate_injection_prompt(self, advice: Dict[str, Any]) -> str:
        """
        根据典故建议生成供 Writer/Refiner 使用的注入提示词
        
        Args:
            advice: 典故推荐结果
            
        Returns:
            格式化的典故注入提示词
        """
        recommendations = advice.get("recommendations", [])
        if not recommendations:
            return ""
        
        prompt_parts = ["\n【典故注入建议】（可选择使用）"]
        
        for i, rec in enumerate(recommendations[:3], 1):
            title = rec.get("title", "未知")
            usage = rec.get("suggested_usage", {})
            usage_type = usage.get("usage_type", "implicit") if isinstance(usage, dict) else "implicit"
            usage_type_cn = {
                "direct": "直接引用",
                "adapted": "改编",
                "inverted": "反用",
                "implicit": "暗用",
                "transformed": "化用"
            }.get(usage_type, usage_type)
            
            example = rec.get("application_example", "")
            fit_score = rec.get("fit_score", 0.5)
            
            prompt_parts.append(
                f"\n{i}. 【{title}】（建议{usage_type_cn}，契合度 {fit_score:.0%}）\n"
                f"   应用示例：{example}"
            )
        
        cautions = advice.get("usage_cautions", [])
        if cautions:
            prompt_parts.append("\n注意事项：" + "；".join(cautions))
        
        return "\n".join(prompt_parts)
    
    def get_usage_statistics(self, novel_id: int) -> Dict[str, Any]:
        """
        获取典故使用统计
        
        Args:
            novel_id: 小说 ID
            
        Returns:
            使用统计信息
        """
        records = self._usage_history.get(novel_id, [])
        
        if not records:
            return {
                "total_usages": 0,
                "unique_allusions": 0,
                "by_type": {},
                "by_chapter": {}
            }
        
        unique_titles = set(r.allusion_title for r in records)
        by_type = {}
        by_chapter = {}
        
        for r in records:
            by_type[r.usage_type] = by_type.get(r.usage_type, 0) + 1
            by_chapter[r.chapter_number] = by_chapter.get(r.chapter_number, 0) + 1
        
        return {
            "total_usages": len(records),
            "unique_allusions": len(unique_titles),
            "by_type": by_type,
            "by_chapter": by_chapter
        }
    
    # ============ 新增：典故验证系统 ============
    
    async def validate_allusion_usage(
        self,
        content: str,
        expected_allusions: List[str],
        scene_context: str = ""
    ) -> List[AllusionUsageValidation]:
        """
        验证典故是否被正确使用
        
        Args:
            content: 章节内容
            expected_allusions: 预期使用的典故列表
            scene_context: 场景上下文
            
        Returns:
            验证结果列表
        """
        if not expected_allusions:
            return []
        
        prompt = self._create_validation_prompt()
        
        # 获取典故详情
        allusion_details = self._get_allusion_details(expected_allusions)
        
        messages = prompt.format_messages(
            content=content[:5000],  # 限制长度
            allusion_details=allusion_details,
            scene_context=scene_context
        )
        
        try:
            response = await self.llm.ainvoke(messages)
            result_content = strip_think_tags(normalize_llm_content(response.content))
            
            result_json = extract_json_from_text(result_content)
            if isinstance(result_json, dict) and "validations" in result_json:
                validations = []
                for v in result_json["validations"]:
                    try:
                        validations.append(AllusionUsageValidation.model_validate(v))
                    except Exception:
                        pass
                return validations
            
            return []
            
        except Exception as e:
            print(f"典故验证失败: {e}")
            return []
    
    def _create_validation_prompt(self) -> ChatPromptTemplate:
        """创建验证提示词"""
        return ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个文学专家，专门验证典故在文本中的使用质量。\n\n"
                "【验证标准】\n"
                "1. 典故是否被正确融入文本（而非生硬堆砌）\n"
                "2. 使用方式是否恰当（直接引用/改编/反用/暗用/化用）\n"
                "3. 与场景的契合度（是否适合当前情境）\n"
                "4. 自然度评分（读者是否会觉得突兀）\n\n"
                "输出必须是 JSON 格式：\n"
                "```json\n"
                "{\n"
                '  "validations": [\n'
                "    {\n"
                '      "allusion_title": "典故名",\n'
                '      "is_correct": true/false,\n'
                '      "detected_usage_type": "使用方式",\n'
                '      "naturalness_score": 0.0-1.0,\n'
                '      "fit_score": 0.0-1.0,\n'
                '      "issues": ["问题1"],\n'
                '      "suggestions": ["建议1"]\n'
                "    }\n"
                "  ]\n"
                "}\n"
                "```"
            )),
            ("human", (
                "【待验证文本】\n{content}\n\n"
                "【预期典故及详情】\n{allusion_details}\n\n"
                "【场景上下文】\n{scene_context}\n\n"
                "请验证这些典故的使用质量。"
            ))
        ])
    
    def _get_allusion_details(self, allusion_titles: List[str]) -> str:
        """获取典故详情用于验证"""
        details = []
        
        for title in allusion_titles:
            # 从预置库查找
            found = None
            for allusion in PRESET_ALLUSIONS:
                if allusion.title == title:
                    found = allusion
                    break
            
            if found:
                details.append(
                    f"【{found.title}】\n"
                    f"  来源：{found.origin}\n"
                    f"  核心含义：{found.core_meaning}\n"
                    f"  常见误用：{', '.join(found.common_misuses)}"
                )
            else:
                details.append(f"【{title}】（无详细信息）")
        
        return "\n".join(details)
    
    # ============ 新增：预置库检索 ============
    
    def search_preset_allusions(
        self,
        emotion: Optional[EmotionalCategory] = None,
        theme: Optional[str] = None,
        limit: int = 5
    ) -> List[AllusionDetail]:
        """
        从预置典故库中搜索
        
        Args:
            emotion: 情感类型
            theme: 主题关键词
            limit: 最大返回数量
            
        Returns:
            匹配的典故列表
        """
        results = []
        
        for allusion in PRESET_ALLUSIONS:
            score = 0
            
            if emotion and emotion in allusion.emotions:
                score += 2
            
            if theme:
                # 简单的关键词匹配
                theme_lower = theme.lower()
                if theme_lower in allusion.core_meaning.lower():
                    score += 1
                if theme_lower in allusion.original_story.lower():
                    score += 1
            
            if score > 0:
                results.append((score, allusion))
        
        # 按分数排序
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [a for _, a in results[:limit]]
    
    def search_preset_poetry(
        self,
        mood: Optional[EmotionalCategory] = None,
        imagery: Optional[str] = None,
        limit: int = 5
    ) -> List[PoetryQuote]:
        """
        从预置诗词库中搜索
        
        Args:
            mood: 意境情感
            imagery: 意象关键词
            limit: 最大返回数量
            
        Returns:
            匹配的诗句列表
        """
        results = []
        
        for poetry in PRESET_POETRY:
            score = 0
            
            if mood and poetry.mood == mood:
                score += 2
            
            if imagery:
                imagery_lower = imagery.lower()
                for img in poetry.imagery:
                    if imagery_lower in img.lower():
                        score += 1
                        break
            
            if score > 0:
                results.append((score, poetry))
        
        results.sort(key=lambda x: x[0], reverse=True)
        
        return [p for _, p in results[:limit]]
    
    def get_motif_by_name(self, name: str) -> Optional[NarrativeMotif]:
        """
        根据名称获取叙事母题
        
        Args:
            name: 母题名称
            
        Returns:
            叙事母题对象
        """
        for motif in PRESET_MOTIFS:
            if name in motif.name:
                return motif
        return None
    
    def recommend_literary_elements(
        self,
        state: NGEState,
        element_types: List[LiteraryElementType] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        综合推荐文学元素（典故、诗词、母题）
        
        Args:
            state: 当前状态
            element_types: 要推荐的元素类型
            
        Returns:
            分类的推荐结果
        """
        if element_types is None:
            element_types = [
                LiteraryElementType.ALLUSION,
                LiteraryElementType.POETRY,
                LiteraryElementType.MOTIF
            ]
        
        # 分析当前情感
        current_emotion = self._detect_emotion(state)
        
        results = {}
        
        if LiteraryElementType.ALLUSION in element_types:
            allusions = self.search_preset_allusions(emotion=current_emotion, limit=3)
            results["allusions"] = [
                {
                    "title": a.title,
                    "core_meaning": a.core_meaning,
                    "usage_example": a.usage_examples.get("implicit", "")
                }
                for a in allusions
            ]
        
        if LiteraryElementType.POETRY in element_types:
            poetry = self.search_preset_poetry(mood=current_emotion, limit=3)
            results["poetry"] = [
                {
                    "quote": p.quote,
                    "author": p.author,
                    "adaptation": p.adaptation_example
                }
                for p in poetry
            ]
        
        if LiteraryElementType.MOTIF in element_types:
            results["motifs"] = [
                {
                    "name": m.name,
                    "description": m.description[:100]
                }
                for m in PRESET_MOTIFS[:2]
            ]
        
        return results
    
    def _detect_emotion(self, state: NGEState) -> Optional[EmotionalCategory]:
        """从状态中检测当前情感"""
        # 简单的情感检测逻辑
        if state.current_plot_index < len(state.plot_progress):
            plot = state.plot_progress[state.current_plot_index]
            desc = plot.description.lower()
            
            emotion_keywords = {
                EmotionalCategory.PARTING: ["离别", "分离", "告别"],
                EmotionalCategory.REVENGE: ["复仇", "报仇", "仇恨"],
                EmotionalCategory.SORROW: ["悲伤", "痛苦", "失去"],
                EmotionalCategory.HOPE: ["希望", "转机", "新生"],
                EmotionalCategory.AMBITION: ["雄心", "壮志", "征服"],
            }
            
            for emotion, keywords in emotion_keywords.items():
                for kw in keywords:
                    if kw in desc:
                        return emotion
        
        return None
