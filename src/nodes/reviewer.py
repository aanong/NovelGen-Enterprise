from typing import Dict, Any, List
from datetime import datetime
from ..schemas.state import NGEState
from ..agents.constants import NodeAction, ReviewDecision
from ..db.base import SessionLocal
from ..db.models import LogicAudit, PlotOutline
from ..agents.reviewer import ReviewerAgent
from ..utils import normalize_llm_content, strip_think_tags
from ..config import Config
from .base import BaseNode
import re

class ReviewNode(BaseNode):
    def __init__(self, reviewer: ReviewerAgent):
        self.reviewer = reviewer

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
        print("--- REVIEWING DRAFT ---")
        db = SessionLocal()
        try:
            # 获取当前章节的大纲信息用于遵循度检查
            current_chapter_num = state.current_plot_index + 1
            outline = db.query(PlotOutline).filter_by(
                novel_id=state.current_novel_id,
                branch_id=state.current_branch,
                chapter_number=current_chapter_num
            ).first()
            
            outline_info = {
                "scene": outline.scene_description if outline else "未定义场景",
                "conflict": outline.key_conflict if outline else "未定义冲突"
            }
            
            review_result = await self.reviewer.review_draft(
                state, 
                state.current_draft,
                outline_info=outline_info
            )
            
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
                # 分析错误类型，决定重试策略
                error_type = self._classify_error(review_result)
                feedback = review_result.get('feedback', '')
                
                # 根据错误类型决定下一步动作
                if error_type == "logic_error":
                    # 逻辑错误：直接 REPAIR
                    return {
                        "next_action": NodeAction.REPAIR,
                        "review_feedback": f"逻辑错误，强制修复：{feedback}",
                        "retry_count": state.retry_count + 1
                    }
                elif error_type == "ooc_error":
                    # OOC 问题：REPAIR（强制修复）
                    return {
                        "next_action": NodeAction.REPAIR,
                        "review_feedback": f"人物 OOC，强制修复：{feedback}",
                        "retry_count": state.retry_count + 1
                    }
                else:
                    # 风格问题或其他：REVISE（最多 N 次）
                    from ..agents.constants import Defaults
                    max_style_retries = Defaults.MAX_STYLE_RETRIES
                    if state.retry_count >= max_style_retries:
                        # 超过风格重试次数，转为 REPAIR
                        return {
                            "next_action": NodeAction.REPAIR,
                            "review_feedback": f"风格问题多次重试失败，强制修复：{feedback}",
                            "retry_count": state.retry_count + 1
                        }
                    else:
                        return {
                            "next_action": NodeAction.WRITE,
                            "review_feedback": f"修正建议：{feedback}",
                            "retry_count": state.retry_count + 1
                        }
    
    def _classify_error(self, review_result: Dict[str, Any]) -> str:
        """
        分类错误类型
        
        Args:
            review_result: 审查结果
            
        Returns:
            错误类型：'logic_error', 'ooc_error', 'style_error', 'other'
        """
        feedback = review_result.get('feedback', '').lower()
        logical_errors = review_result.get('logical_errors', [])
        
        # 检查逻辑错误关键词
        logic_keywords = ['逻辑', '矛盾', '错误', '漏洞', '不符合', '违背设定', '世界观']
        if any(keyword in feedback for keyword in logic_keywords) or logical_errors:
            return "logic_error"
        
        # 检查 OOC 错误关键词
        ooc_keywords = ['ooc', '性格突变', '降智', '不符合性格', '人物不一致', '角色行为']
        if any(keyword in feedback for keyword in ooc_keywords):
            return "ooc_error"
        
        # 检查风格错误关键词
        style_keywords = ['风格', '文风', '语气', '节奏', '描写', '句式']
        if any(keyword in feedback for keyword in style_keywords):
            return "style_error"
        
        return "other"
        finally:
            db.close()

class RepairNode(BaseNode):
    def __init__(self, reviewer: ReviewerAgent):
        self.reviewer = reviewer

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
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

def should_continue(state: NGEState) -> str:
    """
    Rule 5.1 & 5.2: 循环熔断机制（智能重试策略）
    根据错误类型和重试次数决定下一步动作
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
    
    # 如果已经决定 REPAIR，直接返回
    if state.next_action == NodeAction.REPAIR:
        print(f"🔴 触发强制修复（智能重试策略）")
        if hasattr(state, 'antigravity_context'):
            state.antigravity_context.violated_rules.append(
                f"Rule 5.2 Triggered: 第{state.current_plot_index + 1}章在第{state.retry_count}次重试后强制修复"
            )
        return ReviewDecision.REPAIR
    
    # 达到最大重试次数，强制修复
    if state.retry_count >= max_retry_limit:
        print(f"🔴 熔断保护：已重试 {state.retry_count} 次，进入 Gemini 强制修复。")
        if hasattr(state, 'antigravity_context'):
            state.antigravity_context.violated_rules.append(
                f"Rule 5.2 Triggered: 第{state.current_plot_index + 1}章在第{state.retry_count}次重试后强制通过"
            )
        return ReviewDecision.REPAIR
        
    print(f"🔄 准备第 {state.retry_count + 1} 次生成...")
    return ReviewDecision.REVISE
