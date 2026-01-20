import logging
from typing import Dict, Any, Optional
from ..schemas.state import NGEState
from ..core.types import NodeAction
from ..db.base import SessionLocal
from ..db.models import PlotOutline
from ..agents.architect import ArchitectAgent
from ..agents.rhythm_analyzer import RhythmAnalyzer
from .base import BaseNode
from ..core.registry import register_node

logger = logging.getLogger(__name__)

@register_node("plan")
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
            coherence_feedback = ""
            
            if outline and outline.status == "completed":
                 # 如果已有完成的大纲，直接复用
                print(f"✅ 发现现有完成大纲 (Ch.{current_chapter_num})")
                plan_data = {
                    "scene": outline.scene_description,
                    "conflict": outline.key_conflict,
                    "instruction": f"Scene: {outline.scene_description}\nConflict: {outline.key_conflict}"
                }
            else:
                # 2. 规划循环（带自动重试）
                max_retries = 2
                attempt = 0
                
                while attempt <= max_retries:
                    # 如果有 outline 但不完整，或者没有 outline，都进入生成逻辑
                    # 第一次尝试如果没有 feedback，就生成新的
                    # 后续尝试如果有 feedback，就带上 feedback 重成
                    
                    if attempt > 0:
                        print(f"🔄 规划重试 ({attempt}/{max_retries})...")
                    
                    plan_data = await self.architect.plan_next_chapter(state, feedback=coherence_feedback)
                    
                    # 连贯性检查
                    if state.last_chapter_id or state.memory_context.recent_summaries:
                        coherence_check = await self._check_chapter_coherence(state, plan_data)
                        if not coherence_check.get("coherent", True):
                            issues = coherence_check.get("issues", [])
                            score = coherence_check.get("score", 0.0)
                            
                            logger.warning(f"章节连贯性检查未通过 (Score: {score}): {issues}")
                            print(f"⚠️ 连贯性警告: {issues[0] if issues else '未知问题'}")
                            
                            # 如果分数太低，且还有重试机会，则重试
                            if score < 0.6 and attempt < max_retries:
                                coherence_feedback = "上一次规划存在严重连贯性问题，请修正：\n" + "\n".join([f"- {i}" for i in issues])
                                attempt += 1
                                continue
                            else:
                                # 虽有问题但不再重试（或者分数尚可），记录反馈给 Writer
                                coherence_feedback = f"\n\n【连贯性警示】：\n" + "\n".join([f"- {i}" for i in issues])
                                break
                        else:
                            # 检查通过
                            coherence_feedback = ""
                            break
                    else:
                        break
                
                # 3. 存入/更新 DB
                if outline:
                    outline.scene_description = plan_data.get("scene", "Generated Scene")
                    outline.key_conflict = plan_data.get("conflict", "Generated Conflict")
                    # 保持 pending，直到 Writer 完成
                else:
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
