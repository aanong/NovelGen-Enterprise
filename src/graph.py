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
        self.workflow.add_node("load_context", self.load_context_node) # 新增：从DB加载最新上下文
        self.workflow.add_node("plan", self.plan_node)
        self.workflow.add_node("refine_context", self.refine_context_node) # 新增：上下文精炼
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
            # 1. 加载人物最新状态
            chars = db.query(Character).all()
            char_map = {}
            for c in chars:
                char_map[c.name] = {
                    "name": c.name,
                    "personality_traits": c.personality_traits,
                    "current_mood": c.current_mood,
                    "evolution_log": c.evolution_log,
                    "status": c.status
                    # relationships 需要单独处理或在 CharacterRelationship 表中查询
                }
            
            # 2. 简单的将 DB 数据同步回 State (这里做简化处理，实际需要完整映射)
            # state.characters = char_map 
            
            return {"next_action": "plan"}
        except Exception as e:
            print(f"Error loading context: {e}")
            return {"next_action": "plan"} # Fallback
        finally:
            db.close()

    async def plan_node(self, state: NGEState):
        print("--- PLANNING CHAPTER ---")
        db = SessionLocal()
        try:
            current_chapter_num = state.current_plot_index + 1
            
            # 1. 检查 DB 是否已有大纲
            outline = db.query(PlotOutline).filter_by(
                novel_id=1, # 假设单本小说 ID=1
                chapter_number=current_chapter_num
            ).first()
            
            if outline and outline.status == "completed":
                print(f"Found existing outline for Ch.{current_chapter_num}")
                instruction = f"Scene: {outline.scene_description}\nConflict: {outline.key_conflict}"
                return {"next_action": "write", "review_feedback": instruction}

            # 2. 如果没有，调用 Architect Agent 生成
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
            return {"next_action": "refine_context", "review_feedback": "Error in planning, proceeding with default."}
        finally:
            db.close()

    async def refine_context_node(self, state: NGEState):
        """
        上下文精炼节点：
        基于即将写的章节内容（state.review_feedback 中的 instruction），
        从 VectorDB 中检索最相关的 '世界观设定' 和 '过往伏笔'，
        替换掉 state.memory_context 中冗余的全局信息。
        """
        print("--- REFINING CONTEXT ---")
        
        # 模拟：实际应调用 RAG 检索
        # query = state.review_feedback 
        # relevant_docs = vector_store.similarity_search(query)
        
        # 假设检索到了关于“魂力测试”的特定规则
        refined_context = [
            "检索到的设定：魂力测试碑在受到攻击时会反弹力量。",
            "检索到的伏笔：主角口袋里有一块神秘的黑石。"
        ]
        
        # 更新 MemoryContext (这里仅做演示，实际应更新 state.memory_context 字段)
        print(f"Refined Context: {refined_context}")
        
        return {"next_action": "write"}

    async def write_node(self, state: NGEState):
        print("--- WRITING CHAPTER ---")
        # 正文撰写可以引入 RAG (在 WriterAgent 内部实现)，这里只负责调度
        draft = await self.writer.write_chapter(state, state.review_feedback)
        return {"current_draft": draft, "next_action": "review"}

    async def review_node(self, state: NGEState):
        print("--- REVIEWING DRAFT ---")
        db = SessionLocal()
        try:
            review_result = await self.reviewer.review_draft(state, state.current_draft)
            
            # 记录审计日志
            audit = LogicAudit(
                chapter_id=None, # 尚未生成 Chapter ID
                reviewer_role="Deepseek-Critic",
                is_passed=review_result["passed"],
                feedback=review_result["feedback"],
                logic_score=review_result.get("score", 0.0),
                created_at=datetime.utcnow()
            )
            db.add(audit)
            db.commit()

            if review_result["passed"]:
                return {"next_action": "evolve", "review_feedback": "Passed"}
            else:
                print(f"Draft failed review: {review_result['feedback']}")
                return {
                    "next_action": "write", 
                    "review_feedback": f"修正建议：{review_result['feedback']}",
                    "retry_count": state.retry_count + 1
                }
        finally:
            db.close()

    async def evolve_node(self, state: NGEState):
        print("--- EVOLVING CHARACTERS & SAVING ---")
        db = SessionLocal()
        try:
            # 1. 触发人物演化
            evolution = await self.reviewer.evolve_characters(state, state.current_draft)
            
            # 2. 持久化章节内容
            new_chapter = DBChapter(
                novel_id=1,
                chapter_number=state.current_plot_index + 1,
                title=f"Chapter {state.current_plot_index + 1}",
                content=state.current_draft,
                created_at=datetime.utcnow(),
                logic_checked=True
            )
            db.add(new_chapter)
            
            # 3. 更新人物状态 (示例：更新 Mood)
            # 实际应用中应解析 evolution 结果并更新 CharacterRelationship 表
            # ...
            
            db.commit()
            
            new_index = state.current_plot_index + 1
            return {
                "current_plot_index": new_index,
                "next_action": "finalize"
            }
        except Exception as e:
            print(f"Save Error: {e}")
            db.rollback()
            return {"next_action": "finalize"}
        finally:
            db.close()

    def should_continue(self, state: NGEState):
        if state.next_action == "evolve":
            return "continue"
        return "revise"

if __name__ == "__main__":
    pass
