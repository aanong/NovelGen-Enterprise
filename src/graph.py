"""
NGEGraph 模块
定义 NovelGen-Enterprise 的工作流图
"""
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from .schemas.state import NGEState, WorldItemSchema
from .agents.architect import ArchitectAgent
from .agents.writer import WriterAgent
from .agents.reviewer import ReviewerAgent
from .agents.style_analyzer import StyleAnalyzer
from .agents.evolver import CharacterEvolver
from .agents.summarizer import ChapterSummarizer
from .agents.constants import NodeAction, ReviewDecision, OutlineStatus, Defaults
from .db.base import SessionLocal
from .db.models import (
    Novel, NovelBible, Character, CharacterRelationship, 
    PlotOutline, LogicAudit, Chapter as DBChapter, 
    WorldItem, CharacterBranchStatus
)
from .db.vector_store import VectorStore
from .monitoring import monitor
from .utils import strip_think_tags, normalize_llm_content
from .config import Config
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NGEGraph:
    def __init__(self):
        self.architect = ArchitectAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()
        self.analyzer = StyleAnalyzer()
        self.evolver = CharacterEvolver()
        self.summarizer = ChapterSummarizer()
        
        self.workflow = StateGraph(NGEState)
        self._build_graph()

    def _build_graph(self):
        # 节点定义
        self.workflow.add_node("load_context", self.load_context_node) 
        self.workflow.add_node("plan", self.plan_node)
        self.workflow.add_node("refine_context", self.refine_context_node) 
        self.workflow.add_node("write", self.write_node)
        self.workflow.add_node("review", self.review_node)
        self.workflow.add_node("evolve", self.evolve_node)
        
        # 连线
        self.workflow.add_node("repair", self.repair_node) 
        
        # 连线
        self.workflow.set_entry_point("load_context")
        self.workflow.add_edge("load_context", "plan")
        self.workflow.add_edge("plan", "refine_context")
        self.workflow.add_edge("refine_context", "write")
        self.workflow.add_edge("write", "review")
        
        # 条件分支
        self.workflow.add_conditional_edges(
            "review",
            self.should_continue,
            {
                ReviewDecision.CONTINUE: NodeAction.EVOLVE,
                ReviewDecision.REVISE: NodeAction.WRITE,
                ReviewDecision.REPAIR: NodeAction.REPAIR
            }
        )
        
        self.workflow.add_edge("repair", "evolve")
        self.workflow.add_edge("evolve", END)
        
        self.app = self.workflow.compile()

    async def load_context_node(self, state: NGEState):
        """从数据库加载/刷新当前的 State（如人物状态、世界观、历史摘要）"""
        current_ch = state.current_plot_index + 1
        print(f"--- LOADING CONTEXT (Chapter {current_ch}, Branch: {state.current_branch}) ---")
        
        # 启动性能会话
        monitor.start_session(current_ch)
        
        db = SessionLocal()
        try:
            # 1. 同步角色状态 (支持分支快照)
            db_chars = db.query(Character).filter(Character.novel_id == state.current_novel_id).all()
            for c in db_chars:
                if c.name in state.characters:
                    char_state = state.characters[c.name]
                    
                    # 默认使用全局最新状态
                    target_mood = c.current_mood
                    target_skills = c.skills or []
                    target_assets = c.assets or {}
                    target_status = c.status or {}
                    
                    # 尝试查找分支快照
                    # 查找条件：当前分支，章节号 < 当前章节，按章节号倒序取第一个
                    snapshot = db.query(CharacterBranchStatus).filter(
                        CharacterBranchStatus.character_id == c.id,
                        CharacterBranchStatus.branch_id == state.current_branch,
                        CharacterBranchStatus.chapter_number < current_ch
                    ).order_by(CharacterBranchStatus.chapter_number.desc()).first()
                    
                    if snapshot:
                        print(f"  - Loaded snapshot for {c.name} from Branch {state.current_branch} Ch.{snapshot.chapter_number}")
                        target_mood = snapshot.current_mood
                        target_skills = snapshot.skills or []
                        target_assets = snapshot.assets or {}
                        target_status = snapshot.status or {}
                    
                    # 更新 State
                    char_state.current_mood = target_mood
                    char_state.skills = target_skills
                    char_state.assets = target_assets
                    char_state.status = target_status
                    
                    # 同步背包
                    char_state.inventory = [
                        WorldItemSchema(
                            name=item.name,
                            description=item.description or "",
                            rarity=item.rarity or "Common",
                            powers=item.powers or {},
                            location=item.location
                        ) for item in c.inventory
                    ]
            
            # 2. 同步全球物品
            db_items = db.query(WorldItem).filter(WorldItem.novel_id == state.current_novel_id).all()
            state.world_items = [
                WorldItemSchema(
                    name=item.name,
                    description=item.description or "",
                    rarity=item.rarity or "Common",
                    powers=item.powers or {},
                    location=item.location
                ) for item in db_items
            ]
            
            # 3. Rule 3.1: 加载历史摘要 (链表回溯)
            summaries = []
            
            # 确定回溯起点
            start_chapter_id = state.last_chapter_id
            if not start_chapter_id:
                # 如果没有指定起点，尝试查找当前分支的最新章节
                latest_chapter = db.query(DBChapter).filter(
                    DBChapter.novel_id == state.current_novel_id,
                    DBChapter.branch_id == state.current_branch,
                    DBChapter.chapter_number < current_ch
                ).order_by(DBChapter.chapter_number.desc()).first()
                if latest_chapter:
                    start_chapter_id = latest_chapter.id
            
            # 开始回溯（使用配置中的最大上下文章节数）
            from .config import Config
            max_context_chapters = Config.antigravity.MAX_CONTEXT_CHAPTERS
            curr_id = start_chapter_id
            for _ in range(max_context_chapters): # 回溯章节数可配置，增加上下文窗口防止剧情漂移
                if not curr_id:
                    break
                ch = db.query(DBChapter).filter(DBChapter.id == curr_id).first()
                if ch:
                    if ch.summary:
                        summaries.insert(0, ch.summary) # 插入到开头，保持时间顺序
                    curr_id = ch.previous_chapter_id
                else:
                    break
            
            state.memory_context.recent_summaries = summaries
            print(f"✅ 已加载 {len(summaries)} 条历史摘要 (Branch: {state.current_branch})。")
            
            return {"next_action": "plan"}
        except Exception as e:
            logger.error(f"Error loading context for chapter {current_ch}: {e}", exc_info=True)
            print(f"Error loading context: {e}")
            return {"next_action": "plan"}
        finally:
            db.close()

    async def plan_node(self, state: NGEState):
        print(f"--- PLANNING CHAPTER (Branch: {state.current_branch}) ---")
        db = SessionLocal()
        try:
            current_chapter_num = state.current_plot_index + 1
            
            # 0. 检查章节连贯性（如果已有前文）
            if state.last_chapter_id or state.memory_context.recent_summaries:
                coherence_check = await self._check_chapter_coherence(state)
                if not coherence_check.get("coherent", True):
                    logger.warning(f"章节连贯性检查发现问题: {coherence_check.get('issues', [])}")
                    print(f"⚠️ 连贯性提醒: {', '.join(coherence_check.get('issues', [])[:2])}")
            
            # 1. 检查 DB 是否已有大纲 (匹配 branch_id)
            outline = db.query(PlotOutline).filter_by(
                novel_id=state.current_novel_id, 
                chapter_number=current_chapter_num,
                branch_id=state.current_branch
            ).first()
            
            if outline:
                # 如果已有大纲（不管是 pending 还是 completed），直接复用
                print(f"✅ 发现现有大纲 (Ch.{current_chapter_num}, Branch: {state.current_branch}, Status: {outline.status})")
                
                # 如果是 pending 且内容为空，则可以调用 Agent 补充，但这里我们假设 import 已有内容
                if not outline.scene_description or not outline.key_conflict:
                    plan_data = await self.architect.plan_next_chapter(state)
                    outline.scene_description = plan_data.get("scene", outline.scene_description)
                    outline.key_conflict = plan_data.get("conflict", outline.key_conflict)
                    db.commit()
                    instruction = plan_data["instruction"]
                else:
                    instruction = f"Scene: {outline.scene_description}\nConflict: {outline.key_conflict}"
                
                return {"next_action": NodeAction.REFINE_CONTEXT, "review_feedback": instruction}

            # 2. 调用 Architect Agent 生成
            plan_data = await self.architect.plan_next_chapter(state)
            
            # 3. 存入 DB
            new_outline = PlotOutline(
                novel_id=state.current_novel_id,
                chapter_number=current_chapter_num,
                branch_id=state.current_branch,
                scene_description=plan_data.get("scene", "Generated Scene"),
                key_conflict=plan_data.get("conflict", "Generated Conflict"),
                status="pending"
            )
            db.add(new_outline)
            db.commit()
            
            return {"next_action": NodeAction.REFINE_CONTEXT, "review_feedback": plan_data["instruction"]}
        except Exception as e:
            logger.error(f"Planning error for chapter {current_chapter_num}: {e}", exc_info=True)
            print(f"Planning Error: {e}")
            return {"next_action": NodeAction.REFINE_CONTEXT, "review_feedback": "Error in planning."}
        finally:
            db.close()

    async def refine_context_node(self, state: NGEState):
        """上下文精炼 (增强的 RAG Implementation)"""
        print("--- REFINING CONTEXT VIA ENHANCED RAG ---")
        
        # 1. 构建更精准的 RAG 查询
        query = self._build_rag_query(state)
        
        vs = VectorStore()
        try:
            import asyncio
            
            # 2. 并行检索多种资料（增强检索范围）
            bible_results, style_results, plot_tropes, char_archetypes = await asyncio.gather(
                vs.search_bible(query, top_k=5),  # 从3增加到5
                vs.search_style(query, top_k=3),  # 从1增加到3
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
        scene_keywords = {
            "Action": "动作 战斗 紧张",
            "Emotional": "情感 心理 细腻",
            "Dialogue": "对话 交流 语言",
            "Normal": "常规 叙述"
        }
        
        style_parts = [f"【文风参考（{scene_type}场景）】"]
        for i, style in enumerate(style_results[:3], 1):
            content = style.get('content', '')
            if content:
                style_parts.append(f"\n参考 {i}：\n{content[:300]}...")
        
        return "\n".join(style_parts) + "\n"

    async def write_node(self, state: NGEState):
        print("--- WRITING CHAPTER ---")
        draft = await self.writer.write_chapter(state, state.review_feedback)
        return {"current_draft": draft, "next_action": NodeAction.REVIEW}

    async def review_node(self, state: NGEState):
        print("--- REVIEWING DRAFT ---")
        db = SessionLocal()
        try:
            review_result = await self.reviewer.review_draft(state, state.current_draft)
            
            audit = LogicAudit(
                reviewer_role="Deepseek-Critic",
                is_passed=review_result.get("passed", False),
                feedback=review_result.get("feedback", "No feedback"),
                logic_score=review_result.get("score", 0.0),
                created_at=datetime.utcnow()
            )
            db.add(audit)
            db.commit()

            if review_result.get("passed"):
                return {"next_action": NodeAction.EVOLVE, "review_feedback": "Passed"}
            else:
                return {
                    "next_action": NodeAction.WRITE, 
                    "review_feedback": f"修正建议：{review_result.get('feedback')}",
                    "retry_count": state.retry_count + 1
                }
        finally:
            db.close()

    async def evolve_node(self, state: NGEState):
        """
        最终确定本章内容，并根据内容演化角色状态。
        遵循 Rule 3.2 (人物立体与成长)。
        """
        print("--- EVOLVING CHARACTERS & FINALIZING CHAPTER ---")
        db = SessionLocal()
        try:
            # 1. 调用 Evolver Agent 分析人物变化
            evolution_result = await self.evolver.evolve(state)
            
            char_map = {c.name: c for c in db.query(Character).filter(Character.novel_id == state.current_novel_id).all()}

            # 更新角色状态和 DB
            for evo in evolution_result.evolutions:
                char = char_map.get(evo.character_name)
                if not char:
                    continue

                print(f"  - Evolving {char.name}: {evo.evolution_summary}")
                
                # 更新心情
                if evo.mood_change:
                    char.current_mood = evo.mood_change
                    if evo.character_name in state.characters:
                        state.characters[evo.character_name].current_mood = evo.mood_change

                # 更新技能
                if evo.skill_update:
                    current_skills = set(char.skills or [])
                    current_skills.update(evo.skill_update)
                    char.skills = list(current_skills)
                    if evo.character_name in state.characters:
                        state.characters[evo.character_name].skills = char.skills

                # 更新状态
                if evo.status_change:
                    char.status = evo.status_change
                    if evo.character_name in state.characters:
                        state.characters[evo.character_name].status = evo.status_change

                # 更新成长日志
                timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                log_entry = f"[{timestamp}] Ch.{state.current_plot_index + 1}: {evo.evolution_summary}"
                char.evolution_log = (char.evolution_log or []) + [log_entry]
                if evo.character_name in state.characters:
                    state.characters[evo.character_name].evolution_log.append(log_entry)

                # 处理关系变更
                if hasattr(evo, 'relationship_change') and evo.relationship_change:
                    for target_name, description in evo.relationship_change.items():
                        target_char = char_map.get(target_name)
                        if target_char:
                            rel = db.query(CharacterRelationship).filter(
                                ((CharacterRelationship.char_a_id == char.id) & (CharacterRelationship.char_b_id == target_char.id)) |
                                ((CharacterRelationship.char_a_id == target_char.id) & (CharacterRelationship.char_b_id == char.id))
                            ).first()
                            
                            if not rel:
                                rel = CharacterRelationship(
                                    char_a_id=char.id,
                                    char_b_id=target_char.id,
                                    relation_type="Neutral",
                                    intimacy=0.0,
                                    history=[]
                                )
                                db.add(rel)
                            
                            history = list(rel.history or [])
                            history.append({"chapter": state.current_plot_index + 1, "desc": description})
                            rel.history = history
                            db.commit()

                # 保存分支快照
                existing_snapshot = db.query(CharacterBranchStatus).filter_by(
                    character_id=char.id,
                    branch_id=state.current_branch,
                    chapter_number=state.current_plot_index + 1
                ).first()

                if existing_snapshot:
                    existing_snapshot.current_mood = char.current_mood
                    existing_snapshot.status = char.status
                    existing_snapshot.skills = char.skills
                    existing_snapshot.assets = char.assets
                    existing_snapshot.is_active = char.status.get("is_active", True)
                else:
                    snapshot = CharacterBranchStatus(
                        character_id=char.id,
                        branch_id=state.current_branch,
                        chapter_number=state.current_plot_index + 1,
                        current_mood=char.current_mood,
                        status=char.status,
                        skills=char.skills,
                        assets=char.assets,
                        is_active=char.status.get("is_active", True)
                    )
                    db.add(snapshot)

            # 处理剧情线更新
            if evolution_result.story_updates:
                updates = evolution_result.story_updates
                
                if updates.new_foreshadowing:
                    for f in updates.new_foreshadowing:
                        if f not in state.memory_context.global_foreshadowing:
                            state.memory_context.global_foreshadowing.append(f)
                            print(f"📖 New Foreshadowing: {f}")

                if updates.resolved_threads:
                    original_threads = list(state.memory_context.global_foreshadowing)
                    for resolved in updates.resolved_threads:
                        for existing in original_threads:
                            if existing in resolved or resolved in existing:
                                if existing in state.memory_context.global_foreshadowing:
                                    state.memory_context.global_foreshadowing.remove(existing)
                                    print(f"✅ Resolved Thread: {existing}")

                sys_bible = db.query(NovelBible).filter(
                    NovelBible.novel_id == state.current_novel_id,
                    NovelBible.category == "system_state",
                    NovelBible.key == "global_foreshadowing"
                ).first()

                new_content = json.dumps(state.memory_context.global_foreshadowing, ensure_ascii=False)
                
                if sys_bible:
                    sys_bible.content = new_content
                else:
                    sys_bible = NovelBible(
                        novel_id=state.current_novel_id,
                        category="system_state",
                        key="global_foreshadowing",
                        content=new_content,
                        importance=10
                    )
                    db.add(sys_bible)

            db.commit()
            print("✅ Character evolution & Plot Threads saved to DB.")

            # 将最终章节内容写入数据库
            current_chapter_num = state.current_plot_index + 1
            
            chapter_entry = db.query(DBChapter).filter_by(
                novel_id=state.current_novel_id,
                branch_id=state.current_branch,
                chapter_number=current_chapter_num
            ).first()

            if not chapter_entry:
                chapter_entry = DBChapter(
                    novel_id=state.current_novel_id,
                    branch_id=state.current_branch,
                    chapter_number=current_chapter_num,
                    previous_chapter_id=state.last_chapter_id
                )
                db.add(chapter_entry)

            chapter_entry.title = f"第 {current_chapter_num} 章"
            if state.current_plot_index < len(state.plot_progress):
                chapter_entry.title = state.plot_progress[state.current_plot_index].title
                
            chapter_entry.content = state.current_draft
            
            # 使用新的结构化摘要生成器
            try:
                summary_result = await self.summarizer.generate_summary(
                    state.current_draft, 
                    state=state
                )
                chapter_entry.summary = summary_result.get("summary", state.current_draft[:200])
                
                # 提取新伏笔并添加到全局伏笔列表
                new_foreshadowing = summary_result.get("new_foreshadowing", [])
                for f in new_foreshadowing:
                    if f and f not in state.memory_context.global_foreshadowing:
                        state.memory_context.global_foreshadowing.append(f)
                        print(f"📖 从摘要中提取新伏笔: {f}")
            except Exception as e:
                logger.error(f"摘要生成失败，使用回退方案: {e}", exc_info=True)
                # 回退到简单摘要
                from .utils import generate_chapter_summary
                chapter_entry.summary = generate_chapter_summary(state.current_draft)
            
            chapter_entry.logic_checked = True
            
            outline = db.query(PlotOutline).filter_by(
                novel_id=state.current_novel_id,
                branch_id=state.current_branch,
                chapter_number=current_chapter_num
            ).first()
            if outline:
                outline.status = OutlineStatus.COMPLETED

            db.commit()
            db.refresh(chapter_entry)
            
            state.memory_context.recent_summaries.append(chapter_entry.summary)
            # 使用配置中的最近章节上下文数量限制
            from .config import Config
            max_recent_summaries = Config.antigravity.RECENT_CHAPTERS_CONTEXT
            if len(state.memory_context.recent_summaries) > max_recent_summaries:
                state.memory_context.recent_summaries.pop(0)

            print(f"✅ Chapter {current_chapter_num} finalized and saved to DB (ID: {chapter_entry.id}).")
            
            monitor.end_session(state.current_plot_index, success=True, retry_count=state.retry_count)
            
            return {
                "current_plot_index": state.current_plot_index + 1,
                "last_chapter_id": chapter_entry.id,
                "retry_count": 0
            }

        except Exception as e:
            logger.error(f"Error during evolution/finalizing for chapter {state.current_plot_index + 1}: {e}", exc_info=True)
            print(f"❌ Error during evolution/finalizing: {e}")
            db.rollback()
            monitor.end_session(state.current_plot_index, success=False)
            return {}
        finally:
            db.close()

    async def repair_node(self, state: NGEState):
        """Rule 5.2: Gemini 介入重写修复"""
        print("🔴 触发 Rule 5.2：Gemini 执行强制修复...")

        prompt = (
            f"你作为一个小说主编，现在需要对一份经过多次修改仍不合格的草稿进行最终修复。\n"
            f"修改意见：{state.review_feedback}\n"
            f"原始草稿：\n{state.current_draft}\n\n"
            f"请直接输出修复后的完整小说正文，不要包含任何前言、后语或说明性文字。只输出小说内容。"
        )
        
        response = await self.reviewer.llm.ainvoke(prompt)
        fixed_draft = normalize_llm_content(response.content)
        fixed_draft = strip_think_tags(fixed_draft)
        
        return {
            "current_draft": fixed_draft,
            "next_action": NodeAction.EVOLVE,
            "review_feedback": "Fixed by Gemini (Rule 5.2)"
        }

    def should_continue(self, state: NGEState) -> str:
        """
        Rule 5.1 & 5.2: 循环熔断机制
        
        Args:
            state: 当前状态
            
        Returns:
            下一步动作: "continue", "revise", 或 "repair"
        """
        if state.next_action == NodeAction.EVOLVE:
            print("🟢 审核通过。")
            return ReviewDecision.CONTINUE
        
        # 使用 state 中的配置，如果没有则使用 Config 默认值
        max_retry_limit = (
            state.max_retry_limit 
            if hasattr(state, 'max_retry_limit') 
            else Config.antigravity.MAX_RETRY_LIMIT
        )
        
        if state.retry_count >= max_retry_limit:
            print(f"🔴 熔断保护：已重试 {state.retry_count} 次，进入 Gemini 分级修复。")
            # 记录违规信息
            if hasattr(state, 'antigravity_context'):
                state.antigravity_context.violated_rules.append(
                    f"Rule 5.2 Triggered: 第{state.current_plot_index + 1}章在第{state.retry_count}次重试后强制通过"
                )
            return ReviewDecision.REPAIR
            
        print(f"🔄 准备第 {state.retry_count + 1} 次生成...")
        return ReviewDecision.REVISE
