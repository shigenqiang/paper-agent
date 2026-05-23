"""
问题导向的Paper Agent模块

基于论文写作中的常见困难设计的针对性Agent：
- TopicRefinerAgent: 选题精炼
- LiteratureMapperAgent: 文献映射
- MethodologyAdvisorAgent: 方法指导
- LanguagePolisherAgent: 语言润色
"""
from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig
from .topic_refiner import TopicRefinerAgent
from .literature_mapper import LiteratureMapperAgent
from .methodology_advisor import MethodologyAdvisorAgent
from .language_polisher import LanguagePolisherAgent

__all__ = [
    "ProblemAgentBase",
    "AgentOutput",
    "LLMConfig",
    "TopicRefinerAgent",
    "LiteratureMapperAgent",
    "MethodologyAdvisorAgent",
    "LanguagePolisherAgent",
]
