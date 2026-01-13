"""
NGEGraph 模块
定义 NovelGen-Enterprise 的工作流图
"""
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from .schemas.state import NGEState
from .agents.architect import ArchitectAgent
from .agents.writer import WriterAgent
from .agents.reviewer import ReviewerAgent
from .agents.style_analyzer import StyleAnalyzer
from .agents.evolver import CharacterEvolver
from .agents.summarizer import ChapterSummarizer
from .agents.constants import NodeAction, ReviewDecision
from .nodes import (
    LoadContextNode,
    PlanNode,
    RefineContextNode,
    WriteNode,
    ReviewNode,
    RepairNode,
    should_continue,
    EvolveNode
)
import logging

logger = logging.getLogger(__name__)

class NGEGraph:
    def __init__(self):
        self.architect = ArchitectAgent()
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()
        self.analyzer = StyleAnalyzer()
        self.evolver = CharacterEvolver()
        self.summarizer = ChapterSummarizer()
        
        # Instantiate nodes with dependencies
        self.load_context_node = LoadContextNode()
        self.plan_node = PlanNode(self.architect)
        self.refine_context_node = RefineContextNode()
        self.write_node = WriteNode(self.writer)
        self.review_node = ReviewNode(self.reviewer)
        self.repair_node = RepairNode(self.reviewer)
        self.evolve_node = EvolveNode(self.evolver, self.summarizer)
        
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
            should_continue,
            {
                ReviewDecision.CONTINUE: "evolve",
                ReviewDecision.REVISE: "write",
                ReviewDecision.REPAIR: "repair"
            }
        )
        
        self.workflow.add_edge("repair", "evolve")
        self.workflow.add_edge("evolve", END)
        
        self.app = self.workflow.compile()
