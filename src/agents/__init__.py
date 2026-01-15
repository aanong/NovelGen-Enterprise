"""
Agents 模块
提供小说生成各环节的 AI Agent
"""

from .base import BaseAgent
from .writer import WriterAgent
from .architect import ArchitectAgent
from .evolver import CharacterEvolver, apply_evolution_to_character
from .reviewer import ReviewerAgent
from .summarizer import SummarizerAgent
from .style_analyzer import StyleAnalyzer
from .learner import LearnerAgent
from .allusion_advisor import AllusionAdvisor
from .writing_technique_advisor import WritingTechniqueAdvisor
from .world_guard import WorldConsistencyGuard

__all__ = [
    # 基础类
    "BaseAgent",
    
    # 核心 Agent
    "WriterAgent",
    "ArchitectAgent",
    "CharacterEvolver",
    "ReviewerAgent",
    "SummarizerAgent",
    
    # 辅助 Agent
    "StyleAnalyzer",
    "LearnerAgent",
    "AllusionAdvisor",
    
    # 新增 Agent
    "WritingTechniqueAdvisor",  # 写作技法顾问
    "WorldConsistencyGuard",    # 世界观一致性守护
    
    # 辅助函数
    "apply_evolution_to_character",
]
