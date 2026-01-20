"""
工厂类模块
提供 Agent 和 Node 的统一创建接口
支持依赖注入和配置化实例化
"""
from typing import Dict, Any, Optional, Type, TypeVar
from functools import lru_cache
import logging

from .registry import get_agent_class, get_node_class

from .registry import get_agent_class, get_node_class

T = TypeVar('T')


class AgentFactory:
    """
    Agent 工厂类
    统一管理 Agent 的创建和缓存
    
    使用方式：
        factory = AgentFactory()
        writer = factory.get_writer()
        architect = factory.get_architect()
    """
    
    _instance: Optional["AgentFactory"] = None
    _agents: Dict[str, Any] = {}
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._agents = {}
        return cls._instance
    
    def get_writer(self, **kwargs) -> "WriterAgent":
        """获取 Writer Agent"""
        if "writer" not in self._agents or kwargs:
            cls = get_agent_class("writer")
            if not cls:
                from ..agents.writer import WriterAgent
                cls = WriterAgent
            self._agents["writer"] = cls(**kwargs)
        return self._agents["writer"]
    
    def get_architect(self, **kwargs) -> "ArchitectAgent":
        """获取 Architect Agent"""
        if "architect" not in self._agents or kwargs:
            cls = get_agent_class("architect")
            if not cls:
                from ..agents.architect import ArchitectAgent
                cls = ArchitectAgent
            self._agents["architect"] = cls(**kwargs)
        return self._agents["architect"]
    
    def get_reviewer(self, **kwargs) -> "ReviewerAgent":
        """获取 Reviewer Agent"""
        if "reviewer" not in self._agents or kwargs:
            cls = get_agent_class("reviewer")
            if not cls:
                from ..agents.reviewer import ReviewerAgent
                cls = ReviewerAgent
            self._agents["reviewer"] = cls(**kwargs)
        return self._agents["reviewer"]
    
    def get_evolver(self, **kwargs) -> "CharacterEvolver":
        """获取 Character Evolver Agent"""
        if "evolver" not in self._agents or kwargs:
            cls = get_agent_class("evolver")
            if not cls:
                from ..agents.evolver import CharacterEvolver
                cls = CharacterEvolver
            self._agents["evolver"] = cls(**kwargs)
        return self._agents["evolver"]
    
    def get_summarizer(self, **kwargs) -> "SummarizerAgent":
        """获取 Summarizer Agent"""
        if "summarizer" not in self._agents or kwargs:
            cls = get_agent_class("summarizer")
            if not cls:
                from ..agents.summarizer import SummarizerAgent
                cls = SummarizerAgent
            self._agents["summarizer"] = cls(**kwargs)
        return self._agents["summarizer"]
    
    def get_style_analyzer(self, **kwargs) -> "StyleAnalyzer":
        """获取 Style Analyzer Agent"""
        if "style_analyzer" not in self._agents or kwargs:
            cls = get_agent_class("style_analyzer")
            if not cls:
                from ..agents.style_analyzer import StyleAnalyzer
                cls = StyleAnalyzer
            self._agents["style_analyzer"] = cls(**kwargs)
        return self._agents["style_analyzer"]
    
    def get_rhythm_analyzer(self, **kwargs) -> "RhythmAnalyzer":
        """获取 Rhythm Analyzer Agent"""
        if "rhythm_analyzer" not in self._agents or kwargs:
            cls = get_agent_class("rhythm_analyzer")
            if not cls:
                from ..agents.rhythm_analyzer import RhythmAnalyzer
                cls = RhythmAnalyzer
            self._agents["rhythm_analyzer"] = cls(**kwargs)
        return self._agents["rhythm_analyzer"]
    
    def get_allusion_advisor(self, **kwargs) -> "AllusionAdvisor":
        """获取 Allusion Advisor Agent"""
        if "allusion_advisor" not in self._agents or kwargs:
            cls = get_agent_class("allusion_advisor")
            if not cls:
                from ..agents.allusion_advisor import AllusionAdvisor
                cls = AllusionAdvisor
            self._agents["allusion_advisor"] = cls(**kwargs)
        return self._agents["allusion_advisor"]
    
    def clear_cache(self):
        """清除缓存的 Agent 实例"""
        self._agents.clear()
        logger.info("Agent 缓存已清除")
    
    def get_all_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有已创建 Agent 的信息"""
        return {
            name: agent.get_agent_info() 
            for name, agent in self._agents.items()
            if hasattr(agent, 'get_agent_info')
        }


class NodeFactory:
    """
    Node 工厂类
    统一管理 Node 的创建，支持依赖注入
    
    使用方式：
        factory = NodeFactory(agent_factory)
        plan_node = factory.get_plan_node()
        write_node = factory.get_write_node()
    """
    
    def __init__(self, agent_factory: Optional[AgentFactory] = None):
        """
        初始化 Node 工厂
        
        Args:
            agent_factory: Agent 工厂实例，为空则自动创建
        """
        self.agent_factory = agent_factory or AgentFactory()
        self._nodes: Dict[str, Any] = {}
    
    def get_load_context_node(self) -> "LoadContextNode":
        """获取 LoadContext Node"""
        if "load_context" not in self._nodes:
            from ..nodes.loader import LoadContextNode
            self._nodes["load_context"] = LoadContextNode()
        return self._nodes["load_context"]
    
    def get_plan_node(self) -> "PlanNode":
        """获取 Plan Node"""
        if "plan" not in self._nodes:
            from ..nodes.planner import PlanNode
            architect = self.agent_factory.get_architect()
            rhythm_analyzer = self.agent_factory.get_rhythm_analyzer()
            self._nodes["plan"] = PlanNode(architect, rhythm_analyzer)
        return self._nodes["plan"]
    
    def get_refine_context_node(self) -> "RefineContextNode":
        """获取 RefineContext Node"""
        if "refine_context" not in self._nodes:
            from ..nodes.refiner import RefineContextNode
            allusion_advisor = self.agent_factory.get_allusion_advisor()
            self._nodes["refine_context"] = RefineContextNode(allusion_advisor)
        return self._nodes["refine_context"]
    
    def get_write_node(self) -> "WriteNode":
        """获取 Write Node"""
        if "write" not in self._nodes:
            from ..nodes.writer import WriteNode
            writer = self.agent_factory.get_writer()
            self._nodes["write"] = WriteNode(writer)
        return self._nodes["write"]
    
    def get_review_node(self) -> "ReviewNode":
        """获取 Review Node"""
        if "review" not in self._nodes:
            from ..nodes.reviewer import ReviewNode
            reviewer = self.agent_factory.get_reviewer()
            self._nodes["review"] = ReviewNode(reviewer)
        return self._nodes["review"]
    
    def get_repair_node(self) -> "RepairNode":
        """获取 Repair Node"""
        if "repair" not in self._nodes:
            from ..nodes.reviewer import RepairNode
            reviewer = self.agent_factory.get_reviewer()
            self._nodes["repair"] = RepairNode(reviewer)
        return self._nodes["repair"]
    
    def get_evolve_node(self) -> "EvolveNode":
        """获取 Evolve Node"""
        if "evolve" not in self._nodes:
            from ..nodes.evolver import EvolveNode
            evolver = self.agent_factory.get_evolver()
            summarizer = self.agent_factory.get_summarizer()
            self._nodes["evolve"] = EvolveNode(evolver, summarizer)
        return self._nodes["evolve"]
    
    def get_all_nodes(self) -> Dict[str, Any]:
        """
        获取所有 Node 实例
        
        Returns:
            节点名称到实例的映射
        """
        return {
            "load_context": self.get_load_context_node(),
            "plan": self.get_plan_node(),
            "refine_context": self.get_refine_context_node(),
            "write": self.get_write_node(),
            "review": self.get_review_node(),
            "repair": self.get_repair_node(),
            "evolve": self.get_evolve_node(),
        }
    
    def clear_cache(self):
        """清除缓存的 Node 实例"""
        self._nodes.clear()
        logger.info("Node 缓存已清除")


class DependencyContainer:
    """
    依赖注入容器
    管理整个应用的依赖关系
    
    使用方式：
        container = DependencyContainer()
        graph = container.create_graph()
    """
    
    _instance: Optional["DependencyContainer"] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化容器"""
        if not self._initialized:
            self._agent_factory = AgentFactory()
            self._node_factory = NodeFactory(self._agent_factory)
            self._initialized = True
    
    @property
    def agents(self) -> AgentFactory:
        """获取 Agent 工厂"""
        return self._agent_factory
    
    @property
    def nodes(self) -> NodeFactory:
        """获取 Node 工厂"""
        return self._node_factory
    
    def create_graph(self) -> "NGEGraph":
        """
        创建工作流图
        
        Returns:
            配置好的工作流图实例
        """
        from ..graph import NGEGraph
        return NGEGraph(
            agent_factory=self._agent_factory,
            node_factory=self._node_factory
        )
    
    def reset(self):
        """重置容器，清除所有缓存"""
        self._agent_factory.clear_cache()
        self._node_factory.clear_cache()
        logger.info("依赖容器已重置")


# ============ 便捷函数 ============

def get_container() -> DependencyContainer:
    """获取全局依赖容器"""
    return DependencyContainer()


def get_agent_factory() -> AgentFactory:
    """获取全局 Agent 工厂"""
    return get_container().agents


def get_node_factory() -> NodeFactory:
    """获取全局 Node 工厂"""
    return get_container().nodes
