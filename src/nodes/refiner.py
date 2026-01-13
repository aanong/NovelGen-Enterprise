import logging
import asyncio
from typing import Dict, Any, List
from ..schemas.state import NGEState
from ..agents.constants import NodeAction
from ..db.vector_store import VectorStore
from .base import BaseNode

logger = logging.getLogger(__name__)

class RefineContextNode(BaseNode):
    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        """上下文精炼 (增强的 RAG Implementation)"""
        print("--- REFINING CONTEXT VIA ENHANCED RAG ---")
        
        # 1. 构建更精准的 RAG 查询
        query = self._build_rag_query(state)
        
        vs = VectorStore()
        try:
            # 2. 并行检索多种资料（增强检索范围）
            bible_results, style_results, plot_tropes, char_archetypes = await asyncio.gather(
                vs.search_bible(query, top_k=5),
                vs.search_style(query, top_k=3),
                vs.search_references(query, top_k=2, category="plot_trope"),
                vs.search_references(query, top_k=2, category="character_archetype"),
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
            bible_context = "\n".join([f"[{b['key']}]: {b['content']}" for b in bible_results]) if bible_results else ""
            
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
            
            # 4. 更新 State 中的提示词
            enhanced_instruction = (
                f"{state.review_feedback}\n\n"
                f"【参考世界观设定】\n{bible_context}\n"
                f"{style_context}"
                f"{plot_context}"
                f"{archetype_context}"
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
        
        # 从 review_feedback 中提取场景和冲突信息
        if state.review_feedback:
            query_parts.append(state.review_feedback[:200])  # 限制长度
        
        # 添加当前剧情点信息
        if state.current_plot_index < len(state.plot_progress):
            plot_point = state.plot_progress[state.current_plot_index]
            query_parts.append(plot_point.title)
            query_parts.append(plot_point.description[:100])
        
        # 添加涉及的主要人物
        if state.characters:
            main_chars = [name for name, char in list(state.characters.items())[:3] 
                         if char.current_mood]
            if main_chars:
                query_parts.append(" ".join(main_chars))
        
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
