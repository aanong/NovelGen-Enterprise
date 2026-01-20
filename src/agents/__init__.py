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
from .learner import LearnerAgent
from .allusion_advisor import AllusionAdvisor

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
    "LearnerAgent",
    "AllusionAdvisor",
    
    # 辅助函数
    "apply_evolution_to_character",
]
