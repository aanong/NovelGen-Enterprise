from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from .schemas.state import NGEState
from .agents.architect import ArchitectAgent
from .agents.writer import WriterAgent
from .agents.reviewer import ReviewerAgent
from .agents.style_analyzer import StyleAnalyzer
from .db.base import SessionLocal
from .db.models import NovelBible, Character, CharacterRelationship, PlotOutline, LogicAudit, Chapter as DBChapter
from .db.vector_store import VectorStore
from .monitoring import monitor
import json
from datetime import datetime

class NGEGraph:
    def __init__(self):
        self.architect = ArchitectAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()
        self.analyzer = StyleAnalyzer()
        
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
                "continue": "evolve",
                "revise": "write"
            }
        )
        
        self.workflow.add_edge("evolve", END)
        
        self.app = self.workflow.compile()

    async def load_context_node(self, state: NGEState):
        """从数据库加载/刷新当前的 State（如人物状态、世界观）"""
        print(f"--- LOADING CONTEXT (Chapter {state.current_plot_index + 1}) ---")
        
        # 启动性能会话
        session_id = monitor.start_session(state.current_plot_index + 1)
        
        db = SessionLocal()
        try:
            db_chars = db.query(Character).all()
            # 同步数据库中的角色状态到内存
            for c in db_chars:
                if c.name in state.characters:
                    state.characters[c.name].current_mood = c.current_mood
                    state.characters[c.name].personality_traits = c.personality_traits or {}
            
            return {"next_action": "plan"}
        except Exception as e:
            print(f"Error loading context: {e}")
            return {"next_action": "plan"}
        finally:
            db.close()

    async def plan_node(self, state: NGEState):
        print("--- PLANNING CHAPTER ---")
        db = SessionLocal()
        try:
            current_chapter_num = state.current_plot_index + 1
            
            # 1. 检查 DB 是否已有大纲
            outline = db.query(PlotOutline).filter_by(
                novel_id=1, 
                chapter_number=current_chapter_num
            ).first()
            
            if outline and outline.status == "completed":
                print(f"Found existing outline for Ch.{current_chapter_num}")
                instruction = f"Scene: {outline.scene_description}\nConflict: {outline.key_conflict}"
                return {"next_action": "write", "review_feedback": instruction}

            # 2. 调用 Architect Agent 生成
            plan_data = await self.architect.plan_next_chapter(state)
            
            # 3. 存入 DB
            new_outline = PlotOutline(
                novel_id=1,
                chapter_number=current_chapter_num,
                scene_description=plan_data.get("scene", "Generated Scene"),
                key_conflict=plan_data.get("conflict", "Generated Conflict"),
                status="pending"
            )
            db.add(new_outline)
            db.commit()
            
            return {"next_action": "refine_context", "review_feedback": plan_data["instruction"]}
        except Exception as e:
            print(f"Planning Error: {e}")
            return {"next_action": "refine_context", "review_feedback": "Error in planning."}
        finally:
            db.close()

    async def refine_context_node(self, state: NGEState):
        """上下文精炼 (Real RAG Implementation)"""
        print("--- REFINING CONTEXT VIA RAG ---")
        
        # 1. 获取当前规划的场景描述作为 Query
        query = state.review_feedback # 在 plan 节点中，instruction 或 plan_data 被存入 review_feedback
        
        vs = VectorStore()
        try:
            # 2. 检索相关世界观
            bible_results = await vs.search_bible(query, top_k=3)
            bible_context = "\n".join([f"[{b['key']}]: {b['content']}" for b in bible_results])
            
            # 3. 检索相关文风范例
            style_results = await vs.search_style(query, top_k=1)
            style_context = style_results[0]['content'] if style_results else "常规文风"
            
            print(f"✅ RAG 检索完成。找到 {len(bible_results)} 条相关设定。")
            
            # 4. 更新 State 中的提示词
            # 将检索到的内容注入到 review_feedback 中，供 Writer 使用
            enhanced_instruction = (
                f"{state.review_feedback}\n\n"
                f"【参考世界观设定】\n{bible_context}\n\n"
                f"【文风参考范例】\n{style_context}"
            )
            
            return {
                "next_action": "write",
                "review_feedback": enhanced_instruction
            }
        except Exception as e:
            print(f"RAG Error: {e}")
            return {"next_action": "write"}
        finally:
            vs.close()

    async def write_node(self, state: NGEState):
        print("--- WRITING CHAPTER ---")
        draft = await self.writer.write_chapter(state, state.review_feedback)
        return {"current_draft": draft, "next_action": "review"}

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
                return {"next_action": "evolve", "review_feedback": "Passed"}
            else:
                return {
                    "next_action": "write", 
                    "review_feedback": f"修正建议：{review_result.get('feedback')}",
                    "retry_count": state.retry_count + 1
                }
        finally:
            db.close()

    async def evolve_node(self, state: NGEState):
        print("--- EVOLVING CHARACTERS & SAVING ---")
        db = SessionLocal()
        try:
            evolution_data = await self.reviewer.evolve_characters(state, state.current_draft)
            
            # 1. 更新内存和 DB 中的角色状态
            for name, changes in evolution_data.items():
                if name in state.characters:
                    char = state.characters[name]
                    char.current_mood = changes.get("new_mood", char.current_mood)
                    evol_log = f"Ch.{state.current_plot_index + 1}: {changes.get('evolution_summary', '')}"
                    char.evolution_log.append(evol_log)
                    
                    # 同步到 DB
                    db_char = db.query(Character).filter_by(name=name).first()
                    if db_char:
                        db_char.current_mood = char.current_mood
                        db_char.evolution_log = char.evolution_log
            
            # 2. 保存章节
            new_chapter = DBChapter(
                novel_id=1,
                chapter_number=state.current_plot_index + 1,
                title=f"第 {state.current_plot_index + 1} 章",
                content=state.current_draft,
                summary=evolution_data.get("summary", ""),
                created_at=datetime.utcnow(),
                logic_checked=True
            )
            db.add(new_chapter)
            db.commit()
            
            # 3. 结束性能会话
            monitor.end_session(state.current_plot_index, success=True, retry_count=state.retry_count)
            monitor.print_summary()

            return {
                "current_plot_index": state.current_plot_index + 1,
                "next_action": "finalize",
                "retry_count": 0 # 重置章节重试计数
            }
        except Exception as e:
            print(f"Save & Evolve Error: {e}")
            db.rollback()
            return {"next_action": "finalize"}
        finally:
            db.close()

    def should_continue(self, state: NGEState):
        """Rule 5.1 & 5.2: 循环熔断机制"""
        if state.next_action == "evolve":
            print("🟢 审核通过。")
            return "continue"
        if state.retry_count >= state.max_retry_limit:
            print(f"🔴 熔断保护：已重试 {state.retry_count} 次，强制进入演化。")
            # 记录熔断事件到反重力上下文
            state.antigravity_context.violated_rules.append(
                f"Rule 5.2 Triggered: 第{state.current_plot_index + 1}章在第{state.retry_count}次重试后强制通过"
            )
            return "continue"
        print(f"🔄 准备第 {state.retry_count + 1} 次生成...")
        return "revise"
