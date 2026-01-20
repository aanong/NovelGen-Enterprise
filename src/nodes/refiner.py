import logging
import asyncio
import re
from typing import Dict, Any, List, Optional
from ..schemas.state import NGEState
from ..core.types import NodeAction
from ..db.vector_store import VectorStore
from ..db.models import NovelBible, StyleRef, ReferenceMaterial
from ..agents.allusion_advisor import AllusionAdvisor
from .base import BaseNode
from ..core.registry import register_node

logger = logging.getLogger(__name__)

@register_node("refine_context")
class RefineContextNode(BaseNode):
    """
    上下文精炼节点
    负责 RAG 检索、典故注入等上下文增强
    """
    
    def __init__(self, allusion_advisor: Optional[AllusionAdvisor] = None):
        """
        初始化上下文精炼节点
        
        Args:
            allusion_advisor: 典故顾问（可选，为空则自动创建）
        """
        self.allusion_advisor = allusion_advisor or AllusionAdvisor()
    
    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        """上下文精炼 (增强的 RAG Implementation)"""
        print("--- REFINING CONTEXT VIA ENHANCED RAG ---")
        
        # 1. 构建更精准的 RAG 查询
        query = self._build_rag_query(state)
        novel_id = state.novel_id if hasattr(state, 'novel_id') else None
        
        vs = VectorStore()
        try:
            # 2. 并行检索多种资料（增强检索范围）
            bible_results, style_results, plot_tropes, char_archetypes = await asyncio.gather(
                vs.search(query, model_class=NovelBible, top_k=5, novel_id=novel_id),
                vs.search(query, model_class=StyleRef, top_k=3, novel_id=novel_id),
                vs.search(query, model_class=ReferenceMaterial, top_k=2, filters={"category": "plot_trope"}, novel_id=novel_id),
                vs.search(query, model_class=ReferenceMaterial, top_k=2, filters={"category": "character_archetype"}, novel_id=novel_id),
                return_exceptions=True
            )
            
            # 处理异常
            if isinstance(bible_results, Exception):
                logger.warning(f"Bible search failed: {bible_results}")
                bible_results = []
            if isinstance(style_results, Exception):
                logger.warning(f"Style search failed: {style_results}")
                style_results = []
            if isinstance(plot_tropes, Exception):
                logger.warning(f"Plot tropes search failed: {plot_tropes}")
                plot_tropes = []
            if isinstance(char_archetypes, Exception):
                logger.warning(f"Character archetypes search failed: {char_archetypes}")
                char_archetypes = []
            
            # 3. 格式化检索结果
            bible_context = "\n".join([f"[{b.get('key', 'Unknown')}]: {b.get('content', '')}" for b in bible_results]) if bible_results else ""
            
            # 多文风参考融合
            style_context = self._format_style_references(style_results, state)
            
            # 剧情套路参考
            plot_context = ""
            if plot_tropes:
                plot_context = "\n【剧情套路参考】\n" + "\n".join([
                    f"- {t.get('title', '套路')}: {t.get('content', '')[:150]}..."
                    for t in plot_tropes
                ])
            
            # 人物原型参考
            archetype_context = ""
            if char_archetypes:
                archetype_context = "\n【人物原型参考】\n" + "\n".join([
                    f"- {a.get('title', '原型')}: {a.get('content', '')[:150]}..."
                    for a in char_archetypes
                ])
            
            print(f"✅ 增强 RAG 检索完成。世界观:{len(bible_results)}, 文风:{len(style_results)}, 套路:{len(plot_tropes)}, 原型:{len(char_archetypes)}")
            
            # 4. 典故主动注入（新增）
            allusion_context = ""
            try:
                allusion_advice = await self.allusion_advisor.recommend_allusions(state)
                if allusion_advice and allusion_advice.get("recommendations"):
                    allusion_context = self.allusion_advisor.generate_injection_prompt(allusion_advice)
                    rec_count = len(allusion_advice.get("recommendations", []))
                    print(f"📚 典故推荐完成，推荐 {rec_count} 个典故")
                    
                    # 检查已使用警告
                    warnings = allusion_advice.get("already_used_warnings", [])
                    if warnings:
                        print(f"⚠️ 典故重复警告: {', '.join(warnings[:2])}")
            except Exception as e:
                logger.warning(f"典故推荐跳过: {e}")
            
            # 5. 更新 State 中的提示词
            enhanced_instruction = (
                f"{state.review_feedback}\n\n"
                f"【参考世界观设定】\n{bible_context}\n"
                f"{style_context}"
                f"{plot_context}"
                f"{archetype_context}"
                f"{allusion_context}"
            )
            
            # 保存到 refined_context 供后续使用
            refined_context_list = []
            if bible_context:
                refined_context_list.append(f"世界观设定：{bible_context[:200]}...")
            if plot_context:
                refined_context_list.append(f"剧情套路：{plot_context[:200]}...")
            
            return {
                "next_action": NodeAction.WRITE,
                "review_feedback": enhanced_instruction,
                "refined_context": refined_context_list
            }
        except Exception as e:
            logger.error(f"RAG refinement error: {e}", exc_info=True)
            print(f"RAG Error: {e}")
            return {"next_action": NodeAction.WRITE}
        finally:
            vs.close()
    
    def _build_rag_query(self, state: NGEState) -> str:
        """构建更精准的 RAG 查询"""
        query_parts = []
        
        # 1. 从规划指令中提取核心信息
        if state.review_feedback:
            # 尝试提取 Scene 和 Conflict
            instruction = state.review_feedback
            scene_match = re.search(r"Scene: (.*?)(?:\n|$)", instruction)
            conflict_match = re.search(r"Conflict: (.*?)(?:\n|$)", instruction)
            
            if scene_match:
                query_parts.append(scene_match.group(1))
            if conflict_match:
                query_parts.append(conflict_match.group(1))
            
            # 如果没匹配到，取前 200 字
            if not scene_match and not conflict_match:
                query_parts.append(instruction[:200])
        
        # 2. 添加当前剧情大纲点
        if state.current_plot_index < len(state.plot_progress):
            plot_point = state.plot_progress[state.current_plot_index]
            query_parts.append(getattr(plot_point, "title", ""))
            query_parts.append(getattr(plot_point, "description", "")[:100])
        
        # 3. 添加涉及的主要人物及当前状态
        if state.characters:
            for name, char in list(state.characters.items())[:3]:
                if char.current_mood:
                    query_parts.append(f"{name} {char.current_mood}")
                # 添加重要物品
                if char.inventory:
                    items = [getattr(i, 'name', str(i)) for i in char.inventory[:2]]
                    query_parts.append(" ".join(items))
        
        # 4. 添加全局未回收伏笔
        if state.memory_context.global_foreshadowing:
            # 取最近两条伏笔增加检索相关性
            threads = state.memory_context.global_foreshadowing[-2:]
            query_parts.append(" ".join(threads))
        
        return " ".join([p for p in query_parts if p])
    
    def _format_style_references(self, style_results: list, state: NGEState) -> str:
        """格式化多文风参考"""
        if not style_results:
            return "【文风参考范例】\n常规文风\n"
        
        # 根据场景类型选择不同的文风描述
        scene_type = state.antigravity_context.scene_constraints.get("scene_type", "Normal")
        
        style_parts = [f"【文风参考（{scene_type}场景）】"]
        for i, style in enumerate(style_results[:3], 1):
            content = style.get('content', '')
            if content:
                style_parts.append(f"\n参考 {i}：\n{content[:300]}...")
        
        return "\n".join(style_parts) + "\n"
