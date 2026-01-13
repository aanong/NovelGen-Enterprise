from typing import Dict, Any
from datetime import datetime
from ..schemas.state import NGEState
from ..agents.constants import NodeAction, ReviewDecision
from ..db.base import SessionLocal
from ..db.models import LogicAudit
from ..agents.reviewer import ReviewerAgent
from ..utils import normalize_llm_content, strip_think_tags
from ..config import Config
from .base import BaseNode

class ReviewNode(BaseNode):
    def __init__(self, reviewer: ReviewerAgent):
        self.reviewer = reviewer

    async def __call__(self, state: NGEState) -> Dict[str, Any]:
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
    Rule 5.1 & 5.2: 循环熔断机制
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
