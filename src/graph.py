from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from .schemas.state import NGEState
from .agents.architect import ArchitectAgent
from .agents.writer import WriterAgent
from .agents.reviewer import ReviewerAgent
from .agents.style_analyzer import StyleAnalyzer
from .db.base import SessionLocal
from .db.models import NovelBible, Character, CharacterRelationship, PlotOutline, LogicAudit, Chapter as DBChapter
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
        db = SessionLocal()
        try:
            db_chars = db.query(Character).all()
            # 同步数据库中的角色状态到内存 (简略示例)
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
        """上下文精炼 (Mock RAG)"""
        print("--- REFINING CONTEXT ---")
        refined_context = [
            "检索到的设定：魂力测试碑在受到攻击时会反弹力量。",
            "检索到的伏笔：主角口袋里有一块神秘的黑石。"
        ]
        print(f"Refined Context: {refined_context}")
        return {"next_action": "write"}

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
            evolution = await self.reviewer.evolve_characters(state, state.current_draft)
            
            new_chapter = DBChapter(
                novel_id=1,
                chapter_number=state.current_plot_index + 1,
                title=f"Chapter {state.current_plot_index + 1}",
                content=state.current_draft,
                created_at=datetime.utcnow(),
                logic_checked=True
            )
            db.add(new_chapter)
            db.commit()
            
            return {
                "current_plot_index": state.current_plot_index + 1,
                "next_action": "finalize"
            }
        except Exception as e:
            print(f"Save Error: {e}")
            db.rollback()
            return {"next_action": "finalize"}
        finally:
            db.close()

    def should_continue(self, state: NGEState):
        """Rule 5.1 & 5.2: 循环熔断机制"""
        if state.next_action == "evolve":
            print("🟢 审核通过。")
            return "continue"
        if state.retry_count >= 3:
            print(f"🔴 熔断保护：已重试 {state.retry_count} 次，强制进入演化。")
            return "continue"
        print(f"🔄 准备第 {state.retry_count + 1} 次生成...")
        return "revise"
