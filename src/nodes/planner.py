import logging
from typing import Dict, Any
from ..schemas.state import NGEState
from ..agents.constants import NodeAction
from ..db.base import SessionLocal
from ..db.models import PlotOutline
from ..agents.architect import ArchitectAgent
from .base import BaseNode

logger = logging.getLogger(__name__)

class PlanNode(BaseNode):
    def __init__(self, architect: ArchitectAgent):
        self.architect = architect

    async def _check_chapter_coherence(self, state: NGEState) -> Dict[str, Any]:
        """
        检查章节连贯性
        简单实现：总是返回 True，后续可对接 LogicAgent
        """
        # TODO: Implement actual coherence check using LLM or LogicAgent
        return {"coherent": True, "issues": []}

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
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
                
                # 如果是 pending 且内容为空，则可以调用 Agent 补充
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
