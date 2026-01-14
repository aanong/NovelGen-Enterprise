"""
NGEGraph 模块
定义 NovelGen-Enterprise 的工作流图

采用依赖注入模式，支持灵活配置和测试
"""
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
import logging

from .schemas.state import NGEState
from .core.types import ReviewDecision
from .core.factories import AgentFactory, NodeFactory
from .nodes.reviewer import should_continue

logger = logging.getLogger(__name__)


class NGEGraph:
    """
    NovelGen-Enterprise 工作流图
    
    工作流程：
    load_context → plan → refine_context → write → review → evolve
                                                      ↓
                                    ┌─────────────────────┐
                                    │ CONTINUE → evolve   │
                                    │ REVISE → write      │
                                    │ REPAIR → repair     │
                                    └─────────────────────┘
    
    支持依赖注入，便于测试和配置
    """
    
    def __init__(
        self,
        agent_factory: Optional[AgentFactory] = None,
        node_factory: Optional[NodeFactory] = None
    ):
        """
        初始化工作流图
        
        Args:
            agent_factory: Agent 工厂，为空则自动创建
            node_factory: Node 工厂，为空则自动创建
        """
        # 初始化工厂
        self.agent_factory = agent_factory or AgentFactory()
        self.node_factory = node_factory or NodeFactory(self.agent_factory)
        
        # 获取所有节点
        self._init_nodes()
        
        # 构建工作流
        self.workflow = StateGraph(NGEState)
        self._build_graph()
    
    def _init_nodes(self):
        """初始化所有节点"""
        self.load_context_node = self.node_factory.get_load_context_node()
        self.plan_node = self.node_factory.get_plan_node()
        self.refine_context_node = self.node_factory.get_refine_context_node()
        self.write_node = self.node_factory.get_write_node()
        self.review_node = self.node_factory.get_review_node()
        self.repair_node = self.node_factory.get_repair_node()
        self.evolve_node = self.node_factory.get_evolve_node()
        
        logger.info("工作流节点初始化完成")

    def _build_graph(self):
        """构建工作流图"""
        # 添加节点
        self.workflow.add_node("load_context", self.load_context_node)
        self.workflow.add_node("plan", self.plan_node)
        self.workflow.add_node("refine_context", self.refine_context_node)
        self.workflow.add_node("write", self.write_node)
        self.workflow.add_node("review", self.review_node)
        self.workflow.add_node("repair", self.repair_node)
        self.workflow.add_node("evolve", self.evolve_node)
        
        # 设置入口点
        self.workflow.set_entry_point("load_context")
        
        # 添加边（线性流程）
        self.workflow.add_edge("load_context", "plan")
        self.workflow.add_edge("plan", "refine_context")
        self.workflow.add_edge("refine_context", "write")
        self.workflow.add_edge("write", "review")
        
        # 添加条件分支（审核后的路由）
        self.workflow.add_conditional_edges(
            "review",
            should_continue,
            {
                ReviewDecision.CONTINUE.value: "evolve",
                ReviewDecision.REVISE.value: "write",
                ReviewDecision.REPAIR.value: "repair"
            }
        )
        
        # 修复后继续演化
        self.workflow.add_edge("repair", "evolve")
        
        # 演化后结束
        self.workflow.add_edge("evolve", END)
        
        # 编译工作流
        self.app = self.workflow.compile()
        
        logger.info("工作流图构建完成")
    
    async def run(self, initial_state: NGEState) -> NGEState:
        """
        运行工作流
        
        Args:
            initial_state: 初始状态
            
        Returns:
            最终状态
        """
        logger.info(f"开始运行工作流，小说 ID: {initial_state.current_novel_id}")
        
        result = await self.app.ainvoke(initial_state)
        
        logger.info("工作流运行完成")
        return result
    
    def get_graph_info(self) -> Dict[str, Any]:
        """
        获取图信息
        
        Returns:
            图的配置信息
        """
        return {
            "nodes": list(self.workflow.nodes.keys()),
            "entry_point": "load_context",
            "agents": self.agent_factory.get_all_info()
        }


def create_graph(
    agent_factory: Optional[AgentFactory] = None,
    node_factory: Optional[NodeFactory] = None
) -> NGEGraph:
    """
    创建工作流图的便捷函数
    
    Args:
        agent_factory: Agent 工厂
        node_factory: Node 工厂
        
    Returns:
        配置好的工作流图
    """
    return NGEGraph(agent_factory, node_factory)
