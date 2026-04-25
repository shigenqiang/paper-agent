"""
问题导向的Paper Agent模块

基于论文写作中的常见困难设计的针对性Agent：
- TopicRefinerAgent: 选题精炼
- LiteratureMapperAgent: 文献映射
- MethodologyAdvisorAgent: 方法指导
- ArgumentBuilderAgent: 论证构建
- SectionDifferentiatorAgent: 差异化写作
- DiscussionDeepenerAgent: 讨论深化
- ChartFormatterAgent: 图表规范化
- LanguagePolisherAgent: 语言润色
- PlagiarismCheckerAgent: 查重检测
"""
from .base_problem_agent import ProblemAgentBase, AgentOutput, LLMConfig
from .topic_refiner import TopicRefinerAgent
from .literature_mapper import LiteratureMapperAgent
from .methodology_advisor import MethodologyAdvisorAgent
from .argument_builder import ArgumentBuilderAgent
from .section_differentiator import SectionDifferentiatorAgent
from .discussion_deepener import DiscussionDeepenerAgent
from .chart_formatter import ChartFormatterAgent
from .language_polisher import LanguagePolisherAgent
from .plagiarism_checker import PlagiarismCheckerAgent
from .supervisor import ProblemSupervisor

__all__ = [
    "ProblemAgentBase",
    "AgentOutput",
    "LLMConfig",
    "TopicRefinerAgent",
    "LiteratureMapperAgent",
    "MethodologyAdvisorAgent",
    "ArgumentBuilderAgent",
    "SectionDifferentiatorAgent",
    "DiscussionDeepenerAgent",
    "ChartFormatterAgent",
    "LanguagePolisherAgent",
    "PlagiarismCheckerAgent",
    "ProblemSupervisor",
]
