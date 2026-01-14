import logging
from typing import Dict, Any, Optional
from ..schemas.state import NGEState
from ..agents.constants import NodeAction
from ..db.base import SessionLocal
from ..db.models import PlotOutline
from ..agents.architect import ArchitectAgent
from ..agents.rhythm_analyzer import RhythmAnalyzer
from .base import BaseNode

logger = logging.getLogger(__name__)

class PlanNode(BaseNode):
    """
    规划节点
    负责章节规划、连贯性检查和节奏控制
    """
    
    def __init__(
        self, 
        architect: ArchitectAgent,
        rhythm_analyzer: Optional[RhythmAnalyzer] = None
    ):
        """
        初始化规划节点
        
        Args:
            architect: 架构师 Agent
            rhythm_analyzer: 节奏分析器（可选，为空则自动创建）
        """
        self.architect = architect
        self.rhythm_analyzer = rhythm_analyzer or RhythmAnalyzer()

    async def _check_chapter_coherence(self, state: NGEState, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查拟定规划与前文的连贯性
        """
        return await self.architect.check_coherence(state, plan_data)
    
    async def _analyze_rhythm(self, state: NGEState) -> Dict[str, Any]:
        """
        分析节奏曲线并获取下一章建议
        
        Args:
            state: 当前状态
            
        Returns:
            节奏分析结果
        """
        try:
            result = await self.rhythm_analyzer.analyze_and_suggest(state)
            return result
        except Exception as e:
            logger.warning(f"节奏分析失败: {e}")
            return {}

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        print(f"--- PLANNING CHAPTER (Branch: {state.current_branch}) ---")
        db = SessionLocal()
        try:
            current_chapter_num = state.current_plot_index + 1
            
            # 1. 检查 DB 是否已有大纲 (匹配 branch_id)
            outline = db.query(PlotOutline).filter_by(
                novel_id=state.current_novel_id, 
                chapter_number=current_chapter_num,
                branch_id=state.current_branch
            ).first()
            
            plan_data = {}
            if outline:
                # 如果已有大纲（不管是 pending 还是 completed），直接复用
                print(f"✅ 发现现有大纲 (Ch.{current_chapter_num}, Branch: {state.current_branch}, Status: {outline.status})")
                
                # 如果是 pending 且内容为空，则可以调用 Agent 补充
                if not outline.scene_description or not outline.key_conflict:
                    plan_data = await self.architect.plan_next_chapter(state)
                    outline.scene_description = plan_data.get("scene", outline.scene_description)
                    outline.key_conflict = plan_data.get("conflict", outline.key_conflict)
                    db.commit()
                else:
                    plan_data = {
                        "scene": outline.scene_description,
                        "conflict": outline.key_conflict,
                        "instruction": f"Scene: {outline.scene_description}\nConflict: {outline.key_conflict}"
                    }
            else:
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

            # 4. 检查拟定规划的连贯性
            coherence_feedback = ""
            if state.last_chapter_id or state.memory_context.recent_summaries:
                coherence_check = await self._check_chapter_coherence(state, plan_data)
                if not coherence_check.get("coherent", True):
                    issues = coherence_check.get("issues", [])
                    logger.warning(f"章节连贯性检查发现问题: {issues}")
                    coherence_feedback = f"\n\n【连贯性警示】：\n" + "\n".join([f"- {i}" for i in issues])
                    print(f"⚠️ 连贯性提醒: {', '.join(issues[:2])}")
            
            # 5. 节奏分析与控制（新增）
            rhythm_feedback = ""
            try:
                rhythm_result = await self._analyze_rhythm(state)
                if rhythm_result:
                    rhythm_feedback = self.rhythm_analyzer.generate_pacing_prompt(rhythm_result)
                    
                    # 检查是否有节奏警告
                    curve = rhythm_result.get("curve_analysis", {})
                    if curve.get("pattern_warning"):
                        print(f"⚠️ 节奏警告: {curve['pattern_warning']}")
                    
                    suggestion = rhythm_result.get("next_chapter_suggestion", {})
                    print(f"📊 节奏建议: 强度 {suggestion.get('suggested_intensity', '?')}/10, 类型: {suggestion.get('suggested_type', '?')}")
            except Exception as e:
                logger.warning(f"节奏分析跳过: {e}")
            
            return {
                "next_action": NodeAction.REFINE_CONTEXT, 
                "review_feedback": plan_data["instruction"] + coherence_feedback + rhythm_feedback
            }
        except Exception as e:
            logger.error(f"Planning error for chapter {current_chapter_num}: {e}", exc_info=True)
            print(f"Planning Error: {e}")
            return {"next_action": NodeAction.REFINE_CONTEXT, "review_feedback": "Error in planning."}
        finally:
            db.close()
